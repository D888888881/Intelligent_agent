import logging

logger = logging.getLogger(__name__)


def normalize_shot_list(shots: list, expected_count: int, user_prompt: str) -> list:
    """保证 index 1..N 连续，避免少镜头、少打 API。"""
    by_index = {}
    for shot in shots:
        try:
            idx = int(shot.get("index"))
        except (TypeError, ValueError):
            continue
        if idx > 0:
            by_index[idx] = shot
    if not by_index and expected_count > 0:
        return shots
    target = max(expected_count, max(by_index.keys(), default=0))
    if target <= 0:
        return shots
    out = []
    for i in range(1, target + 1):
        if i in by_index:
            shot = dict(by_index[i])
            shot["index"] = i
            out.append(shot)
        else:
            logger.warning("plan missing shot index=%s, inserting fallback", i)
            out.append(
                {
                    "index": i,
                    "role": f"fill_{i}",
                    "reference_mode": "none",
                    "prompt_en": (
                        f"Unique e-commerce product photo variation {i}/{target}. "
                        f"{user_prompt[:400]}"
                    ),
                    "prompt_es": "",
                }
            )
    return out
