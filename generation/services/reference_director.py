"""参考图导演模式：由用户 prompt 解析分镜与逐镜参考绑定（非固定九职能）。"""

from __future__ import annotations

import json
import re

from django.conf import settings

REFERENCE_GUIDED_NEGATIVE = (
    "collage, grid layout, split screen with text banners, watermark, wrong SKU, "
    "redesigned packaging, copying competitor trademark text from style references"
)

VALID_REFERENCE_MODES = frozenset(
    {"identity", "style_mimic", "layout_mimic", "model_mimic", "scene_mimic", "full_mimic"}
)

_ZH_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def _coerce_text(val, default: str = "") -> str:
    if val is None:
        return default
    if isinstance(val, (list, tuple)):
        parts = [_coerce_text(x) for x in val]
        joined = " ".join(p for p in parts if p).strip()
        return joined or default
    return str(val).strip() or default


def _zh_num_to_int(s: str) -> int | None:
    s = (s or "").strip()
    if s.isdigit():
        return int(s)
    return _ZH_NUM.get(s)


def infer_product_and_layout_ref_indices(user_prompt: str, n_refs: int) -> tuple[int, int] | None:
    """从文案推断产品图与版式参考图的下标（0-based）。"""
    if n_refs < 2:
        return None
    text = (user_prompt or "").replace("\r", "")
    product_ix: int | None = None
    layout_ix: int | None = None

    for pat, role in (
        (r"图\s*([一二三四1234])\s*是[^，。；\n]{0,40}(产品|商品|sku|我方|我们的产品)", "product"),
        (r"图\s*([一二三四1234])\s*为[^，。；\n]{0,40}(产品|商品|sku|我方)", "product"),
        (r"图\s*([一二三四1234])\s*是[^，。；\n]{0,40}(模仿|参考|版式|构图|风格|样图)", "layout"),
        (r"图\s*([一二三四1234])\s*是[^，。；\n]{0,40}需要模仿", "layout"),
        (r"模仿\s*图\s*([一二三四1234])", "layout"),
        (r"参考\s*图\s*([一二三四1234])", "layout"),
    ):
        for m in re.finditer(pat, text, re.I):
            raw = m.group(1)
            idx = _zh_num_to_int(raw)
            if idx is None:
                continue
            ui = idx - 1
            if not (0 <= ui < n_refs):
                continue
            if role == "product" and product_ix is None:
                product_ix = ui
            elif role == "layout" and layout_ix is None:
                layout_ix = ui

    if product_ix is None and re.search(r"上传图\s*1|图\s*1\s*.*产品", text, re.I):
        product_ix = 0
    if layout_ix is None and re.search(r"上传图\s*2|图\s*2\s*.*(模仿|参考)", text, re.I):
        layout_ix = 1
    if product_ix is None:
        product_ix = 0
    if layout_ix is None:
        layout_ix = 1 if n_refs > 1 else 0
    if product_ix == layout_ix and n_refs > 1:
        layout_ix = 1 if product_ix != 1 else 0
    if 0 <= product_ix < n_refs and 0 <= layout_ix < n_refs:
        return product_ix, layout_ix
    return None


def _dual_ref_binding(user_prompt: str, n_refs: int) -> tuple[list[int], list[str]] | None:
    pair = infer_product_and_layout_ref_indices(user_prompt, n_refs)
    if not pair:
        return None
    p_ix, l_ix = pair
    indices = [p_ix] if p_ix == l_ix else [p_ix, l_ix]
    modes = _normalize_modes(
        ["identity", "layout_mimic"] if len(indices) > 1 else ["identity"],
        len(indices),
    )
    return indices, modes


def apply_reference_guided_dual_ref_defaults(
    shots: list[dict],
    user_prompt: str,
    n_refs: int,
) -> None:
    """双参考时保证产品图+版式参考都绑定；单张输出也能带上两张上传图。"""
    if n_refs < 2 or not shots:
        return
    binding = _dual_ref_binding(user_prompt, n_refs)
    if not binding:
        return
    indices, modes = binding
    mimic = (
        "Lock product from the identity reference (exact SKU shape, fabric, color). "
        "Replicate composition, crop, layout zones, text/icon placement and scene structure "
        "from the layout reference — swap in the SKU product only; no competitor logos."
    )
    if re.search(r"一模一样|同样|相同构图|same composition|match.*layout", user_prompt, re.I):
        mimic += (
            " Match the layout reference as closely as possible — same crop, zones, and structure; "
            "only the product SKU and allowed text may change."
        )
    for shot in shots:
        cur = shot.get("reference_attachment_indices") or []
        if len(cur) < 2:
            shot["reference_attachment_indices"] = list(indices)
            shot["reference_modes"] = list(modes)
        if any(m in ("layout_mimic", "full_mimic", "style_mimic") for m in (shot.get("reference_modes") or [])):
            shot["reference_payload_canvas_first"] = True
        elif len(shot.get("reference_modes") or []) < len(cur):
            shot["reference_modes"] = _normalize_modes(shot.get("reference_modes"), len(cur))
        old = (shot.get("mimic_instruction_en") or "").strip()
        if len(old) < 80:
            shot["mimic_instruction_en"] = mimic
        if not (shot.get("intent_zh") or "").strip():
            shot["intent_zh"] = (user_prompt or "")[:300]


def _clamp_indices(raw, n_refs: int) -> list[int]:
    out: list[int] = []
    if raw is None:
        return out
    items = raw if isinstance(raw, list) else [raw]
    for item in items:
        try:
            i = int(item)
        except (TypeError, ValueError):
            continue
        if 0 <= i < n_refs and i not in out:
            out.append(i)
    return out


def _normalize_modes(modes, n: int) -> list[str]:
    if not isinstance(modes, list):
        modes = []
    out: list[str] = []
    for m in modes[:n]:
        m = (str(m or "identity").strip().lower())
        if m not in VALID_REFERENCE_MODES:
            m = "identity" if m in ("product", "sku") else "style_mimic"
        out.append(m)
    while len(out) < n:
        out.append("identity" if len(out) == 0 else "style_mimic")
    return out


def _fallback_shots(user_prompt: str, image_count: int, n_refs: int) -> list[dict]:
    """无 LLM 时：尽量解析「第 N 张」；否则均分用户说明。"""
    shots: list[dict] = []
    text = (user_prompt or "").strip()
    by_index: dict[int, str] = {}
    for m in re.finditer(
        r"(?:第\s*(\d+)\s*张|index\s*(\d+)|图\s*(\d+)\s*输出)",
        text,
        re.I,
    ):
        idx = int(m.group(1) or m.group(2) or m.group(3))
        start = m.end()
        nxt = re.search(r"(?:第\s*\d+\s*张|index\s*\d+)", text[start:], re.I)
        chunk = text[start : start + nxt.start()] if nxt else text[start : start + 400]
        by_index[idx] = chunk.strip()[:800]

    dual = _dual_ref_binding(text, n_refs)
    for i in range(1, image_count + 1):
        if dual:
            ref_indices, modes = dual
        else:
            ref_indices = [0] if n_refs > 0 else []
            if n_refs > 1:
                ref_indices = [0, min(1, n_refs - 1)]
            ref_indices = _clamp_indices(ref_indices, n_refs) or ([0] if n_refs else [])
            modes = _normalize_modes(
                ["identity", "layout_mimic"] if len(ref_indices) > 1 else ["identity"],
                len(ref_indices),
            )
        intent = by_index.get(i, f"Output listing frame #{i} per user brief.")
        shots.append(
            {
                "index": i,
                "role": "reference_directed",
                "intent_zh": intent[:200],
                "prompt_en": f"Frame {i}: {intent}",
                "prompt_es": "",
                "reference_attachment_indices": ref_indices,
                "reference_modes": modes,
                "mimic_instruction_en": (
                    "Follow user brief; image 1 locks SKU when present; "
                    "other images guide style/layout only — no competitor logos."
                ),
                "diversity_lock": f"Distinct from other frames in this {image_count}-image set.",
            }
        )
    return shots


def _parse_with_llm(
    user_prompt: str,
    image_count: int,
    product_identity: str,
    product_analysis: dict,
    n_refs: int,
) -> tuple[list[dict], list] | None:
    from chat.services.openai_client import get_openai_client, is_chat_configured

    if not is_chat_configured() or n_refs < 1:
        return None

    system = (
        "你是电商视觉分镜导演。用户上传了多张参考图（按上传顺序编号为 0 到 N-1，"
        "在说明里「图1/图一」= 上传列表 index 0，与「输出的第1张图」不同）。"
        "用户 prompt 描述要输出多少张图、每张做什么、"
        "每张应使用哪些参考（模仿构图/模特/版式/仅锁产品等）。"
        "输出单个 JSON，无 markdown。"
        "字段：reference_roles（可选，每项 index, role, label_zh）；"
        f"shots 长度必须等于 {image_count}；每项含："
        "index, intent_zh, prompt_en（英文生图叙述 ≥80词）, prompt_es（可空）, "
        "reference_attachment_indices（0-based 整数数组，可多张）, "
        "reference_modes（与 indices 等长：identity|style_mimic|layout_mimic|model_mimic|scene_mimic|full_mimic）, "
        "mimic_instruction_en（哪些向参考学习、哪些禁止复制，如无品牌文案）。"
        "不要套用固定九职能模板；完全服从用户分镜。"
        "同一参考图可被多张输出复用；每张输出互不相同。"
    )
    user = "\n".join(
        [
            f"image_count={image_count}",
            f"reference_image_count={n_refs} (indices 0..{n_refs - 1})",
            f"product_identity={product_identity[:3000]}",
            f"product_analysis={json.dumps(product_analysis or {}, ensure_ascii=False)[:8000]}",
            f"user_prompt={user_prompt[:12000]}",
        ]
    )
    try:
        client = get_openai_client()
        resp = client.chat.completions.create(
            model=settings.OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=0.55,
        )
        data = json.loads(resp.choices[0].message.content or "{}")
    except Exception:
        return None

    shots = data.get("shots") or []
    if len(shots) != image_count:
        return None

    roles = data.get("reference_roles")
    out_roles = None
    if isinstance(roles, list) and roles:
        out_roles = []
        for r in roles:
            if not isinstance(r, dict):
                continue
            try:
                ri = int(r.get("index"))
            except (TypeError, ValueError):
                continue
            if 0 <= ri < n_refs:
                out_roles.append(
                    {
                        "index": ri,
                        "role": (r.get("role") or "reference").strip(),
                        "label_zh": (r.get("label_zh") or r.get("label") or "").strip()[:120],
                    }
                )

    normalized: list[dict] = []
    for raw in shots:
        try:
            idx = int(raw.get("index"))
        except (TypeError, ValueError):
            return None
        ref_indices = _clamp_indices(raw.get("reference_attachment_indices"), n_refs)
        if not ref_indices and n_refs:
            ref_indices = [0]
        modes = _normalize_modes(raw.get("reference_modes"), len(ref_indices))
        normalized.append(
            {
                "index": idx,
                "role": "reference_directed",
                "intent_zh": _coerce_text(raw.get("intent_zh"))[:300],
                "prompt_en": _coerce_text(raw.get("prompt_en") or raw.get("intent_zh"))[:4000],
                "prompt_es": _coerce_text(raw.get("prompt_es"))[:500],
                "reference_attachment_indices": ref_indices,
                "reference_modes": modes,
                "mimic_instruction_en": _coerce_text(raw.get("mimic_instruction_en"))[:1500],
                "diversity_lock": _coerce_text(
                    raw.get("diversity_lock"), "Unique vs other frames."
                )[:500],
                "reference_mode": "identity",
            }
        )
    normalized.sort(key=lambda s: int(s.get("index") or 0))
    return normalized, out_roles or []


def build_reference_guided_plan(
    user_prompt: str,
    image_count: int,
    product_identity: str,
    product_analysis: dict | None,
    *,
    reference_attachment_count: int = 0,
) -> dict:
    from generation.services.reference_director_parse import try_parse_upload_map_nine_shots

    analysis = product_analysis or {}
    n_refs = max(0, int(reference_attachment_count))
    reference_roles = []
    shots = None
    plan_source = "fallback"

    explicit = try_parse_upload_map_nine_shots(user_prompt, image_count, n_refs)
    if explicit:
        shots, reference_roles = explicit
        plan_source = "explicit_upload_map"

    if not shots:
        parsed = _parse_with_llm(user_prompt, image_count, product_identity, analysis, n_refs)
        if parsed:
            shots, reference_roles = parsed
            plan_source = "llm"

    if not shots:
        shots = _fallback_shots(user_prompt, image_count, n_refs)
        plan_source = "fallback_rules"

    for shot in shots:
        shot.setdefault("reference_mode", "identity")
        if not shot.get("reference_attachment_indices") and n_refs:
            shot["reference_attachment_indices"] = [0]

    apply_reference_guided_dual_ref_defaults(shots, user_prompt, n_refs)

    plan = {
        "plan_template": "reference_guided",
        "generation_mode": "reference_guided",
        "image_count": image_count,
        "aspect_ratio": "1:1",
        "locale": "user",
        "negative_prompt": REFERENCE_GUIDED_NEGATIVE,
        "subject_lock": user_prompt[:800],
        "reference_attachment_count": n_refs,
        "reference_roles": reference_roles,
        "user_director_prompt": user_prompt[:12000],
        "reference_plan_source": plan_source,
        "shots": shots,
    }
    return plan


def format_reference_guided_preview_markdown(plan: dict) -> str:
    lines = [
        "【参考图导演 · 分镜预览】",
        "按你的提示词解析分镜，不使用 TK 九职能固定模板。",
        f"上传参考图数量：{plan.get('reference_attachment_count', 0)}（编号从 1 起对应上传顺序）",
        f"解析方式：{plan.get('reference_plan_source', 'unknown')}",
        "",
    ]
    roles = plan.get("reference_roles") or []
    if roles:
        lines.append("### 参考图角色（解析）")
        for r in roles:
            lines.append(f"- 图{r.get('index', 0) + 1}：{r.get('label_zh') or r.get('role')}")
        lines.append("")

    for shot in sorted(plan.get("shots") or [], key=lambda s: int(s.get("index") or 0)):
        idx = shot.get("index")
        lines.append(f"### 输出第 {idx} 张")
        if shot.get("intent_zh"):
            lines.append(f"- 意图：{shot['intent_zh']}")
        refs = shot.get("reference_attachment_indices") or []
        modes = shot.get("reference_modes") or []
        if refs:
            ref_human = [f"上传图{i + 1}({modes[j] if j < len(modes) else 'ref'})" for j, i in enumerate(refs)]
            lines.append(f"- 绑定参考：{', '.join(ref_human)}")
        if shot.get("mimic_instruction_en"):
            lines.append(f"- 模仿说明：{shot['mimic_instruction_en'][:400]}")
        pe = (shot.get("prompt_en") or "")[:400]
        if pe:
            lines.append(f"- 生图提示（摘要）：{pe}…" if len(shot.get("prompt_en") or "") > 400 else f"- 生图提示：{pe}")
        lines.append("")
    return "\n".join(lines).strip()
