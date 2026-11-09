"""九张套图互斥机位 / 产品朝向，避免参考图或模型默认「同一角度复制」。"""

from __future__ import annotations

# index 1–9 与 TK_MX_NINE_FRAME_MATRIX 对齐
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
            "Camera 45° above product, viewing from front-left; product dominant left third; "
            "right third reserved for text; show top + front-left face."
        ),
        "mandate": (
            "CAMERA MANDATE — Elevated three-quarter from front-left; asymmetric layout; NOT profile, NOT top-down."
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
        "code": "macro_label_corner",
        "short": "macro label corner",
        "orientation": (
            "Macro close-up at 30° on front label corner; shallow depth of field; "
            "crop tight on texture/logo; product fills 75%+ frame; not full-pack silhouette."
        ),
        "mandate": (
            "CAMERA MANDATE — Macro detail on label/texture; tight crop; NOT full product, NOT wide shot."
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

ANGLE_NEGATIVE = (
    "copying reference photo camera angle, same product rotation as reference, "
    "duplicate facing direction as other listing frames, minor 5–15 degree tweak only, "
    "all nine images front-facing packshot"
)


def apply_camera_diversity(plan: dict) -> dict:
    """为每个 shot 写入互斥朝向，并生成全计划 roster 供 prompt 交叉约束。"""
    shots = plan.get("shots") or []
    roster: dict[int, str] = {}

    for shot in shots:
        try:
            idx = int(shot.get("index"))
        except (TypeError, ValueError):
            continue
        spec = CAMERA_SPEC_BY_INDEX.get(idx)
        if not spec:
            continue
        roster[idx] = spec["short"]
        shot["camera_angle_code"] = spec["code"]
        shot["orientation_lock"] = spec["orientation"]
        shot["composition_mandate"] = spec["mandate"]
        extra = (shot.get("negative_extra") or "").strip()
        shot["negative_extra"] = f"{extra}, {ANGLE_NEGATIVE}".strip(", ")

    plan["camera_roster"] = roster
    plan["shots"] = shots
    return plan
