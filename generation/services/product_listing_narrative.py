"""套图叙事：过滤用户元指令，生成干净的产品摘要与西语卖点池。"""

from __future__ import annotations

import re

_META_PROMPT_MARKERS = re.compile(
    r"制作\s*\d+\s*张|商品主图|九图|详情图|TikTok\s*Shop|墨西哥|白底图|"
    r"多视角|不要拼图|帮我制作|包括\s*1\s*张|listing|套图",
    re.I,
)


def is_meta_listing_instruction(text: str) -> bool:
    t = (text or "").strip()
    if len(t) < 20:
        return False
    return bool(_META_PROMPT_MARKERS.search(t))


def product_summary_for_story(analysis: dict, user_prompt: str = "", strategy: dict | None = None) -> str:
    strategy = strategy or {}
    for candidate in (
        strategy.get("product_summary_zh"),
        analysis.get("product_summary_zh"),
        analysis.get("primary_function"),
        analysis.get("product_name_en"),
        f"{analysis.get('category') or ''} {analysis.get('product_name_en') or ''}".strip(),
    ):
        c = (candidate or "").strip()
        if not c or is_meta_listing_instruction(c):
            continue
        if len(c) > 180:
            c = c[:180]
        return c
    up = (user_prompt or "").strip()
    if up and not is_meta_listing_instruction(up):
        return up[:180]
    zone = (analysis.get("application_zone_en") or analysis.get("application_zone") or "").strip()
    name = (analysis.get("product_name_en") or "Hero SKU").strip()
    if zone:
        return f"{name} — {zone}"[:180]
    return name[:120] or "Hero SKU for Mexico e-commerce listing"


def default_spanish_usps_for_zone(zone: str) -> list[str]:
    pools = {
        "hair": [
            "Cabello suave",
            "Brillo sano",
            "Peinado fluido",
            "Sin frizz",
            "Hidratacion real",
            "Puntas cuidadas",
            "Menos quiebre",
            "Raiz liviana",
            "Control del frizz",
            "Sedosidad",
            "Definicion",
            "Nutricion capilar",
        ],
        "oral": [
            "Sonrisa blanca",
            "Aliento fresco",
            "Dientes brillantes",
            "Encias cuidadas",
            "Formula suave",
            "Limpieza profunda",
            "Sensacion fresca",
            "Placa reducida",
            "Boca limpia",
            "Proteccion diaria",
        ],
        "skin_face": [
            "Piel luminosa",
            "Hidratacion",
            "Textura pareja",
            "Glow natural",
            "Poros menos visibles",
            "Piel comoda",
            "Absorcion ligera",
            "Tono uniforme",
            "Sensacion fresca",
            "Barrera cuidada",
        ],
        "nail_fungus": [
            "Uña con mejor aspecto",
            "Menos aspecto amarillo",
            "Cuidado en la uña",
            "Uña de aspecto más limpio",
            "Para la uña manchada",
            "La uña se ve más clara",
            "Aspecto de uña cuidada",
            "Puedes mostrar la uña",
        ],
        "body_hand": [
            "Piel suave",
            "Hidratacion diaria",
            "Absorcion rapida",
            "Toque seco",
            "Manos cuidadas",
            "Elasticidad",
            "Piel nutrida",
            "Sin residuo graso",
        ],
        "body_bath": [
            "Espuma rica",
            "Piel suave",
            "Frescura diaria",
            "Aroma duradero",
            "Limpieza de la piel",
            "Sensacion ligera",
            "Piel comoda",
            "Bano fresco",
            "Aroma limpio",
            "Enjuague facil",
        ],
        "home_clean": [
            "Manchas fuera",
            "Brillo del piso",
            "Olor fresco",
            "Superficie lista",
            "Accion rapida",
            "Sin residuos",
            "Grasa fuera",
            "Vidrio claro",
            "Juntas limpias",
            "Espuma activa",
            "Un solo paso",
            "Aroma limpio",
        ],
    }
    return pools.get(
        zone,
        [
            "Formula estable",
            "Textura clara",
            "Envase firme",
            "Dosis justa",
            "Acabado uniforme",
            "Aplicacion limpia",
            "Efecto concreto",
            "Presentacion clara",
            "Toque ligero",
            "Aroma propio",
            "Listo al momento",
            "Detalle de cerca",
        ],
    )


def default_pain_phrases_en_for_zone(zone: str) -> list[str]:
    from generation.services.product_usage_semantics import ZONE_PROFILES

    profile = ZONE_PROFILES.get(zone, ZONE_PROFILES["generic"])
    before = profile.get("before") or "problem before use"
    after = profile.get("after") or "improved after use"
    return [before, f"need outcome: {after}"]