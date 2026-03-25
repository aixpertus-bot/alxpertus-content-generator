# 🤖 Alxpertus Content Generator

Sistema automatizado de generación de contenido para LinkedIn, X y Reddit sobre Equipos de Agentes IA.

## Características

- ✅ Generación de posts con IA (Groq - modelo gratuito)
- ✅ Generación de imágenes con IA (FLUX via Hugging Face)
- ✅ Programación de publicaciones
- ✅ Dashboard web
- ✅ Base de datos SQLite (local) o D1 (Cloudflare)
- ✅ Despliegue a Cloudflare Workers + Pages

## Estructura

```
Contenido/
├── backend/              # API local (FastAPI)
│   ├── generator.py      # Generador de contenido
│   ├── image_generator_hf.py  # Generador de imágenes
│   ├── api/main.py       # Endpoints
│   └── db/database.py    # Base de datos
├── cloudflare/           # Workers para despliegue
│   ├── worker.js
│   └── wrangler.toml
├── dashboard/            # Dashboard Streamlit (local)
├── dashboard-html/       # Dashboard HTML (Cloudflare Pages)
├── .env                  # Variables de entorno
└── requirements.txt
```

## Configuración

### 1. Variables de entorno (.env)

```bash
# Groq API (gratis)
GROQ_API_KEY=gsk_tu_api_key

# Hugging Face (gratis)
HUGGING_FACE_TOKEN=hf_tu_token

# OpenAI (opcional, si usas DALL-E)
# OPENAI_API_KEY=sk-...
```

### 2. Instalar dependencias (desarrollo local)

```bash
pip install -r requirements.txt
```

## Uso Local

### Iniciar API

```bash
python backend/api/main.py
# API: http://localhost:8000
```

### Iniciar Dashboard

```bash
streamlit run dashboard/main.py
# Dashboard: http://localhost:8501
```

## Despliegue a Cloudflare

Ver [cloudflare/DEPLOY.md](cloudflare/DEPLOY.md)

```bash
cd cloudflare
wrangler login
wrangler d1 create alxpertus-content
wrangler d1 execute alxpertus-content --command="CREATE TABLE posts (...)"
wrangler deploy
```

## API Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/generar` | Generar nuevo post |
| GET | `/posts` | Listar posts |
| GET | `/posts/{id}` | Ver post |
| POST | `/posts/{id}/imagen` | Generar imagen |
| GET | `/stats` | Estadísticas |

## Tecnologías

- **Texto**: Groq (Llama 3.1 70B)
- **Imágenes**: Hugging Face FLUX.1-dev
- **Cloudflare**: Workers + D1 + Pages
- **Dashboard**: Streamlit (local) / HTML (cloudflare)

## Licencia

MIT