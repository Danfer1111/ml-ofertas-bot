import requests
import logging
import time
from typing import Optional
from config import (
    ML_SITE, ML_API_BASE, ML_SEARCH_LIMIT,
    MIN_DISCOUNT_PERCENT, AFFILIATE_LINK,
    ML_CLIENT_ID, ML_CLIENT_SECRET, ML_ACCESS_TOKEN,
)

logger = logging.getLogger(__name__)

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "es-MX,es;q=0.9",
})

_token_cache: dict = {"token": None, "expires_at": 0}


def get_access_token() -> Optional[str]:
    if ML_ACCESS_TOKEN:
        return ML_ACCESS_TOKEN

    if not ML_CLIENT_ID or not ML_CLIENT_SECRET:
        logger.warning("Sin credenciales ML OAuth — las requests pueden fallar con 403.")
        return None

    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"]:
        return _token_cache["token"]

    try:
        resp = requests.post(
            "https://api.mercadolibre.com/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": ML_CLIENT_ID,
                "client_secret": ML_CLIENT_SECRET,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        token = data["access_token"]
        expires_in = data.get("expires_in", 21600)
        _token_cache["token"] = token
        _token_cache["expires_at"] = now + expires_in - 300
        logger.info("Token OAuth obtenido correctamente.")
        return token
    except Exception as e:
        logger.error(f"Error obteniendo token OAuth: {e}")
        return None


def ml_get(url: str, params: dict = None) -> Optional[requests.Response]:
    token = get_access_token()
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    for attempt in range(3):
        try:
            resp = SESSION.get(url, params=params, headers=headers, timeout=15)

            if resp.status_code == 401 and ML_CLIENT_ID:
                _token_cache["expires_at"] = 0
                token = get_access_token()
                if token:
                    headers["Authorization"] = f"Bearer {token}"
                continue

            if resp.status_code in (429, 503):
                wait = 2 ** attempt * 5
                logger.warning(f"Rate limit {resp.status_code}, esperando {wait}s...")
                time.sleep(wait)
                continue

            if resp.status_code == 403:
                logger.error(
                    "403 Forbidden: ML bloquea IPs de datacenter sin OAuth. "
                    "Configura ML_CLIENT_ID + ML_CLIENT_SECRET. "
                    "Regístrate gratis en https://developers.mercadolibre.com.mx/"
                )
                return None

            resp.raise_for_status()
            return resp

        except requests.exceptions.RequestException as e:
            if attempt == 2:
                logger.error(f"Error de red tras 3 intentos: {e}")
                return None
            time.sleep(3)

    return None


def build_affiliate_url(product_url: str) -> str:
    return AFFILIATE_LINK


def search_deals(query: str) -> list[dict]:
    deals = []
    resp = ml_get(
        f"{ML_API_BASE}/sites/{ML_SITE}/search",
        params={"q": query, "limit": ML_SEARCH_LIMIT, "sort": "relevance"},
    )
    if not resp:
        return deals

    try:
        results = resp.json().get("results", [])
        logger.info(f"[{query}] -> {len(results)} resultados")

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
                "title": item.get("title", "Sin titulo"),
                "original_price": original_price,
                "current_price": current_price,
                "discount": discount,
                "thumbnail": thumbnail,
                "permalink": permalink,
                "affiliate_url": build_affiliate_url(permalink),
                "condition": item.get("condition", "new"),
                "sold_quantity": item.get("sold_quantity", 0),
            })

        logger.info(f"[{query}] -> {len(deals)} ofertas con >={MIN_DISCOUNT_PERCENT}% descuento")
    except Exception as e:
        logger.error(f"Error procesando respuesta de '{query}': {e}")

    return deals


def format_price(amount: float) -> str:
    return f"${amount:,.0f}"


def format_message(deal: dict) -> str:
    condition_map = {"new": "Nuevo", "used": "Usado", "refurbished": "Reacondicionado"}
    condition = condition_map.get(deal["condition"], deal["condition"])

    msg = (
        f"Oferta: *{deal['title']}*\n\n"
        f"Precio original: {format_price(deal['original_price'])}\n"
        f"Precio oferta: *{format_price(deal['current_price'])}*\n"
        f"Descuento: *{deal['discount']}%*\n"
        f"Estado: {condition}\n"
    )
    if deal["sold_quantity"] > 0:
        msg += f"Vendidos: {deal['sold_quantity']:,}\n"

    msg += (
        f"\n[Ver en Mercado Libre]({deal['permalink']})\n"
        f"[Link de afiliado]({deal['affiliate_url']})"
    )
    return msg
