"""策划预览：每镜动作母版（中文）。"""

from __future__ import annotations


def format_action_preview_markdown(plan: dict) -> str:
    ap = plan.get("action_planning") or {}
    if (ap.get("scope") or plan.get("action_planning_scope")) == "skip":
        return ""
    roster = ap.get("roster") or []
    if not roster and not any((s.get("primary_action_id") for s in plan.get("shots") or [])):
        return ""

    plugin = ap.get("plugin") or "generic"
    plugin_zh = (
        "美妆/个护（通用8+增量）"
        if plugin == "beauty_skincare" or ap.get("beauty_increment")
        else "通用 8 动作"
    )
    lines = [
        "## 本套产品动作（L3.5）",
        f"- **动作库**：{plugin_zh}（`{ap.get('version') or '1.0'}`）",
        "- **规则**：职能/role 不变；每镜一个主动作，套内尽量不重复。",
        "",
        "| 镜 | 职能 | 动作母版 |",
        "| --- | --- | --- |",
    ]
    shots = sorted(plan.get("shots") or [], key=lambda s: int(s.get("index") or 0))
    if shots:
        for shot in shots:
            idx = shot.get("index") or "—"
            role = shot.get("role") or "—"
            label = shot.get("action_master_zh") or shot.get("primary_action_id") or "—"
            lines.append(f"| {idx} | {role} | {label} |")
    else:
        for r in roster:
            lines.append(
                f"| {r.get('index')} | {r.get('role') or '—'} | {r.get('label_zh') or r.get('action_id')} |"
            )
    lines.append("")
    lines.append(
        "> 动作母版约束产品怎么摆、怎么被看见；色彩与场景气质仍由套图创意层负责。"
    )
    return "\n".join(lines)
