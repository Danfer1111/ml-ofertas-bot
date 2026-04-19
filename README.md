# 🤖 Bot de Ofertas Mercado Libre — Telegram

Publica automáticamente productos con ≥40% de descuento en tu canal/chat de Telegram con link de afiliado.

---

## Archivos

```
├── main.py            # Bot principal + scheduler
├── mercadolibre.py    # Búsqueda y formateo de ofertas
├── config.py          # Configuración centralizada
├── requirements.txt   # Dependencias
└── render.yaml        # Deploy en Render.com
```

---

## Instalación local

### 1. Requisitos
- Python 3.10+
- pip

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 3. Credenciales
Las credenciales ya están en `config.py`. Si prefieres variables de entorno:
```bash
export BOT_TOKEN="tu_token"
export CHAT_ID="tu_chat_id"
export AFFILIATE_LINK="tu_link"
```

### 4. Ejecutar
```bash
python main.py
```

---

## Despliegue en Render.com (gratis)

### Paso 1 — Subir a GitHub
```bash
git init
git add .
git commit -m "Bot ML Ofertas"
git remote add origin https://github.com/TU_USUARIO/ml-bot.git
git push -u origin main
```

### Paso 2 — Crear cuenta en Render
1. Ve a https://render.com y regístrate (gratis)
2. Click en **"New +"** → **"Blueprint"** (usa render.yaml) O manualmente:

### Paso 3 — Nuevo servicio (manual, recomendado)
1. **New +** → **Background Worker**
2. Conecta tu repositorio de GitHub
3. Configuración:
   - **Name:** `ml-ofertas-bot`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
   - **Plan:** Free

### Paso 4 — Variables de entorno
En el dashboard de Render → tu servicio → **Environment**:

| Key | Value |
|-----|-------|
| `BOT_TOKEN` | `8759115195:AAEUEQ-...` |
| `CHAT_ID` | `1803571733` |
| `AFFILIATE_LINK` | `https://meli.la/1Y2v7jp` |

### Paso 5 — Deploy
Click **"Deploy"**. Los logs aparecen en tiempo real.

> ⚠️ **Render Free tier** suspende workers inactivos. Para mantenerlo siempre activo considera el plan Starter ($7/mes) o usa Railway.app como alternativa gratuita.

---

## Personalización

### Cambiar categorías de búsqueda (`config.py`)
```python
SEARCH_QUERIES = [
    "electronica",
    "celulares",
    "laptops",
    # agrega los que quieras
]
```

### Cambiar descuento mínimo
```python
MIN_DISCOUNT_PERCENT = 40   # cambia a 30, 50, etc.
```

### Cambiar frecuencia
```python
SEARCH_INTERVAL_HOURS = 6   # cada cuántas horas buscar
```

### Cambiar máximo de productos por ciclo
```python
MAX_PRODUCTS_PER_RUN = 10   # máx. mensajes por búsqueda
```

---

## Cómo funciona el link de afiliado

La API pública de Mercado Libre no expone endpoints de afiliados. El bot usa tu link base (`AFFILIATE_LINK`) que redirige a ML con tu tracking, y también incluye el permalink directo del producto. Cuando el usuario hace clic en tu link de afiliado, el programa de afiliados registra la visita.

Para tracking más granular por producto, inscríbete en el **Programa de Afiliados de ML** y genera deeplinks desde su panel.

---

## Logs esperados

```
2026-04-15 10:00:00 [INFO] main: Bot autenticado: @tu_bot (id=123456)
2026-04-15 10:00:01 [INFO] main: Iniciando búsqueda...
2026-04-15 10:00:03 [INFO] mercadolibre: [celulares] → 50 resultados
2026-04-15 10:00:03 [INFO] mercadolibre: [celulares] → 7 ofertas con ≥40% descuento
2026-04-15 10:00:05 [INFO] main:   ✓ [MLM123] iPhone 13... | -45% | $8,999
2026-04-15 10:00:07 [INFO] main: Ciclo finalizado — 8 oferta(s) enviadas.
```
