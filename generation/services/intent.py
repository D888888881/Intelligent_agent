import re

from django.conf import settings

_ANALYZE_ONLY = re.compile(
    r"不要生成|不用生成|无需生成|仅分析|只分析|不要出图|不用出图|仅文字|不要图|"
    r"只要分析|文字建议|不用修|不要修",
    re.I,
)

_GEN_HINT = re.compile(
    r"生成|制作|做.{0,8}图|出.{0,4}图|主图|套图|详情图|商品图|宣传图|电商图|"
    r"白底图|listing|banner|render",
    re.I,
)

_REFINE_HINT = re.compile(
    r"优化(一下)?(这张|这个|这幅|该)?(图|图片|照片|素材)|"
    r"帮(我)?(优化|修|重塑|重制|重做)(一下)?(这张|这个|这幅|该)?(图|图片|照片)?|"
    r"(图|图片|照片).{0,16}(优化|修图|改好|重塑|重制|重做)|"
    r"重塑(一下)?(这张|这个|这幅|该)?(图|图片|照片)?|"
    r"重制(一下)?(这张|这个|这幅|该)?(图|图片|照片)?|"
    r"ai感|AI感|去ai|去 AI|不像真人|更真实|真实感|自然一点|减少.{0,6}塑料|"
    r"修图|重绘|重画|改图|真人化|去动漫|动漫感|二次元|"
    r"人物.{0,10}(太假|很假|假|不真实)|太假了?|"
    r"重新生成(这张|这个|这幅|该)?(图|图片|照片)?|"
    r"make.{0,20}(realistic|natural)|fix.{0,12}(image|photo)|"
    r"reduce.{0,12}ai|less.{0,8}uncanny|remake.{0,12}(photo|image)",
    re.I,
)

_REFINE_TEXT_ONLY = re.compile(
    r"优化.{0,8}(文案|标题|描述|prompt|提示词)|只改文字",
    re.I,
)

_INTENT_CUT = re.compile(
    r"\n\s*(\*\*)?(Subject|Style|Shot|Setting|Scene lighting)\b|"
    r"\n\s*---\s*\n|"
    r"\n\s*(\*\*)?回答(\*\*)?\s*\n|"
    r"图片优化建议",
    re.I | re.M,
)

_COUNT_MAKE = re.compile(r"制作\s*(\d{1,2})\s*[张幅个]", re.I)
_COUNT_ZH = re.compile(r"(\d{1,2})\s*[张幅个]", re.I)
_COUNT_EN = re.compile(r"(\d{1,2})\s*(?:images?|pics?)", re.I)

_TK_MX = re.compile(
    r"tiktok|tk\b|墨西哥|mexico|mexican|español|spanish|西语|西班牙语",
    re.I,
)

_ECOM_NINE = re.compile(
    r"主图|白底|详情|9\s*张|九张|1\s*\+?\s*1\s*\+?\s*7|1\+1\+7",
    re.I,
)


def user_intent_snippet(prompt: str, max_len: int = 600) -> str:
    text = (prompt or "").strip()
    if not text:
        return ""
    m = _INTENT_CUT.search(text)
    if m and m.start() > 0:
        text = text[: m.start()].strip()
    return text[:max_len]


def wants_ecommerce_bundle(prompt: str) -> bool:
    """多套电商主图（含 9 图 TK 等），不应走单张 photo_refine。"""
    text = user_intent_snippet(prompt) or (prompt or "")
    count = parse_image_count_from_prompt(prompt)
    if count is not None and count >= 2 and _GEN_HINT.search(text):
        return True
    if count == 9:
        return True
    if _ECOM_NINE.search(text) and (_GEN_HINT.search(text) or _TK_MX.search(text)):
        return True
    if re.search(r"主图.*白底|白底.*详情", text, re.I):
        return True
    return False


def wants_image_refine(prompt: str) -> bool:
    if wants_ecommerce_bundle(prompt):
        return False
    text = user_intent_snippet(prompt)
    if not text:
        return False
    if _ANALYZE_ONLY.search(text):
        return False
    if _REFINE_TEXT_ONLY.search(text):
        return False
    return bool(_REFINE_HINT.search(text))


def wants_image_generation(prompt: str) -> bool:
    text = user_intent_snippet(prompt)
    if not text:
        return False
    if _ANALYZE_ONLY.search(text):
        return False
    if wants_image_refine(prompt):
        return True
    if wants_ecommerce_bundle(prompt):
        return True
    if _GEN_HINT.search(text):
        return True
    if _COUNT_ZH.search(text) and "图" in text:
        return True
    return False


def parse_image_count_from_prompt(prompt: str, default: int | None = None) -> int | None:
    text = user_intent_snippet(prompt) or (prompt or "")

    m = _COUNT_MAKE.search(text)
    if m:
        n = int(m.group(1))
        return max(1, min(n, settings.GEN_MAX_IMAGE_COUNT))

    nums = []
    for pat in (_COUNT_ZH, _COUNT_EN):
        nums.extend(int(x) for x in pat.findall(text))
    if nums:
        n = max(nums)
        return max(1, min(n, settings.GEN_MAX_IMAGE_COUNT))
    return default


def resolve_generation_params(
    prompt: str,
    *,
    image_count: int,
    plan_template: str,
) -> tuple[int, str]:
    tpl = (plan_template or "auto").strip()
    count = max(1, min(int(image_count), settings.GEN_MAX_IMAGE_COUNT))

    parsed = parse_image_count_from_prompt(prompt, None)
    if parsed is not None:
        count = parsed

    text = user_intent_snippet(prompt) or (prompt or "")

    if wants_ecommerce_bundle(prompt):
        if parsed is not None and parsed >= 2:
            count = parsed
        elif count < 2 and _ECOM_NINE.search(text):
            count = 9
        if tpl in ("auto", "photo_refine", "generic"):
            if count == 9 and (
                _TK_MX.search(text)
                or _ECOM_NINE.search(text)
                or re.search(r"主图.*白底|白底.*详情", text, re.I)
            ):
                tpl = "tk_mx_ecommerce_9"
            elif tpl == "photo_refine":
                tpl = "auto"
    elif wants_image_refine(prompt):
        if tpl == "auto":
            tpl = "photo_refine"
        if parsed is None:
            count = 1
    elif tpl == "auto":
        detected = detect_plan_template(prompt, count)
        if detected:
            tpl = detected

    if tpl == "auto" and count == 9:
        detected = detect_plan_template(prompt, count)
        if detected:
            tpl = detected

    return count, tpl


def detect_plan_template(prompt: str, image_count: int) -> str | None:
    text = user_intent_snippet(prompt) or (prompt or "")
    if wants_image_refine(prompt) and image_count == 1 and not wants_ecommerce_bundle(prompt):
        return "photo_refine"
    if image_count != 9:
        return None
    if _TK_MX.search(text) or _ECOM_NINE.search(text):
        return "tk_mx_ecommerce_9"
    if re.search(r"主图.*白底|白底.*详情", text, re.I):
        return "tk_mx_ecommerce_9"
    return None
