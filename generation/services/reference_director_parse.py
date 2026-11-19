"""从用户文案解析「上传图角色 + 输出分镜」，避免与 TK 模板或劣质 fallback 混淆。"""

from __future__ import annotations

import re

_MODEL_POSE_VARIANTS = [
    "front full-body studio, arms relaxed",
    "three-quarter left, hand on hip",
    "three-quarter right, slight turn",
    "side profile, clean silhouette",
    "seated on stool, casual pose",
    "walking pose, dynamic fabric drape",
    "close three-quarter, focus on fit and lace detail",
]


def _zh_num_to_int(s: str) -> int | None:
    m = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    s = (s or "").strip()
    if s.isdigit():
        return int(s)
    return m.get(s)


def _detect_upload_ref_roles(text: str, n_refs: int) -> dict[int, str]:
    """上传图序号 → 角色（0-based index）。"""
    roles: dict[int, str] = {}
    patterns = [
        (r"图\s*([一二三四1234])\s*是[^，。；\n]{0,24}(产品|商品|sku)", "product_sku"),
        (r"图\s*([一二三四1234])\s*是[^，。；\n]{0,32}(首图|主图|引流)", "style_hero"),
        (r"图\s*([一二三四1234])\s*是[^，。；\n]{0,24}(模特|model)", "style_model"),
        (r"图\s*([一二三四1234])\s*是[^，。；\n]{0,24}(尺码|size)", "layout_size"),
    ]
    for pat, role in patterns:
        for m in re.finditer(pat, text, re.I):
            raw = m.group(1)
            idx = _zh_num_to_int(raw)
            if idx is None:
                continue
            ui = idx - 1
            if 0 <= ui < n_refs:
                roles[ui] = role
    return roles


def _pick_ref(roles: dict[int, str], role: str, default: int, n_refs: int) -> int:
    for i, r in roles.items():
        if r == role:
            return i
    return default if 0 <= default < n_refs else 0


def try_parse_upload_map_nine_shots(
    user_prompt: str,
    image_count: int,
    n_refs: int,
) -> tuple[list[dict], list[dict]] | None:
    """
    识别常见结构：上传 图1 产品 / 图2 首图 / 图3 模特 / 图4 尺码；
    输出 9 张 = 1 首图 + 1 尺码 + 7 模特（可由文案触发，非硬编码品类）。
    """
    if image_count != 9 or n_refs < 2:
        return None
    text = (user_prompt or "").replace("\r", "")
    upload_roles_map = _detect_upload_ref_roles(text, n_refs)

    want_hero = bool(
        re.search(r"第一[张个幅]|首张|首图", text)
        and re.search(r"模仿|按|参照", text)
        and re.search(r"首图|主图", text)
    )
    want_size = bool(re.search(r"尺码|size\s*chart|talla", text, re.I)) and bool(
        re.search(r"第二[张个幅]|一张.*尺码|1\s*张.*尺码", text)
    )
    want_models = bool(
        re.search(r"其余\s*七|7\s*张|七张|模特", text) and re.search(r"模特|穿着|内衣", text)
    )

    has_upload_labels = len(upload_roles_map) >= 2 or bool(
        re.search(r"图\s*[1-4一二三四]\s*是", text)
    )
    if not has_upload_labels or not (want_hero or want_models):
        return None

    ref_product = _pick_ref(upload_roles_map, "product_sku", 0, n_refs)
    ref_hero = _pick_ref(upload_roles_map, "style_hero", 1 if n_refs > 1 else 0, n_refs)
    ref_model = _pick_ref(upload_roles_map, "style_model", 2 if n_refs > 2 else ref_hero, n_refs)
    ref_size = _pick_ref(upload_roles_map, "layout_size", 3 if n_refs > 3 else ref_product, n_refs)

    reference_roles = []
    labels = {
        "product_sku": "产品图",
        "style_hero": "首图风格参考",
        "style_model": "模特图风格参考",
        "layout_size": "尺码图版式参考",
    }
    for i in range(n_refs):
        role = upload_roles_map.get(i, "reference")
        reference_roles.append(
            {"index": i, "role": role, "label_zh": labels.get(role, f"参考图{i + 1}")}
        )

    shots: list[dict] = []

    def _shot(
        idx: int,
        intent_zh: str,
        prompt_en: str,
        ref_ix: list[int],
        modes: list[str],
        mimic: str,
        diversity: str,
    ) -> dict:
        return {
            "index": idx,
            "role": "reference_directed",
            "intent_zh": intent_zh,
            "prompt_en": prompt_en,
            "prompt_es": "",
            "reference_attachment_indices": ref_ix,
            "reference_modes": modes,
            "mimic_instruction_en": mimic,
            "diversity_lock": diversity,
            "reference_mode": "identity",
        }

    shots.append(
        _shot(
            1,
            "首图：模仿上传首图参考的版式与氛围，产品来自产品参考",
            (
                "E-commerce hero listing image: recreate the LAYOUT, lighting, typography ZONES, badges, "
                "and model-plus-product composition from style reference image 2 — but hero SKU colors/packaging "
                "must match product reference image 1 (pick one clear colorway from pack if multiple). "
                "Do NOT copy competitor brand text from style ref. Single photograph, scroll-stopper quality."
            ),
            [ref_product, ref_hero] if n_refs > 1 else [ref_product],
            ["identity", "style_mimic"] if n_refs > 1 else ["identity"],
            "Style ref = composition/badges/background mood only; product ref = exact SKU.",
            "Hero frame — not a white catalog shot.",
        )
    )

    if want_size and n_refs > 1:
        size_refs = [ref_product, ref_size]
        size_modes = ["identity", "layout_mimic"]
        if ref_size == ref_product:
            size_refs = [ref_product]
            size_modes = ["identity"]
        shots.append(
            _shot(
                2,
                "尺码表图：模仿尺码参考的版式结构",
                (
                    "Size chart / fit guide image: match the TABLE LAYOUT and information architecture "
                    "from size-chart reference — region labels, measurement diagrams, grid structure. "
                    "Product thumbnails or line art must reflect SKU from product reference. "
                    "Legible at mobile size. NOT a lifestyle model photo."
                ),
                size_refs,
                size_modes,
                "Layout ref defines grid; product ref defines garment silhouette for diagrams.",
                "Infographic layout — differs from hero and model frames.",
            )
        )

    model_start = len(shots) + 1
    for j, out_idx in enumerate(range(model_start, 10)):
        pose = _MODEL_POSE_VARIANTS[j % len(_MODEL_POSE_VARIANTS)]
        refs = [ref_product, ref_model] if n_refs > 1 else [ref_product]
        modes = ["identity", "model_mimic"] if n_refs > 1 else ["identity"]
        shots.append(
            _shot(
                out_idx,
                f"模特展示图 {out_idx - model_start + 1}/7：穿着产品参考同款，氛围模仿模特参考",
                (
                    f"Apparel model photo #{out_idx - model_start + 1}/7: female model wearing the exact lingerie "
                    f"SKU from product reference — {pose}. Match studio lighting, background simplicity, "
                    f"and commercial lingerie presentation style from model reference image. "
                    f"New model identity; do not copy face from references. Single 1:1 photo."
                ),
                refs,
                modes,
                "Model ref = lighting/pose type/studio mood; product ref = garment color and design.",
                f"Pose variant: {pose} — must differ from other model frames.",
            )
        )

    if len(shots) != 9:
        return None
    return shots, reference_roles
