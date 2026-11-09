import base64

from django.conf import settings

from Intelligent_agent.model_catalog import resolve_vision_model
from chat.services.openai_client import get_openai_client, is_chat_configured

# 5S 提示法：Subject / Style / Shot / Setting / Scene lighting
FIVE_S_SECTIONS = (
    ("Subject", "主体/核心视觉元素"),
    ("Style", "风格"),
    ("Shot", "镜头与构图"),
    ("Setting", "场景元素与环境"),
    ("Scene lighting", "场景光照与影调"),
)

FIVE_S_CHAT_SYSTEM = """
当用户消息中包含图片时，你必须按「5S提示法」分析并组织回答，依次包含以下五部分（保留英文标题，后跟中文内容）：

**Subject 主体/核心视觉元素**：画面核心对象、数量、状态、关键细节。
**Style 风格**：整体美学、色彩、材质、时代或流派、后期倾向。
**Shot 镜头与构图**：景别（特写/中景/全景等）、机位角度、构图法则、留白。
**Setting 场景元素与环境**：地点类型、背景、道具、环境信息。
**Scene lighting 场景光照与影调**：主光源、光质、明暗对比、色温、氛围。

要求：用中文，具体可执行，适合作为后续 AI 生图 prompt；若用户另有提问，在 5S 分析后单独用「回答」小节回应。
""".strip()

FIVE_S_REFERENCE_PROMPT = """
请严格按 5S 提示法分析这张参考图，用中文，每节单独一段，格式如下（标题必须保留）：

Subject（主体/核心视觉元素）：
Style（风格）：
Shot（镜头与构图）：
Setting（场景元素与环境）：
Scene lighting（场景光照与影调）：

要求：客观、具体、可复现，便于作为套图生成的统一视觉基准；不要输出 markdown 代码块。
""".strip()


def five_s_user_prompt(user_question: str = "") -> str:
    q = (user_question or "").strip()
    base = """
请按 5S 提示法分析这张图片，用中文输出五部分：Subject、Style、Shot、Setting、Scene lighting（每部分写明中文含义）。
""".strip()
    if q:
        return f"{base}\n\n用户问题：{q}\n请先完成 5S 分析，再简要回答用户问题。"
    return base


def attachment_to_data_url(attachment) -> str:
    mime = attachment.mime_type or "image/png"
    with attachment.file.open("rb") as f:
        raw = f.read()
    b64 = base64.standard_b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{b64}"


def analyze_image(attachment, prompt: str, vision_model: str | None = None) -> str:
    if not attachment:
        return ""
    if not is_chat_configured():
        return f"参考图 {attachment.original_name or attachment.id}（未配置对话 API）"

    model = resolve_vision_model(vision_model)
    client = get_openai_client()
    data_url = attachment_to_data_url(attachment)

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        max_tokens=2048,
    )
    choices = getattr(resp, "choices", None) or []
    if not choices:
        raise RuntimeError("识图模型未返回内容")
    return (choices[0].message.content or "").strip()


def analyze_image_five_s(
    attachment,
    user_question: str = "",
    vision_model: str | None = None,
) -> str:
    prompt = FIVE_S_REFERENCE_PROMPT if not user_question else five_s_user_prompt(user_question)
    return analyze_image(attachment, prompt, vision_model=vision_model)


ECOMMERCE_PRODUCT_ANALYSIS_PROMPT = """
你是一名跨境电商商品分析师。请分析这张商品参考图，输出单个 JSON 对象（不要 markdown，不要代码块）。

字段说明：
- product_name_en: 商品英文名
- product_name_es: 商品西班牙语名（墨西哥常用表述）
- category: 品类
- primary_function: 商品作用/核心功能（中文一句 + 英文一句，用 " | " 连接）
- key_selling_points: 字符串数组，3-6 条卖点（中英均可）
- pain_points: 字符串数组，2-5 条目标用户痛点（中英均可）
- purchase_motivations: 字符串数组，2-4 条购买动机（为什么现在买）
- visual_identity: 只描述「商品本身」的外观（形状、尺寸感、主色、辅色、包装材质、logo/文字位置、配件），禁止描述当前照片的背景墙、桌面、构图、机位、景深、打光方式
- identity_lock_en: 英文 120-220 词，像电商 SKU 规范：精确包装形状、主色/辅色 hex 或名称、材质、logo 位置、标签上可读文字（原文抄写）、容量/尺寸感、配件清单；供 AI 必须画「同一商品」
- label_text_exact: 包装/瓶身/盒子上可见文字，逐字抄写（多种语言都保留）
- primary_colors: 字符串数组，主色名 + 大致 hex
- package_includes: 包装内含物数组（若看不出可空数组）
- target_audience: 目标人群
- model_cast_gender: 生图人物性别约束，三选一字符串 — female（女性模特/手部，如口红、女装、女性内衣、女鞋）、male（男性，如男士护肤、剃须、男款服饰鞋）、any（中性/男女均可，如部分家居、3C、明显 unisex 运动装备）。口红/唇釉/唇彩/眼影/粉底/睫毛膏/女性美妆必须为 female；不要对女性美妆输出 male。
- spanish_headlines: 5-8 条西班牙语短标题（每条 3-6 词，适合主图/详情图字卡）
- usage_scenarios: 2-4 个使用场景短语（西班牙语）
- before_use_state: 使用「本品前」用户/目标对象的典型问题状态（中文 1-2 句，可被画成单张照片，如毛躁发、暗沉肤、杂乱厨房）
- after_use_state: 使用「本品后」的理想改善结果（中文 1-2 句，可被画成单张照片，与 before 成对）
- before_after_visual_en: 英文 40-80 词，描述一张电商图里如何表达「前后对比」（同一画面内的左右/前后/因果隐喻；禁止拼贴多宫格，仍须 single photograph）
- same_category_comparison: 对象，含：
  - generic_alternative_en: 同品类「普通/廉价/常规」替代品的通用外观描述（无真实竞品品牌名、无他人商标）
  - our_advantages_en: 字符串数组 3-5 条，本品相对该普通替代品的可视化优势（容量、成分、包装、效果、认证等）
  - comparison_shot_en: 英文 40-80 词，单张棚拍中「本品 vs 通用替代品」并排对比的构图建议（两物体同场景，非 collage grid）
- product_variants: 数组。若一张图内有多件商品/多个色号/多个款式，或用户上传了多张不同 SKU 图，则必须列出每个可售变体（美妆、内衣、鞋靴、吊带/背心、服饰均适用）。每项字段：
  - variant_label: 简短名称（如「#12 正红」「Nude Beige / M」「White Air Sneaker / 42」）
  - colorway_en: 英文颜色描述（主色+辅色）
  - style_en: 英文款式描述（如 balconette bra, strappy camisole, high-top sneaker, slide sandal, seamless underwear）
  - size_or_fit_en: 可见尺码或规格（S/M/L, 32A, EU42, US9, one-size 等；看不出可空字符串）
  - material_en: 主要材质/面料（lace, cotton, mesh, leather, knit, satin 等）
  - identity_lock_en: 该变体 80-180 词 SKU 外观锁定（轮廓、肩带/鞋带、logo、印花、五金、跟高/鞋型）
  - label_text_exact: 该变体可见标签/鞋舌/吊牌文字（若有）
  - source_image_index: 0 起，对应用户上传的第几张图（单图多 SKU 时均为 0）
  - in_frame_position: 可选，单图多品时在画面中的位置（如 front left shoe, top row nude bra）

服饰/鞋类特别要求：
- 内衣/吊带：区分款式（无钢圈、三角、法式、美背等）与颜色，不要合并成「一件内衣」。
- 鞋子：区分鞋型（跑鞋/板鞋/凉鞋）、配色、高帮/低帮；多双同框时每个 colorway 一条 variant。
- 若仅有颜色不同但款式相同，仍按颜色拆 variant；若款式+颜色都不同，variant_label 里同时体现。

额外要求：visual_identity 必须足够让画师在「全新棚拍/场景」中画出同一 SKU，而不是复刻这张参考图。
before/after 与 category comparison 必须基于该商品真实品类与功能推断，不可编造医疗承诺。
若存在 product_variants，顶层 identity_lock_en 仍写「主 SKU/系列共性」；各变体细节放在 product_variants 内。
""".strip()


MULTI_IMAGE_ECOMMERCE_EXTRA = """
用户上传了多张参考图。请综合所有图片：
1) 若每张图是不同色号/SKU/款式（如不同色口红、不同配色鞋、不同色内衣/吊带），在 product_variants 中为每张图至少列 1 个变体，source_image_index 对应图片顺序（第一张为 0）。
2) 若某张图内同时出现多个色号/多款并列（如一排鞋、多色内衣平铺），每个可售款一条 variant，并用 in_frame_position 区分。
3) product_name_en / category 等顶层字段描述整个 listing 系列（如 "Women's seamless bra line" / "Unisex casual sneakers"）；不要只描述第一张图而忽略其余图。
4) 内衣、鞋、吊带等 APPAREL/FOOTWEAR 必须写清 style_en 与 colorway_en，避免只写 "underwear" 或 "shoes" 这种笼统词。
""".strip()


def _normalize_model_cast_gender(data: dict) -> None:
    raw = (data.get("model_cast_gender") or data.get("target_model_gender") or "").strip().lower()
    alias = {
        "woman": "female",
        "women": "female",
        "female": "female",
        "f": "female",
        "girl": "female",
        "man": "male",
        "men": "male",
        "male": "male",
        "m": "male",
        "unisex": "any",
        "neutral": "any",
        "any": "any",
        "both": "any",
    }
    if raw in alias:
        data["model_cast_gender"] = alias[raw]


def _parse_product_analysis_json(raw: str, fallback_attachment=None) -> dict:
    import json

    try:
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            data = json.loads(raw[start : end + 1])
            if isinstance(data, dict):
                _normalize_model_cast_gender(data)
            return data
    except json.JSONDecodeError:
        pass
    name = getattr(fallback_attachment, "original_name", None) or "product"
    return {
        "visual_identity": raw[:1500],
        "raw_analysis": raw,
        "product_name_en": name,
    }


def analyze_products_for_ecommerce(
    attachments,
    user_prompt: str = "",
    vision_model: str | None = None,
) -> dict:
    """支持多图：多色号分包、或单图多 SKU。"""
    att_list = [a for a in (attachments or []) if a]
    if not att_list:
        return {}
    if len(att_list) == 1:
        return analyze_product_for_ecommerce(att_list[0], user_prompt, vision_model=vision_model)

    if not is_chat_configured():
        return {
            "visual_identity": ", ".join(
                a.original_name or f"image-{i}" for i, a in enumerate(att_list)
            ),
            "raw_fallback": True,
            "product_variants": [
                {
                    "variant_label": a.original_name or f"Variant {i + 1}",
                    "source_image_index": i,
                }
                for i, a in enumerate(att_list)
            ],
        }

    model = resolve_vision_model(vision_model)
    client = get_openai_client()
    text = ECOMMERCE_PRODUCT_ANALYSIS_PROMPT + "\n\n" + MULTI_IMAGE_ECOMMERCE_EXTRA
    if user_prompt:
        text += f"\n\n用户补充需求：{user_prompt[:2000]}"
    parts: list = [{"type": "text", "text": text}]
    for att in att_list:
        parts.append(
            {
                "type": "image_url",
                "image_url": {"url": attachment_to_data_url(att)},
            }
        )
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": parts}],
        max_tokens=4096,
    )
    choices = getattr(resp, "choices", None) or []
    if not choices:
        raise RuntimeError("识图模型未返回内容")
    raw = (choices[0].message.content or "").strip()
    data = _parse_product_analysis_json(raw, att_list[0])
    data.setdefault(
        "product_variants",
        [
            {
                "variant_label": a.original_name or f"Variant {i + 1}",
                "source_image_index": i,
            }
            for i, a in enumerate(att_list)
        ],
    )
    data["reference_image_count"] = len(att_list)
    return data


def analyze_product_for_ecommerce(
    attachment,
    user_prompt: str = "",
    vision_model: str | None = None,
) -> dict:
    """结构化商品分析，供套图策划使用。"""

    if not attachment:
        return {}
    if not is_chat_configured():
        return {"visual_identity": attachment.original_name or "product", "raw_fallback": True}

    text = ECOMMERCE_PRODUCT_ANALYSIS_PROMPT
    if user_prompt:
        text += f"\n\n用户补充需求：{user_prompt[:2000]}"

    raw = analyze_image(attachment, text, vision_model=vision_model)
    data = _parse_product_analysis_json(raw, attachment)
    if "primary_function" not in data and user_prompt:
        data["primary_function"] = user_prompt[:500]
    data.setdefault("reference_image_count", 1)
    return data


def build_user_content(text: str, attachments) -> str | list:
    """OpenAI 多模态 user content；无图时返回纯文本。"""
    if not attachments:
        return text
    parts: list = []
    instruction = five_s_user_prompt(text) if text else FIVE_S_REFERENCE_PROMPT
    parts.append({"type": "text", "text": instruction})
    for att in attachments:
        parts.append(
            {
                "type": "image_url",
                "image_url": {"url": attachment_to_data_url(att)},
            }
        )
    return parts
