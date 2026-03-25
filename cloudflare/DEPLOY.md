# Despliegue a Cloudflare

## Requisitos Previos

1. **Cuenta de Cloudflare** - Crear en cloudflare.com
2. **Wrangler CLI** - `npm install -g wrangler`
3. **Token de Hugging Face** - Obtener en huggingface.co/settings/tokens

## Variables de Entorno Necesarias

```bash
# .env para desarrollo local
GROQ_API_KEY=gsk_...
HUGGING_FACE_TOKEN=hf_...
```

## Paso 1: Iniciar sesión en Cloudflare

```bash
wrangler login
```

## Paso 2: Crear la base de datos D1

```bash
cd cloudflare
wrangler d1 create alxpertus-content
```

Copia el `database_id` resultante y actualiza `wrangler.toml`:

```toml
[[d1_databases]]
binding = "DB"
database_name = "alxpertus-content"
database_id = "TU_DATABASE_ID_AQUI"
```

## Paso 3: Crear las tablas

```bash
wrangler d1 execute alxpertus-content --command="
CREATE TABLE IF NOT EXISTS posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  titulo TEXT NOT NULL,
  plataforma TEXT NOT NULL,
  tipo TEXT NOT NULL,
  industria TEXT,
  contenido TEXT,
  enlace TEXT,
  imagen_url TEXT,
  estado TEXT DEFAULT 'borrador',
  fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP,
  fecha_publicacion TEXT,
  fecha_programada TEXT
);
"
```

## Paso 4: Desplegar el Worker

```bash
wrangler deploy
```

## Paso 5: Desplegar el Dashboard (Cloudflare Pages)

1. Ve a Cloudflare Dashboard > Pages
2. Conecta tu repositorio de GitHub
3. Selecciona la carpeta `dashboard-html`
4. Deploy!

## URLs Resultantes

- **API**: `https://alxpertus-content.your-subdomain.workers.dev`
- **Dashboard**: `https://alxpertus-content.pages.dev`

## Probar la API

```bash
# Health check
curl https://tu-worker.workers.dev/health

# Generar post
curl -X POST https://tu-worker.workers.dev/generar \
  -H "Content-Type: application/json" \
  -d '{"plataforma":"linkedin","tipo":"general"}'

# Ver posts
curl https://tu-worker.workers.dev/posts

# Generar imagen
curl -X POST https://tu-worker.workers.dev/posts/1/imagen
```

## Notas

- El límite gratuito de Cloudflare Workers es 100,000 solicitudes/día
- Hugging Face FLUX tiene límite gratuito mensual (~1000 imágenes)
- Groq tiene límite gratuito generoso