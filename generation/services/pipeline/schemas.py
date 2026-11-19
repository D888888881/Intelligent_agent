"""五层 Agent 流水线契约版本与快照结构。"""

from __future__ import annotations

PIPELINE_SCHEMA_VERSION = "1.1"


def empty_layer_meta() -> dict:
    return {"schema_version": PIPELINE_SCHEMA_VERSION, "status": "pending"}


def layer_snapshot(layer: str, *, status: str = "ok", summary: dict | None = None) -> dict:
    snap = {
        "layer": layer,
        "schema_version": PIPELINE_SCHEMA_VERSION,
        "status": status,
    }
    if summary:
        snap["summary"] = summary
    return snap
