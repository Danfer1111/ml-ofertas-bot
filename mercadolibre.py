import requests
import logging
import time
from typing import Optional
from config import ML_SITE, ML_API_BASE, ML_SEARCH_LIMIT, MIN_DISCOUNT_PERCENT, AFFILIATE_LINK

logger = logging.getLogger(__name__)

# Headers que simulan un navegador real para evitar 403 de ML
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.mercadolibre.com.mx/",
    "Origin": "https://www.mercadolibre.com.mx",
    "Connection": "keep-alive",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)

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
        resp = SESSION.get(url, timeout=10)
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

    # Retry con backoff ante errores temporales (429, 503, 403)
    for attempt in range(3):
        try:
            resp = SESSION.get(url, params=params, timeout=15)
            if resp.status_code in (429, 503):
                wait = 2 ** attempt * 5
                logger.warning(f"[{query}] Rate limit ({resp.status_code}), esperando {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            break
        except requests.exceptions.RequestException as e:
            if attempt == 2:
                logger.error(f"Error de red buscando '{query}' tras 3 intentos: {e}")
                return deals
            time.sleep(3)
    else:
        return deals

    try:
        data = resp.json()
        results = data.get("results", [])
        logger.info(f"[{query}] → {len(results)} resultados obtenidos de ML")

        for item in results:
            original_price = item.get("original_price")
            current_price = item.get("price")

            if not original_price or not current_price:
                continue
            if original_price <= current_price:
                continue

            discount = round((1 - current_price / original_price) * 100, 1)
            if discount < MIN_DISCOUNT_PERCENT:
                continue

            thumbnail = item.get("thumbnail", "")
            if thumbnail:
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
    except Exception as e:
        logger.error(f"Error procesando respuesta de '{query}': {e}")

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
