#!/usr/bin/env python
"""导出 Grsai 生图提示词汇编 Markdown（从 generation/services 常量与模块读取）。"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Intelligent_agent.settings")

import django

django.setup()


def _sec(title: str, body: str, lines: list[str]) -> None:
    lines.append(f"\n## {title}\n")
    lines.append(body.strip() + "\n")


def _sub(title: str, text: str, lines: list[str]) -> None:
    lines.append(f"\n### {title}\n")
    lines.append(f"```text\n{text.strip()}\n```\n")


def _variants_table(name: str, variants: list[dict], lines: list[str]) -> None:
    lines.append(f"\n### {name}\n\n")
    lines.append("| ID | 中文 | mandate_en（节选） |\n")
    lines.append("|:---|:---|:---|\n")
    for v in variants:
        mid = (v.get("mandate_en") or "").replace("\n", " ").strip()
        if len(mid) > 220:
            mid = mid[:217] + "..."
        lines.append(f"| `{v.get('id', '')}` | {v.get('label_zh', '')} | {mid} |\n")


def main() -> None:
    out = ROOT / "docs" / "生图提示词汇编.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = [
        "# 生图提示词汇编\n",
        f"\n> 自动生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n",
        "> 来源：`generation/services/*`；实际成图 prompt = `build_shot_generation_prompt` + 模型参考图前缀 + `shot.prompt_en`。\n",
        "\n---\n",
    ]

    _sec(
        "1. 单张成图 Prompt 拼装顺序",
        """
`generation/services/prompt_builder.py` → `build_shot_generation_prompt(shot, plan)` 按序拼接（空格连接）：

1. GPT 参考图说明（若适用）
2. `SKU_ONLY_REFERENCE_GUARD`（模特镜时）
3. `quality_prefix`
4. 图上文字策略 `on_image_text_mandate_for_plan`
5. `on_image_text_density_mandate_en`、`listing_usp_diversity_lock_en`
6. 参考图导演块（`reference_guided`）
7. 多色 SKU 展示 / variant 说明
8. `MANDATORY PRODUCT ORIENTATION`、`camera_roster` 互斥
9. SKU identity / Banana 锁
10. `composition_mandate`、各 `role` 的 Frame type 提示
11. 电商故事 beat、`diversity_lock`、`action_lock`、密度锁
12. 人物 Cast、`listing_story_theme_en`、`previous_batch_avoidance_en` 等
13. `usp_message_lock`、`frame*_content_lock`、各类 story lock
14. `SCENE DIRECTION:` + `shot.prompt_en`
15. 西语标题 / icon / `prompt_es`（图 2 白底跳过营销字）
16. `Avoid:` negative
        """,
        lines,
    )

    from generation.services.prompt_builder import SKU_ONLY_REFERENCE_GUARD
    from generation.services.image_text_policy import (
        DEFAULT_NO_CHINESE_NEGATIVE,
        ON_IMAGE_TEXT_MANDATE_DEFAULT,
        ON_IMAGE_TEXT_MANDATE_ES_MX,
    )
    from generation.services.listing_usp_distribution import (
        TYPOGRAPHY_MANDATE_EN,
        USP_DIVERSITY_LOCK_EN,
    )
    from generation.services.camera_diversity import (
        LISTING_ANGLE_DIVERSITY_EN,
        ANGLE_NEGATIVE,
        CAMERA_SPEC_BY_INDEX,
    )
    from generation.services.tk_mx_listing import (
        HERO_VISUAL_IMPACT_EN,
        HERO_LAYERED_MX_COMPOSITION,
        WHITE_BG_NO_TEXT_EN,
        USP_PRIMARY_PAIN_VISUAL,
        LISTING_IMAGE_DOCTRINE_ZH,
        ARTICLE_MATRIX_HINT_ZH,
        TRUST_QUALITY_REAL_LIFE_MX,
        EASE_OBJECTION_TIKTOK_SOCIAL_PROOF,
        LAYOUT_MANDATES,
    )
    from generation.services.frame3_flex import FRAME_3_VARIANTS
    from generation.services.frame4_flex import (
        FRAME_4_MANDATE_EN,
        FRAME_4_LABEL_ZH,
        FRAME_4_VARIANT_ID,
        FRAME_4_NO_COMPARE_TEXT,
    )
    from generation.services.frame5_flex import FRAME_5_VARIANTS
    from generation.services.frame9_conversion import FRAME_9_VARIANTS
    from generation.services.shot_diversity_constants import DETAIL_SHOT_NEGATIVE
    from generation.services.model_strategy import (
        BANANA_STRICT_NEGATIVE,
        GPT_IMAGE_NEGATIVE_EXTRA,
        reference_prefix_for_model,
    )

    _sub("SKU_ONLY_REFERENCE_GUARD", SKU_ONLY_REFERENCE_GUARD, lines)
    _sub("ON_IMAGE_TEXT_MANDATE_ES_MX", ON_IMAGE_TEXT_MANDATE_ES_MX, lines)
    _sub("ON_IMAGE_TEXT_MANDATE_DEFAULT", ON_IMAGE_TEXT_MANDATE_DEFAULT, lines)
    _sub("DEFAULT_NO_CHINESE_NEGATIVE", DEFAULT_NO_CHINESE_NEGATIVE, lines)
    _sub("TYPOGRAPHY_MANDATE_EN", TYPOGRAPHY_MANDATE_EN, lines)
    _sub("USP_DIVERSITY_LOCK_EN", USP_DIVERSITY_LOCK_EN, lines)
    _sub("LISTING_ANGLE_DIVERSITY_EN", LISTING_ANGLE_DIVERSITY_EN, lines)
    _sub("ANGLE_NEGATIVE", ANGLE_NEGATIVE, lines)

    _sec("2. TK México 九图总则", LISTING_IMAGE_DOCTRINE_ZH + "\n\n" + ARTICLE_MATRIX_HINT_ZH, lines)
    for key, val in [
        ("HERO_VISUAL_IMPACT_EN", HERO_VISUAL_IMPACT_EN),
        ("HERO_LAYERED_MX_COMPOSITION", HERO_LAYERED_MX_COMPOSITION),
        ("WHITE_BG_NO_TEXT_EN", WHITE_BG_NO_TEXT_EN),
        ("USP_PRIMARY_PAIN_VISUAL", USP_PRIMARY_PAIN_VISUAL),
        ("TRUST_QUALITY_REAL_LIFE_MX", TRUST_QUALITY_REAL_LIFE_MX),
        ("EASE_OBJECTION_TIKTOK_SOCIAL_PROOF", EASE_OBJECTION_TIKTOK_SOCIAL_PROOF),
    ]:
        _sub(key, val, lines)
    lines.append("\n### LAYOUT_MANDATES\n\n")
    for k, v in LAYOUT_MANDATES.items():
        _sub(k, v, lines)

    _sec("3. 图 3 / 4 / 5 / 9 灵活职能", "", lines)
    _variants_table("图 3", FRAME_3_VARIANTS, lines)
    _sub(
        "图 4（固定）",
        f"id=`{FRAME_4_VARIANT_ID}` {FRAME_4_LABEL_ZH}\n\n{FRAME_4_MANDATE_EN}\n\n{FRAME_4_NO_COMPARE_TEXT}",
        lines,
    )
    _variants_table("图 5", FRAME_5_VARIANTS, lines)
    _variants_table("图 9 强转化收尾", FRAME_9_VARIANTS, lines)

    _sec("4. 九图默认机位（CAMERA_SPEC_BY_INDEX）", "", lines)
    lines.append("| Index | short | mandate |\n|:---|:---|:---|\n")
    for idx in sorted(CAMERA_SPEC_BY_INDEX):
        s = CAMERA_SPEC_BY_INDEX[idx]
        mand = (s.get("mandate") or "").replace("|", "/")
        lines.append(f"| {idx} | {s.get('short', '')} | {mand} |\n")

    _sub("DETAIL_SHOT_NEGATIVE（创意帧共用）", DETAIL_SHOT_NEGATIVE, lines)
    lines.append(
        "\n### layout_diversity_lock_en（product_story_locks 写入 plan）\n\n"
        "```text\n"
        "LAYOUT DIVERSITY — No more than TWO top-down flat-lays in the full 9-frame set; "
        "no more than ONE bathroom mirror composition; alternate studio / outdoor / macro / infographic; "
        "each frame distinct camera distance (macro vs wide vs table-level) and product rotation; "
        "never nine similar front-facing packshots.\n```\n"
    )

    _sec("5. 模型与参考图前缀", "", lines)
    _sub("BANANA_STRICT_NEGATIVE（并入 plan negative）", BANANA_STRICT_NEGATIVE, lines)
    _sub("GPT_IMAGE_NEGATIVE_EXTRA", GPT_IMAGE_NEGATIVE_EXTRA, lines)
    for label, fam in [("Banana 生图", "nano-banana"), ("GPT Image 生图", "gpt-image-1")]:
        _sub(
            f"reference_prefix_for_model — {label}",
            reference_prefix_for_model(fam, has_reference=True, purpose="generation"),
            lines,
        )

    from generation.services.visual_batch_variance import (
        _GENERIC_BATCH_PACKS,
        _BEAUTY_BATCH_PACKS,
    )

    _sec("6. 批次视觉主题包（story_theme_en + 图 3/6/7/8/9 action_en）", "", lines)
    for pack_list, title in [
        (_GENERIC_BATCH_PACKS, "通用 6 主题"),
        (_BEAUTY_BATCH_PACKS, "美妆护肤包"),
    ]:
        lines.append(f"\n### {title}\n\n")
        for pack in pack_list:
            lines.append(f"#### `{pack.get('name')}`\n\n")
            theme = (pack.get("story_theme_en") or "").strip()
            if theme:
                lines.append(f"- **story_theme_en**: {theme}\n")
            mood = (pack.get("color_mood_en") or "").strip()
            if mood:
                lines.append(f"- **color_mood_en**: {mood}\n")
            frames = pack.get("frames") or {}
            for fi in sorted(frames, key=int):
                fr = frames[fi]
                lines.append(
                    f"- **图 {fi}** `{fr.get('action_code', '')}`: "
                    f"{(fr.get('action_en') or '').replace(chr(10), ' ')}\n"
                )
                if fr.get("camera_short"):
                    lines.append(f"  - camera_short: `{fr['camera_short']}`\n")

    _sec(
        "7. 策划 LLM 与单镜 prompt_en",
        """
- **策划阶段**：`planner.py` / `build_plan` 为每镜生成 `prompt_en`、`prompt_es` 等（TK 九图有长系统说明，见仓库 `planner.py` 内 `tk_mx_ecommerce_9` extra）。
- **成图阶段**：以上字段作为 `SCENE DIRECTION` 主体，与本文档中的锁、mandate 合并后送入 Grsai。
- **查看某次任务真实 prompt**：后台 `GenerationJob` → `images[].prompt` 字段，或 API 任务详情里每张图的 `prompt`。
        """,
        lines,
    )

    _sec(
        "8. 重新生成本文档",
        f"\n```bash\ncd {ROOT}\npython scripts/export_generation_prompts_md.py\n```\n",
        lines,
    )

    out.write_text("".join(lines), encoding="utf-8")
    print(f"Wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
