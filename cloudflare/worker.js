export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;
    
    const headers = {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*"
    };

    if (request.method === "OPTIONS") {
      return new Response("", {
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type"
        }
      });
    }

    try {
      if (path === "/health") {
        return new Response(JSON.stringify({ status: "ok", service: "Alxpertus Content API" }), { headers });
      }

      if (path === "/generar" && request.method === "POST") {
        const body = await request.json();
        const { plataforma, tipo, industria } = body;
        
        const contenido = await generarContenido(env, plataforma, tipo, industria);
        
        const postId = await guardarPost(env, {
          titulo: contenido.titulo,
          plataforma,
          tipo,
          industria,
          contenido: contenido.texto,
          estado: "borrador"
        });

        return new Response(JSON.stringify({
          id: postId,
          contenido: contenido.texto,
          titulo: contenido.titulo,
          plataforma,
          tipo
        }), { headers });
      }

      if (path === "/posts" && request.method === "GET") {
        const posts = await obtenerPosts(env);
        return new Response(JSON.stringify(posts), { headers });
      }

      if (path.startsWith("/posts/") && path.endsWith("/imagen") && request.method === "POST") {
        const postId = path.split("/")[2];
        const post = await obtenerPostPorId(env, postId);
        
        if (!post) {
          return new Response(JSON.stringify({ error: "Post no encontrado" }), { status: 404, headers });
        }

        const prompt = generarPromptImagen(post.tipo, post.industria);
        const imagenResult = await generarImagenHF(env, prompt);

        if (imagenResult.error) {
          return new Response(JSON.stringify({ error: imagenResult.error }), { status: 500, headers });
        }

        await actualizarImagen(env, postId, imagenResult.url);

        return new Response(JSON.stringify({
          post_id: postId,
          imagen_url: imagenResult.url,
          prompt_usado: prompt
        }), { headers });
      }

      if (path.startsWith("/posts/") && request.method === "GET") {
        const postId = path.split("/")[2];
        const post = await obtenerPostPorId(env, postId);
        
        if (!post) {
          return new Response(JSON.stringify({ error: "Post no encontrado" }), { status: 404, headers });
        }
        
        return new Response(JSON.stringify(post), { headers });
      }

      if (path === "/stats" && request.method === "GET") {
        const stats = await obtenerStats(env);
        return new Response(JSON.stringify(stats), { headers });
      }

      if (path === "/webhook" && request.method === "GET") {
        const posts = await obtenerPosts(env, 1);
        if (posts.length === 0) {
          return new Response(JSON.stringify({ error: "No hay posts disponibles" }), { headers });
        }
        const post = await obtenerPostPorId(env, posts[0].id);
        return new Response(JSON.stringify({
          titulo: post.titulo,
          contenido: post.contenido,
          plataforma: post.plataforma,
          tipo: post.tipo,
          industria: post.industria,
          imagen_url: post.imagen_url
        }), { headers });
      }

      if (path === "/webhook" && request.method === "POST") {
        const body = await request.json();
        const postId = body.post_id;
        
        if (!postId) {
          return new Response(JSON.stringify({ error: "post_id requerido" }), { status: 400, headers });
        }
        
        await env.DB.prepare(
          "UPDATE posts SET enlace = ?, estado = 'publicado' WHERE id = ?"
        ).bind(body.enlace || "", postId).run();
        
        return new Response(JSON.stringify({ success: true, post_id: postId }), { headers });
      }

      return new Response(JSON.stringify({ error: "Not found" }), { status: 404, headers });
    } catch (e) {
      return new Response(JSON.stringify({ error: e.message }), { status: 500, headers });
    }
  }
};

const TEMA_CENTRAL = "Equipos de Agentes IA: Tu Nueva Fuerza de Trabajo Digital en 2026";

async function generarContenido(env, plataforma, tipo, industria) {
  const GROQ_URL = "https://api.groq.com/openai/v1/chat/completions";
  
  let systemPrompt = `Eres un experto en IA y automatización. Escribe contenido profesional para ${plataforma} sobre: ${TEMA_CENTRAL}`;
  
  const tipos = {
    general: "Contenido introductorio y general sobre el tema",
    industria: `Contenido específico para la industria: ${industria || "general"}`,
    tendencia: "Contenido sobre últimas tendencias y el futuro de los agentes IA",
    practico: "Contenido práctico con pasos accionables"
  };

  systemPrompt += `\n\nTipo de contenido: ${tipos[tipo] || tipos.general}`;
  systemPrompt += "\n\nTono: Profesional, educativo, no vender directamente. Construir autoridad.";

  const response = await fetch(GROQ_URL, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${env.GROQ_API_KEY}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      model: "llama-3.1-70b-versatile",
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: "Genera un post profesional y completo." }
      ],
      temperature: 0.7,
      max_tokens: 1500
    })
  });

  const data = await response.json();
  const texto = data.choices[0].message.content;
  
  const lineas = texto.split("\n");
  const titulo = lineas[0].replace(/^#*\s*/, "").slice(0, 200);

  return { titulo, texto };
}

async function guardarPost(env, post) {
  const stmt = await env.DB.prepare(
    "INSERT INTO posts (titulo, plataforma, tipo, industria, contenido, estado, fecha_creacion) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))"
  ).bind(post.titulo, post.plataforma, post.tipo, post.industria || null, post.contenido, post.estado || "borrador");
  
  const result = await stmt.run();
  return result.meta.last_row_id;
}

async function obtenerPosts(env, limite = 100) {
  const { results } = await env.DB.prepare(
    "SELECT id, titulo, plataforma, tipo, industria, estado, fecha_creacion FROM posts ORDER BY fecha_creacion DESC LIMIT ?"
  ).bind(limite).all();
  
  return results.map(row => ({
    id: row.id,
    titulo: row.titulo,
    plataforma: row.plataforma,
    tipo: row.tipo,
    industria: row.industria,
    estado: row.estado,
    fecha_creacion: row.fecha_creacion
  }));
}

async function obtenerPostPorId(env, id) {
  const { results } = await env.DB.prepare(
    "SELECT * FROM posts WHERE id = ?"
  ).bind(id).all();
  
  if (results.length === 0) return null;
  
  const row = results[0];
  return {
    id: row.id,
    titulo: row.titulo,
    plataforma: row.plataforma,
    tipo: row.tipo,
    industria: row.industria,
    contenido: row.contenido,
    imagen_url: row.imagen_url,
    enlace: row.enlace,
    estado: row.estado,
    fecha_creacion: row.fecha_creacion
  };
}

async function actualizarImagen(env, postId, url) {
  await env.DB.prepare(
    "UPDATE posts SET imagen_url = ? WHERE id = ?"
  ).bind(url, postId).run();
}

async function obtenerStats(env) {
  const total = await env.DB.prepare("SELECT COUNT(*) as count FROM posts").first();
  
  const porPlataforma = {};
  for (const plat of ["linkedin", "x", "reddit"]) {
    const r = await env.DB.prepare(`SELECT COUNT(*) as count FROM posts WHERE plataforma = ?`).bind(plat).first();
    porPlataforma[plat] = r.count;
  }

  const porTipo = {};
  for (const tipo of ["general", "industria", "tendencia", "practico"]) {
    const r = await env.DB.prepare(`SELECT COUNT(*) as count FROM posts WHERE tipo = ?`).bind(tipo).first();
    porTipo[tipo] = r.count;
  }

  return { total: total.count, por_plataforma: porPlataforma, por_tipo: porTipo };
}

function generarPromptImagen(tipoPost, industria) {
  const prompts = {
    general: "Minimalist modern illustration showing AI agents working together in a coordinated team, digital brain network, blue and white color palette, clean professional style, suitable for LinkedIn article cover",
    industria: `Professional illustration showing AI agents specialized for ${industria || "general"} industry working together, modern tech aesthetic, clean corporate style, LinkedIn article cover image`,
    tendencia: "Futuristic 2026 technology concept, AI agents and automation, modern minimal style, blue gradient, professional LinkedIn cover",
    practico: "Step-by-step technical illustration showing how to set up AI agents, clean diagram style, professional blue tones, LinkedIn article cover"
  };
  
  return prompts[tipoPost] || prompts.general;
}

async function generarImagenHF(env, prompt) {
  const response = await fetch("https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-dev", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${env.HF_TOKEN}`
    },
    body: JSON.stringify({
      inputs: prompt,
      parameters: { width: 1024, height: 1024 }
    })
  });

  if (!response.ok) {
    const err = await response.text();
    return { error: `HF Error: ${err.slice(0, 200)}` };
  }

  const blob = await response.blob();
  const base64 = await blobToBase64(blob);
  
  return { url: `data:image/png;base64,${base64}` };
}

async function blobToBase64(blob) {
  const buffer = await blob.arrayBuffer();
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}