"""策划预览：本套创意 + 8 维（中文精简，与 concepts 同源）。"""

from __future__ import annotations

from generation.services.creative_engine.concepts import DIMENSION_KEYS

# 与 DIMENSION_KEYS 一一对应，单一维护点（改 concepts 维名时同步此处）
DIMENSION_LABELS_ZH: dict[str, str] = {
    "visual_style": "视觉风格",
    "scene_environment": "环境场景",
    "color_palette": "主色调",
    "lighting": "光线",
    "camera_language": "镜头语言",
    "composition": "构图",
    "human_presence": "人物",
    "info_layout": "图上信息",
}

# 预览只展示 4 个核心维，减轻信息过载
PREVIEW_DIMENSION_KEYS = (
    "visual_style",
    "scene_environment",
    "lighting",
    "composition",
)


def format_creative_preview_markdown(plan: dict) -> str:
    cid = (plan.get("creative_concept_id") or "").strip()
    if not cid:
        return ""

    label = (plan.get("creative_concept_label_zh") or plan.get("creative_concept_id") or "").strip()
    dims = plan.get("creative_dimension_matrix") or {}
    lines = [
        "## 本套创意方向（确认生图前请先扫一眼）",
        f"- **概念**：{label}（`{cid}`）",
        f"- **站点**：{(plan.get('marketplace_label_zh') or plan.get('marketplace_id') or '—')}",
    ]

    pack = (plan.get("visual_batch_pack_name") or "").strip()
    if pack:
        lines.append(f"- **动作包**：{pack}")

    history = plan.get("creative_history") or []
    if history:
        avoid_lines = []
        for h in history[:5]:
            typ = h.get("record_type") or "success"
            tag = "已成功" if typ == "success" else "曾尝试"
            name = h.get("concept_label_zh") or h.get("concept_id") or "?"
            avoid_lines.append(f"  - #{h.get('job_id')} {tag}：{name}")
        lines.append("- **已避让近期方向**（本批会换一套）：")
        lines.extend(avoid_lines)

    lines.append("")
    lines.append("| 维度 | 本批方向 |")
    lines.append("| --- | --- |")
    for key in PREVIEW_DIMENSION_KEYS:
        zh = DIMENSION_LABELS_ZH.get(key, key)
        val = dims.get(key) or "—"
        lines.append(f"| {zh} | {val} |")

    extra = []
    for key in DIMENSION_KEYS:
        if key in PREVIEW_DIMENSION_KEYS:
            continue
        val = dims.get(key)
        if val:
            extra.append(f"{DIMENSION_LABELS_ZH.get(key, key)}：{val}")
    if extra:
        lines.append("")
        lines.append("其他：" + "；".join(extra))

    color_lock = (plan.get("creative_color_system_lock_en") or "").strip()
    scene_lock = (plan.get("creative_scene_family_lock_en") or "").strip()
    camera_lock = (plan.get("creative_camera_innovation_lock_en") or "").strip()
    if color_lock or scene_lock or camera_lock:
        lines.append("")
        lines.append("### 套内一致性（本批生图会写入提示词）")
        lines.append(
            "- **色彩**：同一套内主色/辅色协调，跨度不宜过大；白底帧阴影色调也与本套一致。"
        )
        lines.append(
            "- **背景**：类型可多样（纯色、棚拍、实景室内外、虚构场景等），但气质须在同一「视觉世界」内。"
        )
        lines.append(
            "- **机位与摆放**：分镜可大胆变化，须贴合本品材质、结构与使用场景。"
        )

    lines.append("")
    lines.append(
        "> 说明：上表为**策划约定的视觉方向**，生图模型可能仍有偏差；"
        "确认即表示认可职能分工 + 本套创意，而非保证每张成片 100% 一致。"
    )
    return "\n".join(lines)
