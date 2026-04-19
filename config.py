import os

# === CREDENCIALES TELEGRAM ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "8759115195:AAEUEQ-a2kvjwv6SL70RR7XFceNYmw1TzzE")
CHAT_ID = os.getenv("CHAT_ID", "1803571733")
AFFILIATE_LINK = os.getenv("AFFILIATE_LINK", "https://meli.la/1Y2v7jp")

# === CREDENCIALES MERCADO LIBRE (OAuth — requerido en datacenter) ===
# Regístrate gratis en https://developers.mercadolibre.com.mx/
# Crea una app y copia el Client ID y Secret
ML_CLIENT_ID = os.getenv("ML_CLIENT_ID", "")        # ej: "1234567890123456"
ML_CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET", "") # ej: "AbCdEf1234567890AbCdEf"
ML_ACCESS_TOKEN = os.getenv("ML_ACCESS_TOKEN", "")   # alternativa: token estático

# === CONFIGURACIÓN DE BÚSQUEDA ===
MIN_DISCOUNT_PERCENT = 40
MAX_PRODUCTS_PER_RUN = 10
SEEN_IDS_LIMIT = 100
SEARCH_INTERVAL_HOURS = 6

SEARCH_QUERIES = [
    "electronica",
    "celulares",
    "laptops",
    "audifonos",
    "smartwatch",
    "televisores",
    "tablets",
    "videojuegos",
]

# === MERCADO LIBRE API ===
ML_SITE = "MLM"
ML_API_BASE = "https://api.mercadolibre.com"
ML_SEARCH_LIMIT = 50
