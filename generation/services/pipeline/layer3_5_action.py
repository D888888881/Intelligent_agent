"""L3.5：产品动作规划（通用 8 + 美妆增量）。不改 L3 role。"""

from __future__ import annotations

from generation.services.action_planning import apply_action_planning
from generation.services.pipeline.schemas import layer_snapshot


def run_layer3_5_action_planning(plan: dict, *, job=None) -> tuple[dict, dict]:
    roles_before = {
        int(s.get("index") or 0): (s.get("role") or "")
        for s in plan.get("shots") or []
    }
    plan = apply_action_planning(plan, job=job)
    roles_after = {
        int(s.get("index") or 0): (s.get("role") or "")
        for s in plan.get("shots") or []
    }
    ap = plan.get("action_planning") or {}
    identity_preserved = roles_before == roles_after
    status = "ok"
    if ap.get("scope") == "skip":
        status = "skip"
    elif not identity_preserved:
        status = "warn"
    summary = {
        "scope": ap.get("scope"),
        "plugin": ap.get("plugin"),
        "beauty_increment": bool(ap.get("beauty_increment")),
        "action_count": len(ap.get("roster") or []),
        "identity_roles_preserved": identity_preserved,
        "roster": (ap.get("roster") or [])[:12],
    }
    return plan, layer_snapshot("L3_5_action_planning", status=status, summary=summary)
