"""通用 8 动作母版 + 美妆增量。ID 稳定，供套内去重与策划预览。"""

from __future__ import annotations

from typing import Any

ACTION_CATALOG_VERSION = "1.0"

# 全类目共享：具体表现偏物理/构图，不绑 SKU 品类话术
GENERIC_ACTIONS: dict[str, dict[str, Any]] = {
    "G01": {
        "label_zh": "正面陈列",
        "label_en": "Front catalog display",
        "tier": "safe",
        "requires_human": False,
        "lock_en": (
            "PRODUCT ACTION G01 — Front-facing catalog display: hero SKU upright, label readable, "
            "centered or slightly off-center; stable base on a surface — no floating bottle, no collage."
        ),
    },
    "G02": {
        "label_zh": "立体角度",
        "label_en": "Angled 3/4 display",
        "tier": "safe",
        "requires_human": False,
        "lock_en": (
            "PRODUCT ACTION G02 — 35–50° three-quarter view showing depth, side profile, and front together; "
            "product grounded; not a duplicate of a dead-on packshot."
        ),
    },
    "G03": {
        "label_zh": "环境摆放",
        "label_en": "Environment placement",
        "tier": "safe",
        "requires_human": False,
        "lock_en": (
            "PRODUCT ACTION G03 — Product placed in a believable real-life setting at natural scale; "
            "may recline, tilt, or lay on surface per PRODUCT PHYSICAL POSE — NOT default upright tube; "
            "environment is background, product remains hero."
        ),
    },
    "G04": {
        "label_zh": "材质微距",
        "label_en": "Material / texture macro",
        "tier": "medium",
        "requires_human": False,
        "lock_en": (
            "PRODUCT ACTION G04 — Tight macro or close crop of material, texture, craft, or interface; "
            "SKU still identifiable; not a white-catalog clone; single photo not a grid."
        ),
    },
    "G05": {
        "label_zh": "使用互动",
        "label_en": "In-use interaction",
        "tier": "medium",
        "requires_human": True,
        "lock_en": (
            "PRODUCT ACTION G05 — Hands or body interacting with the product in a real use moment "
            "(hold, wear, press, pour as appropriate); product clearly visible; one action only."
        ),
    },
    "G06": {
        "label_zh": "组合陈列",
        "label_en": "Set / kit lineup",
        "tier": "safe",
        "requires_human": False,
        "lock_en": (
            "PRODUCT ACTION G06 — Kit, colorways, or series arranged as one still-life lineup; "
            "each unit matches identity; single photograph, not a contact-sheet collage."
        ),
    },
    "G07": {
        "label_zh": "包装配件",
        "label_en": "Packaging and accessories",
        "tier": "safe",
        "requires_human": False,
        "lock_en": (
            "PRODUCT ACTION G07 — Box, sleeve, lid, or accessories staged with the hero SKU; "
            "packaging print matches reference; not empty gift styling without product."
        ),
    },
    "G08": {
        "label_zh": "场景氛围",
        "label_en": "Lifestyle context",
        "tier": "medium",
        "requires_human": False,
        "lock_en": (
            "PRODUCT ACTION G08 — Lifestyle or ritual atmosphere around the product "
            "(home, commute, workspace, outdoors as fits category); product still readable; not a people-only portrait."
        ),
    },
}

# 美妆增量：在通用 8 之上增加质地/开盖/成分/水感/SPA 等（ID 不以 G 复用）
BEAUTY_INCREMENT: dict[str, dict[str, Any]] = {
    "B03": {
        "label_zh": "倾斜陈列",
        "label_en": "Supported tilt display",
        "tier": "medium",
        "requires_human": False,
        "lock_en": (
            "PRODUCT ACTION B03 — Product tilted with a visible physical support "
            "(acrylic rest, fabric fold, lid as stand); gravity-honest — never a floating bottle."
        ),
    },
    "B04": {
        "label_zh": "开盖结构",
        "label_en": "Open cap / inner structure",
        "tier": "medium",
        "requires_human": False,
        "lock_en": (
            "PRODUCT ACTION B04 — Cap, pump, or lid opened to reveal mouth, applicator, or inner structure; "
            "parts rest on a surface; SKU identity still locked to reference."
        ),
    },
    "B05": {
        "label_zh": "挤出质地",
        "label_en": "Extruded cream / liquid",
        "tier": "hard",
        "requires_human": False,
        "lock_en": (
            "PRODUCT ACTION B05 — Show true product texture leaving the pack "
            "(cream swirl, gel ribbon, serum drop, lotion bead) beside the closed or mid-dispense SKU; "
            "texture color must match the real formula, not generic white cream."
        ),
    },
    "B07": {
        "label_zh": "成分整图",
        "label_en": "Full-frame ingredients only",
        "tier": "medium",
        "requires_human": False,
        "lock_en": (
            "PRODUCT ACTION B07 — INGREDIENT-ONLY COMPOSITION: fill the entire frame with real ingredient "
            "still-life (botanical slices, droplets, minerals, honey, oils, powders) matching the formula story. "
            "NO product bottle, NO packaging, NO SKU, NO brand label in frame — ingredients only edge-to-edge."
        ),
    },
    "B08": {
        "label_zh": "质地微距",
        "label_en": "Formula texture macro",
        "tier": "hard",
        "requires_human": False,
        "lock_en": (
            "PRODUCT ACTION B08 — Extreme close-up of cream, gel, oil, or powder texture "
            "(peaks, sheen, bubbles) with the SKU still in frame or immediately adjacent; not a white packshot."
        ),
    },
    "B09": {
        "label_zh": "水感动态",
        "label_en": "Water / foam motion",
        "tier": "hard",
        "requires_human": False,
        "lock_en": (
            "PRODUCT ACTION B09 — Water droplets, splash, mist, or foam interacting with the SKU; "
            "physics-plausible wet surfaces; product label still readable; freeze a single moment, no collage."
        ),
    },
    "B11": {
        "label_zh": "SPA / 护理场景",
        "label_en": "Spa / bathroom ritual",
        "tier": "medium",
        "requires_human": False,
        "lock_en": (
            "PRODUCT ACTION B11 — Bathroom vanity, towel, steam, or spa-care still-life; "
            "warm ritual mood; product on a real surface at believable scale; not a clinical lab."
        ),
    },
}

# 美妆预览别名：通用 ID 在美妆语境下的中文母版名（不新增分配 ID）
BEAUTY_DISPLAY_ALIAS: dict[str, dict[str, str]] = {
    "G01": {"beauty_id": "B01", "label_zh": "正面展示"},
    "G02": {"beauty_id": "B02", "label_zh": "角度展示"},
    "G05": {"beauty_id": "B06", "label_zh": "人物使用"},
    "G06": {"beauty_id": "B10", "label_zh": "多瓶组合"},
    "G07": {"beauty_id": "B12", "label_zh": "包装展示"},
}

GENERIC_ACTION_IDS: tuple[str, ...] = tuple(GENERIC_ACTIONS.keys())
BEAUTY_INCREMENT_IDS: tuple[str, ...] = tuple(BEAUTY_INCREMENT.keys())

# 美妆池 = 通用 8 + 增量（B06 走 G05）
BEAUTY_POOL_IDS: tuple[str, ...] = GENERIC_ACTION_IDS + BEAUTY_INCREMENT_IDS


def action_by_id(action_id: str) -> dict[str, Any] | None:
    aid = (action_id or "").strip()
    if aid in GENERIC_ACTIONS:
        return {"id": aid, **GENERIC_ACTIONS[aid]}
    if aid in BEAUTY_INCREMENT:
        return {"id": aid, **BEAUTY_INCREMENT[aid]}
    return None


def display_label_zh(action_id: str, *, beauty: bool) -> str:
    row = action_by_id(action_id)
    if not row:
        return action_id or "—"
    if beauty and action_id in BEAUTY_DISPLAY_ALIAS:
        alias = BEAUTY_DISPLAY_ALIAS[action_id]
        return f"{alias['label_zh']}（{alias['beauty_id']}）"
    return f"{row['label_zh']}（{action_id}）"
