import requests
import logging
from typing import Optional
from config import ML_SITE, ML_API_BASE, ML_SEARCH_LIMIT, MIN_DISCOUNT_PERCENT, AFFILIATE_LINK

logger = logging.getLogger(__name__)

def build_affiliate_url(product_url: str) -> str:
    """
    Genera el link de afiliado para un producto.
    El link base de afiliado ya redirige al marketplace;
    para tracking por producto se añade el permalink como parámetro.
    """
    # El link corto del programa de afiliados de ML redirige a la home.
    # Para vincular un producto específico, incluimos el URL del producto
    # como referencia en el mensaje (el usuario llega al producto desde el link afiliado).
    # ML no expone la API de afiliados públicamente, así que usamos el link base
    # + el permalink directo como referencia informativa.
    return f"{AFFILIATE_LINK}"

def get_item_details(item_id: str) -> Optional[dict]:
    """Obtiene detalles completos de un producto por su ID."""
    try:
        url = f"{ML_API_BASE}/items/{item_id}"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning(f"Error obteniendo detalles de {item_id}: {e}")
        return None

def search_deals(query: str) -> list[dict]:
    """
    Busca productos con descuento en ML API pública.
    Filtra por descuento mínimo configurado.
    """
    deals = []
    url = f"{ML_API_BASE}/sites/{ML_SITE}/search"
    params = {
        "q": query,
        "limit": ML_SEARCH_LIMIT,
        "sort": "relevance",
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        logger.info(f"[{query}] → {len(results)} resultados obtenidos de ML")

        for item in results:
            original_price = item.get("original_price")
            current_price = item.get("price")

            # Filtrar: necesitamos ambos precios para calcular descuento
            if not original_price or not current_price:
                continue
            if original_price <= current_price:
                continue

            discount = round((1 - current_price / original_price) * 100, 1)
            if discount < MIN_DISCOUNT_PERCENT:
                continue

            # Imagen
            thumbnail = item.get("thumbnail", "")
            if thumbnail:
                # ML devuelve thumbnails pequeños; pedimos imagen mediana
                thumbnail = thumbnail.replace("-I.jpg", "-O.jpg")

            permalink = item.get("permalink", "")

            deals.append({
                "id": item.get("id"),
                "title": item.get("title", "Sin título"),
                "original_price": original_price,
                "current_price": current_price,
                "discount": discount,
                "thumbnail": thumbnail,
                "permalink": permalink,
                "affiliate_url": build_affiliate_url(permalink),
                "condition": item.get("condition", "new"),
                "sold_quantity": item.get("sold_quantity", 0),
            })

        logger.info(f"[{query}] → {len(deals)} ofertas con ≥{MIN_DISCOUNT_PERCENT}% descuento")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error de red buscando '{query}': {e}")
    except Exception as e:
        logger.error(f"Error inesperado buscando '{query}': {e}")

    return deals

def format_price(amount: float) -> str:
    """Formatea precio con separador de miles."""
    return f"${amount:,.0f}"

def format_message(deal: dict) -> str:
    """Construye el mensaje de Telegram para una oferta."""
    condition_map = {"new": "Nuevo", "used": "Usado", "refurbished": "Reacondicionado"}
    condition = condition_map.get(deal["condition"], deal["condition"])

    msg = (
        f"🔥 *{deal['title']}*\n\n"
        f"💸 ~~{format_price(deal['original_price'])}~~ → "
        f"*{format_price(deal['current_price'])}*\n"
        f"📉 Descuento: *{deal['discount']}%*\n"
        f"📦 Estado: {condition}\n"
    )

    if deal["sold_quantity"] > 0:
        msg += f"✅ Vendidos: {deal['sold_quantity']:,}\n"

    msg += (
        f"\n🛒 [Ver oferta en Mercado Libre]({deal['permalink']})\n"
        f"🤝 [Link de afiliado]({deal['affiliate_url']})"
    )

    return msg
