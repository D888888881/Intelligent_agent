"""九张套图互斥机位 / 产品朝向；按套图批次轮换整组视角预设。"""

from __future__ import annotations

# index 1–9 默认机位（批次 0）
CAMERA_SPEC_BY_INDEX: dict[int, dict[str, str]] = {
    1: {
        "code": "low_3q_front_right",
        "short": "low 3/4 front-right",
        "orientation": (
            "Camera at knee height, 25° upward tilt. Product rotated ~35° clockwise from straight front; "
            "show front-right bevel and depth; hero fills 55–65% frame."
        ),
        "mandate": (
            "CAMERA MANDATE — Low-angle three-quarter from front-right; NOT straight-on, NOT same as reference photo."
        ),
    },
    2: {
        "code": "front_catalog",
        "short": "straight front catalog",
        "orientation": (
            "Eye-level, perfectly centered straight-on front; symmetrical catalog view; pure white seamless; "
            "full label facing camera."
        ),
        "mandate": (
            "CAMERA MANDATE — Straight-on front catalog only; eye-level; centered; compliance white background."
        ),
    },
    3: {
        "code": "env_3q_back_left",
        "short": "wide 3/4 back-left",
        "orientation": (
            "Wide environmental still-life; camera at chest height from back-left (~135° from front); "
            "product occupies ~35% frame; show rear/side panel of packaging in context."
        ),
        "mandate": (
            "CAMERA MANDATE — Wide shot from back-left quarter; product partly turned away from front; lifestyle props."
        ),
    },
    4: {
        "code": "elevated_3q_front_left",
        "short": "elevated 3/4 front-left",
        "orientation": (
            "Camera 45° above product, viewing from front-left; asymmetric layout for before→after visual contrast; "
            "show top + front-left face; NOT the same rotation as frames 1 or 2."
        ),
        "mandate": (
            "CAMERA MANDATE — Elevated three-quarter from front-left; asymmetric transformation layout; "
            "NOT profile, NOT top-down, NOT straight front catalog."
        ),
    },
    5: {
        "code": "side_profile_90_right",
        "short": "90° right side profile",
        "orientation": (
            "True 90° side profile from the RIGHT; label edge and side panel visible; "
            "product centered vertically; flat studio or gradient backdrop."
        ),
        "mandate": (
            "CAMERA MANDATE — Pure right-side profile (90°); no three-quarter; different from hero and catalog."
        ),
    },
    6: {
        "code": "wide_env_trust_3q",
        "short": "wide env chest 3/4",
        "orientation": (
            "Wide Mexican daily-life room; camera at chest height, 3/4 from front-left; "
            "product on shelf/counter ~30–40% frame; environment readable; NOT macro, NOT straight packshot."
        ),
        "mandate": (
            "CAMERA MANDATE — Wide trust scene 3/4; product in real room context; NOT label macro, NOT frame-2 front."
        ),
    },
    7: {
        "code": "table_3q_front_left",
        "short": "table-level 3/4 front-left",
        "orientation": (
            "Table-height camera, three-quarter from front-left (mirror opposite of frame 1); "
            "product beside simple props; mid-frame hero; show front-left and top edge."
        ),
        "mandate": (
            "CAMERA MANDATE — Table-level 3/4 front-left; opposite facing from frame 1; usage context."
        ),
    },
    8: {
        "code": "topdown_90",
        "short": "90° top-down flat lay",
        "orientation": (
            "Bird's-eye 90° top-down; lid/cap facing camera; flat lay with kit items; "
            "organized grid; warm surface texture."
        ),
        "mandate": (
            "CAMERA MANDATE — Strict top-down 90° bird's eye; only frame allowed to use this angle."
        ),
    },
    9: {
        "code": "wide_3q_back_right",
        "short": "wide 3/4 back-right lifestyle",
        "orientation": (
            "Wide 28mm lifestyle; camera from back-right (~225° from front); product in lower third; "
            "aspirational background; show back-right shoulder of pack."
        ),
        "mandate": (
            "CAMERA MANDATE — Wide lifestyle from back-right quarter; product small in frame; NOT packshot."
        ),
    },
}

# 同 index 在不同套图批次下替换整段机位（batch_index % N）
CAMERA_RING_BY_INDEX: dict[int, list[dict[str, str]]] = {
    1: [
        {},
        {
            "code": "high_3q_back_left",
            "short": "high 3/4 back-left",
            "orientation": (
                "Camera above eye level from back-left; product rotated ~50° showing back-left panel and depth; "
                "bold diagonal shadow; hero 50% frame."
            ),
            "mandate": "CAMERA MANDATE — High three-quarter from back-left; dramatic retail scroll-stopper.",
        },
        {
            "code": "worm_eye_front_right",
            "short": "worm's-eye front-right",
            "orientation": (
                "Camera on surface, extreme low angle looking up at product from front-right; "
                "monumental scale, sky/gradient backdrop."
            ),
            "mandate": "CAMERA MANDATE — Worm's-eye low angle; NEVER duplicate catalog straight-on.",
        },
        {
            "code": "dutch_3q_front",
            "short": "dutch tilt 3/4 front",
            "orientation": (
                "Slight dutch tilt; product 40° from front; dynamic editorial; asymmetric Spanish headline space."
            ),
            "mandate": "CAMERA MANDATE — Dutch-angle dynamic hero; product rotation ≠ reference photo.",
        },
        {
            "code": "wide_24mm_front_left",
            "short": "wide 24mm front-left",
            "orientation": (
                "Wide 24mm from front-left; product in foreground 40%; exaggerated perspective lines in scene layers."
            ),
            "mandate": "CAMERA MANDATE — Wide-angle layered hero; deep perspective.",
        },
        {
            "code": "tele_85mm_front_right",
            "short": "tele 85mm front-right",
            "orientation": (
                "85mm compression from front-right; product sharp, background bokeh; premium isolation."
            ),
            "mandate": "CAMERA MANDATE — Telephoto compressed hero; shallow DOF.",
        },
    ],
    2: [
        {},
        {
            "code": "front_catalog_slight_low",
            "short": "front catalog slight low",
            "orientation": (
                "Straight-on white seamless; camera 10° below eye-level; product centered; full label visible."
            ),
            "mandate": "CAMERA MANDATE — Compliance white; only micro tilt vs batch-0 catalog.",
        },
        {
            "code": "front_catalog_slight_high",
            "short": "front catalog slight high",
            "orientation": (
                "Straight-on white seamless; camera 10° above eye-level; symmetrical; full label visible."
            ),
            "mandate": "CAMERA MANDATE — Compliance white; elevated catalog only.",
        },
    ],
    3: [
        {},
        {
            "code": "macro_30_front",
            "short": "macro 30° front",
            "orientation": "Controlled macro 30° on hero SKU; tight crop; shallow DOF; not full room.",
            "mandate": "CAMERA MANDATE — Macro detail angle; differs from wide env default.",
        },
        {
            "code": "wide_env_back_right",
            "short": "wide env back-right",
            "orientation": "Wide still-life from back-right; product ~30% frame; rear label glimpse.",
            "mandate": "CAMERA MANDATE — Back-right environmental; opposite of batch-0 back-left.",
        },
        {
            "code": "low_table_3q",
            "short": "low table 3/4",
            "orientation": "Table-level low 3/4 from front; product dominant; props on same plane.",
            "mandate": "CAMERA MANDATE — Low table narrative angle.",
        },
        {
            "code": "overhead_45",
            "short": "45° overhead oblique",
            "orientation": "Oblique 45° overhead (NOT 90° flat lay); show top + front face together.",
            "mandate": "CAMERA MANDATE — Oblique overhead; not frame-8 bird's eye.",
        },
        {
            "code": "side_env_left",
            "short": "side env left",
            "orientation": "90° left profile in lifestyle context; environmental props; not studio profile like frame 5.",
            "mandate": "CAMERA MANDATE — Left profile in scene; not white catalog.",
        },
    ],
    4: [
        {},
        {
            "code": "split_light_low_right",
            "short": "low 3/4 back-right split",
            "orientation": "Low angle from back-right; split lighting for before/after metaphor; asymmetric halves.",
            "mandate": "CAMERA MANDATE — Low back-right transformation split.",
        },
        {
            "code": "eye_level_profile_contrast",
            "short": "eye-level lateral contrast",
            "orientation": "Eye-level lateral view; transformation via color grade left vs right; product centered.",
            "mandate": "CAMERA MANDATE — Lateral eye-level contrast layout.",
        },
        {
            "code": "top_oblique_transform",
            "short": "top oblique transform",
            "orientation": "30° above table; transformation story top-down oblique; not 90° flat.",
            "mandate": "CAMERA MANDATE — Oblique top transformation.",
        },
    ],
    5: [
        {},
        {
            "code": "side_profile_90_left",
            "short": "90° left side profile",
            "orientation": "True 90° side profile from LEFT; opposite facing from batch-0 right profile.",
            "mandate": "CAMERA MANDATE — Left side profile 90°.",
        },
        {
            "code": "rear_3q_show_back",
            "short": "rear 3/4 show back panel",
            "orientation": "Rear three-quarter; show back-of-pack graphics and barcode zone; studio gradient.",
            "mandate": "CAMERA MANDATE — Rear 3/4 informational angle.",
        },
        {
            "code": "low_front_3q_specs",
            "short": "low front 3/4 specs",
            "orientation": "Low front three-quarter for specs/infographic; label readable; not catalog center.",
            "mandate": "CAMERA MANDATE — Low 3/4 specs hero.",
        },
    ],
    6: [
        {},
        {
            "code": "street_cafe_wide",
            "short": "street café wide",
            "orientation": "Outdoor Mexico café table wide shot; product mid-frame; street bokeh.",
            "mandate": "CAMERA MANDATE — Outdoor trust scene; not indoor default.",
        },
        {
            "code": "bathroom_shelf_eye",
            "short": "bathroom shelf eye-level",
            "orientation": "Eye-level bathroom shelf; product among toiletries; warm steam light.",
            "mandate": "CAMERA MANDATE — Vanity shelf trust angle.",
        },
        {
            "code": "kitchen_counter_wide",
            "short": "kitchen counter wide",
            "orientation": "Kitchen counter wide 28mm; tiled backsplash; morning sun.",
            "mandate": "CAMERA MANDATE — Kitchen lifestyle trust.",
        },
    ],
    7: [
        {},
        {
            "code": "ugc_phone_height",
            "short": "UGC phone capture height",
            "orientation": "Handheld phone height ~1.1m; slight wide; candid TikTok framing; subject off-center.",
            "mandate": "CAMERA MANDATE — UGC phone POV; not studio glamour.",
        },
        {
            "code": "sofa_lifestyle_3q",
            "short": "sofa lifestyle 3/4",
            "orientation": "Living room sofa 3/4; casual use moment; window light from right.",
            "mandate": "CAMERA MANDATE — Sofa lifestyle seeding angle.",
        },
    ],
    8: [
        {},
        {
            "code": "angled_shelf_45",
            "short": "angled shelf 45°",
            "orientation": "45° angled shelf layout (NOT 90° top-down); kit items staggered in depth.",
            "mandate": "CAMERA MANDATE — Angled shelf kit layout; only one flat 90° in set is frame 8 batch-0.",
        },
        {
            "code": "table_scatter_oblique",
            "short": "table scatter oblique",
            "orientation": "Oblique scatter on wood table; shallow depth; warm premium.",
            "mandate": "CAMERA MANDATE — Oblique value layout.",
        },
    ],
    9: [
        {},
        {
            "code": "golden_hour_park",
            "short": "golden hour outdoor",
            "orientation": "Outdoor golden hour; product on bench/grass; wide 35mm; aspirational.",
            "mandate": "CAMERA MANDATE — Outdoor payoff wide.",
        },
        {
            "code": "night_city_bokeh",
            "short": "night city bokeh",
            "orientation": "Night city lights bokeh; product sharp foreground; cool-warm contrast.",
            "mandate": "CAMERA MANDATE — Urban night payoff.",
        },
    ],
}

_CREATIVE_INDICES = frozenset({3, 6, 7, 8, 9})

ANGLE_NEGATIVE = (
    "copying reference photo camera angle, same product rotation as reference, "
    "duplicate facing direction as other listing frames, minor 5–15 degree tweak only, "
    "all nine images front-facing packshot, repeating the same three-quarter hero angle"
)

LISTING_ANGLE_DIVERSITY_EN = (
    "LISTING CAMERA DIVERSITY — All 9 frames MUST use visibly different camera height, distance, "
    "and product rotation/facing. Forbidden: nine similar front-facing packshots, copying the reference "
    "photo pose, or only tiny 5–15° rotations between frames. Match SKU identity but rotate orientation per frame mandate."
)


def _merge_spec(base: dict[str, str], override: dict[str, str]) -> dict[str, str]:
    out = dict(base)
    for k, v in override.items():
        if v:
            out[k] = v
    return out


def camera_spec_for_index(index: int, batch_index: int) -> dict[str, str] | None:
    base = CAMERA_SPEC_BY_INDEX.get(index)
    if not base:
        return None
    ring = CAMERA_RING_BY_INDEX.get(index) or []
    if not ring:
        return dict(base)
    pick = ring[batch_index % len(ring)]
    return _merge_spec(base, pick)


def _append_mandate(shot: dict, mandate: str) -> None:
    mandate = (mandate or "").strip()
    if not mandate:
        return
    existing = (shot.get("composition_mandate") or "").strip()
    if mandate in existing:
        return
    shot["composition_mandate"] = f"{existing} {mandate}".strip() if existing else mandate


def apply_camera_diversity(plan: dict, *, merge: bool = False) -> dict:
    """为每个 shot 写入互斥朝向，并按 visual_batch_index 轮换整组机位预设。"""
    shots = plan.get("shots") or []
    batch_index = int(plan.get("visual_batch_index") or 0)
    roster: dict[int, str] = {}

    plan["camera_batch_preset_id"] = f"ring_batch_{batch_index % 6}"

    for shot in shots:
        try:
            idx = int(shot.get("index"))
        except (TypeError, ValueError):
            continue
        spec = camera_spec_for_index(idx, batch_index)
        if not spec:
            continue

        creative_has_orient = idx in _CREATIVE_INDICES and (shot.get("orientation_lock") or "").strip()
        if merge:
            shot["orientation_lock"] = spec["orientation"]
            shot["camera_angle_code"] = spec["code"]
        elif not creative_has_orient:
            shot["orientation_lock"] = spec["orientation"]
            shot["camera_angle_code"] = spec["code"]

        if merge:
            _append_mandate(shot, spec["mandate"])
        else:
            existing = (shot.get("composition_mandate") or "").strip()
            if not existing or existing == spec["mandate"]:
                shot["composition_mandate"] = spec["mandate"]
            else:
                _append_mandate(shot, spec["mandate"])

        extra = (shot.get("negative_extra") or "").strip()
        if ANGLE_NEGATIVE not in extra:
            shot["negative_extra"] = f"{extra}, {ANGLE_NEGATIVE}".strip(", ")

        roster[idx] = spec["short"]

    plan["camera_roster"] = roster
    plan["listing_angle_diversity_lock_en"] = (
        f"{LISTING_ANGLE_DIVERSITY_EN} This listing batch uses camera preset '{plan['camera_batch_preset_id']}' — "
        "each index has a distinct mandated facing; do not revert to reference-photo angle."
    )
    plan["shots"] = shots
    return plan
