"""职能 / 槽位 → 允许的动作 ID（白名单）。未知 role 走通用池。"""

from __future__ import annotations

from generation.services.action_planning.catalog import GENERIC_ACTION_IDS

# 白底 / 合规：只允许稳妥陈列，禁止液体、人物、开盖messy
_WHITE_BG = ("G01", "G02")
_HERO = ("G01", "G02", "G03", "G06", "G07", "B03")
_PAIN = ("G03", "G05", "G08", "B07", "B11")
_USP_PRIMARY = ("G04", "G05", "B05", "B08", "B09")
_USP_SECONDARY = ("G02", "G04", "G06", "G07", "B04", "B07")
_TRUST = ("G03", "G08", "B11")
_EASE = ("G05", "G08", "B11")
_VALUE = ("G06", "G07", "B04")
_PAYOFF = ("G03", "G05", "G08", "B11")

ROLE_ALLOWED: dict[str, tuple[str, ...]] = {
    "hero_hook": _HERO,
    "white_bg_catalog": _WHITE_BG,
    "pain_empathy": _PAIN,
    "usp_primary": _USP_PRIMARY,
    "usp_secondary": _USP_SECONDARY,
    "trust_quality": _TRUST,
    "ease_objection": _EASE,
    "value_stack": _VALUE,
    "lifestyle_payoff": _PAYOFF,
    "multi_variant_showcase": ("G06", "G01", "G02"),
    "photo_refine": (),
    "reference_directed": (),
}

# 通用套图按 index 的弱槽位（不改 shot.role）
GENERIC_SLOT_BY_MOD: tuple[tuple[str, ...], ...] = (
    _HERO,  # 1
    _WHITE_BG,  # 2 if present
    _PAIN,
    _USP_PRIMARY,
    _USP_SECONDARY,
    _TRUST,
    _EASE,
    _VALUE,
    _PAYOFF,
)


def allowed_action_ids_for_shot(
    shot: dict,
    *,
    plugin_ids: tuple[str, ...],
    shot_ordinal: int,
) -> tuple[str, ...]:
    role = (shot.get("role") or "").strip()
    if role in ROLE_ALLOWED:
        wanted = ROLE_ALLOWED[role]
    else:
        slot = GENERIC_SLOT_BY_MOD[(max(0, shot_ordinal - 1)) % len(GENERIC_SLOT_BY_MOD)]
        wanted = slot
    plugin_set = set(plugin_ids)
    # 白名单 ∩ 当前插件；白名单里的美妆增量若不在插件则丢掉
    filtered = tuple(a for a in wanted if a in plugin_set)
    if filtered:
        return filtered
    # 回退：插件内的通用 8
    generic = tuple(a for a in GENERIC_ACTION_IDS if a in plugin_set)
    return generic or plugin_ids
