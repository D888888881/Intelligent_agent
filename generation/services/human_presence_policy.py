"""九图人物出现频率：按批次动态预算，避免每套都 ~5 张出人。"""

from __future__ import annotations

from generation.services.shot_diversity_constants import CREATIVE_DETAIL_INDICES

# 批次轮换：同一 SKU 不同套图切换「人多少 / 故事多少」
HUMAN_BUDGET_PROFILES: list[dict] = [
    {
        "name": "product_story_heavy",
        "max_face_frames": 1,
        "max_hands_frames": 1,
        "max_human_touch_frames": 2,
        "hero_prefer": "product",
        "frame4_human": "none",
    },
    {
        "name": "balanced_light",
        "max_face_frames": 2,
        "max_hands_frames": 1,
        "max_human_touch_frames": 3,
        "hero_prefer": "product",
        "frame4_human": "none",
    },
    {
        "name": "minimal_human",
        "max_face_frames": 1,
        "max_hands_frames": 1,
        "max_human_touch_frames": 2,
        "hero_prefer": "product",
        "frame4_human": "none",
    },
    {
        "name": "one_face_demo",
        "max_face_frames": 1,
        "max_hands_frames": 1,
        "max_human_touch_frames": 2,
        "hero_prefer": "either",
        "frame4_human": "hands",
    },
]

# 超预算时优先去掉人物（保留产品/材质/故事帧）
_STRIP_HUMAN_PRIORITY: list[tuple[int, str]] = [
    (9, "lifestyle_payoff"),
    (3, "pain_empathy"),
    (1, "hero_hook"),
    (4, "usp_primary"),
]

_PROTECT_HUMAN_FRAME7_ROLES = frozenset({"ease_objection", "lifestyle_payoff"})


def resolve_human_budget(batch_index: int, pack: dict | None = None) -> dict:
    pack = pack or {}
    profile = HUMAN_BUDGET_PROFILES[int(batch_index) % len(HUMAN_BUDGET_PROFILES)]
    out = dict(profile)
    if pack.get("human_budget_override"):
        out.update(pack["human_budget_override"])
    return out


def _mode_weight(mode: str) -> tuple[bool, bool]:
    m = (mode or "").strip().lower()
    if m in ("none", "no", "product", ""):
        return False, False
    if m == "hands":
        return True, False
    if m in ("face", "full"):
        return True, True
    return True, True


def _set_mode(shot: dict, mode: str) -> None:
    if shot.get("human_cast_mandatory") or (shot.get("human_cast_mandatory_en") or "").strip():
        return
    shot["human_cast_mode"] = mode
    if mode == "none":
        shot.pop("human_model_lock", None)
        shot.pop("talent_id", None)
        shot["_force_hands_only"] = False
        note = (
            "NO HUMAN — Product, material, environment, or infographic story only; "
            "no face, no hands, no model."
        )
        shot["action_lock"] = f"{shot.get('action_lock', '')} {note}".strip()
    elif mode == "hands":
        shot["_force_hands_only"] = True


def apply_human_presence_policy(plan: dict, *, pack: dict, batch_index: int) -> dict:
    from generation.services.listing_bundle import is_listing_ecommerce_plan

    if not is_listing_ecommerce_plan(plan):
        return plan

    budget = resolve_human_budget(batch_index, pack)
    plan["human_presence_budget"] = budget
    plan["human_presence_budget_name"] = budget.get("name", "default")

    shots = plan.get("shots") or []
    by_idx = {int(s.get("index") or 0): s for s in shots if s.get("index")}

    hero = by_idx.get(1)
    if hero and hero.get("role") == "hero_hook":
        prefer = (budget.get("hero_prefer") or "either").lower()
        pack_hero = bool(pack.get("hero_human", True))
        if prefer == "product" or not pack_hero:
            _set_mode(hero, "none")
            hero.setdefault(
                "diversity_lock",
                "Hero — product-only scroll stopper; bold typography space; no model face.",
            )
        elif prefer == "either" and pack_hero:
            hero.setdefault("human_cast_mode", "full")

    frame4 = by_idx.get(4)
    if frame4 and frame4.get("role") == "usp_primary":
        tpl = (plan.get("plan_template") or "").strip()
        needs_model = bool(frame4.get("human_cast_mandatory"))
        if tpl == "tk_mx_ecommerce_9":
            needs_model = needs_model or frame4.get("human_cast_mode") not in (None, "", "none", "unset")
        if needs_model:
            frame4["human_cast_mandatory"] = True
            if (frame4.get("human_cast_mode") or "").lower() in ("none", "", "unset"):
                zone = (plan.get("product_analysis") or {}).get("application_zone") or ""
                if zone == "body_bath":
                    frame4["human_cast_mode"] = "full"
                elif zone == "hair":
                    frame4["human_cast_mode"] = "hair"
                else:
                    frame4["human_cast_mode"] = "face"
            if not (frame4.get("frame4_authoritative_en") or "").strip():
                frame4["transformation_story_lock"] = (
                    "PAIN TRANSFORMATION — Single-frame before→after on a MODEL using the product on the "
                    "correct application zone; WITHOUT comparison captions (no antes/después) and WITHOUT overlay "
                    "marketing text. Visible transformation on person + SKU in frame — NOT product-only still life."
                )
        else:
            frame4["human_cast_mandatory"] = False
            frame4["human_cast_mode"] = "none"
            frame4["transformation_story_lock"] = (
                "SURFACE TRANSFORMATION — Single-frame before→after on the cleaned object/surface "
                "(toilet bowl, tile, etc.) with hero cleaner SKU; NO human model; "
                "no antes/después text; NOT skin or hair compare."
            )

    frame5 = by_idx.get(5)
    if frame5 and frame5.get("role") == "usp_secondary":
        _set_mode(frame5, "none")

    face_n = 0
    hands_n = 0
    touch_n = 0

    def _count_shot(shot: dict) -> None:
        nonlocal face_n, hands_n, touch_n
        touch, face = _mode_weight(shot.get("human_cast_mode") or "")
        if not touch:
            return
        touch_n += 1
        mode = (shot.get("human_cast_mode") or "").lower()
        if mode == "hands":
            hands_n += 1
        elif mode in ("face", "full"):
            face_n += 1

    for shot in shots:
        _count_shot(shot)

    max_face = int(budget.get("max_face_frames", 2))
    max_hands = int(budget.get("max_hands_frames", 1))
    max_touch = int(budget.get("max_human_touch_frames", 3))

    def _over_budget() -> bool:
        return face_n > max_face or hands_n > max_hands or touch_n > max_touch

    while _over_budget():
        stripped = False
        for idx, role in _STRIP_HUMAN_PRIORITY:
            shot = by_idx.get(idx)
            if not shot or (shot.get("role") or "") != role:
                continue
            if idx == 7 and (role in _PROTECT_HUMAN_FRAME7_ROLES or role == "ease_objection"):
                continue
            if idx == 6 and (shot.get("human_cast_mode") or "").lower() in ("face", "full"):
                continue
            if idx == 4 and shot.get("human_cast_mandatory"):
                continue
            if shot.get("human_cast_mandatory") or (shot.get("human_cast_mandatory_en") or "").strip():
                continue
            mode = (shot.get("human_cast_mode") or "").lower()
            if mode == "none":
                continue
            if mode in ("face", "full"):
                _set_mode(shot, "none")
            elif mode == "hands":
                _set_mode(shot, "none")
            else:
                _set_mode(shot, "none")
            face_n = hands_n = touch_n = 0
            for s in shots:
                _count_shot(s)
            stripped = True
            break
        if not stripped:
            break

    summary_parts: list[str] = []
    for shot in sorted(shots, key=lambda s: int(s.get("index") or 0)):
        idx = int(shot.get("index") or 0)
        mode = (shot.get("human_cast_mode") or "unset").lower()
        if mode not in ("none", "unset", ""):
            summary_parts.append(f"#{idx}={mode}")

    plan["human_presence_summary"] = ", ".join(summary_parts) or "product-only set"
    plan["human_presence_budget_en"] = (
        f"HUMAN FREQUENCY — This listing batch allows at most {max_face} face/full frame(s), "
        f"{max_hands} hands-only frame(s), {max_touch} total human-touch frames. "
        f"Current plan: {plan['human_presence_summary']}. "
        "Do NOT add extra models in frames marked product-only."
    )
    plan["shots"] = shots
    return plan
