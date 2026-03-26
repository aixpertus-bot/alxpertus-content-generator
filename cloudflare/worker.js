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
        
        await env.alxpertus_content.prepare(
          "UPDATE posts SET enlace = ?, estado = 'publicado' WHERE id = ?"
        ).bind(body.enlace || "", postId).run();
        
        return new Response(JSON.stringify({ success: true, post_id: postId }), { headers });
      }

      if (path === "/publicar/linkedin" && request.method === "POST") {
        const body = await request.json();
        const { post_id, contenido, titulo } = body;
        
        if (!post_id || !contenido) {
          return new Response(JSON.stringify({ error: "post_id y contenido requeridos" }), { status: 400, headers });
        }
        
        const result = await publicarLinkedIn(env, contenido, titulo);
        
        if (result.error) {
          return new Response(JSON.stringify({ error: result.error }), { status: 500, headers });
        }
        
        await env.alxpertus_content.prepare(
          "UPDATE posts SET enlace = ?, estado = 'publicado' WHERE id = ?"
        ).bind(result.url, post_id).run();
        
        return new Response(JSON.stringify({ success: true, url: result.url, linkedin_id: result.id }), { headers });
      }

      if (path === "/publicar/x" && request.method === "POST") {
        const body = await request.json();
        const { post_id, contenido, titulo } = body;
        
        if (!post_id || !contenido) {
          return new Response(JSON.stringify({ error: "post_id y contenido requeridos" }), { status: 400, headers });
        }
        
        const result = await publicarX(env, contenido);
        
        if (result.error) {
          return new Response(JSON.stringify({ error: result.error }), { status: 500, headers });
        }
        
        await env.alxpertus_content.prepare(
          "UPDATE posts SET enlace = ?, estado = 'publicado' WHERE id = ?"
        ).bind(result.url, post_id).run();
        
        return new Response(JSON.stringify({ success: true, url: result.url, x_id: result.id }), { headers });
      }

      if (path === "/publicar/reddit" && request.method === "POST") {
        const body = await request.json();
        const { post_id, contenido, titulo, subreddit } = body;
        
        if (!post_id || !contenido) {
          return new Response(JSON.stringify({ error: "post_id y contenido requeridos" }), { status: 400, headers });
        }
        
        const sub = subreddit || "growmybusinessnow";
        const result = await publicarReddit(env, titulo, contenido, sub);
        
        if (result.error) {
          return new Response(JSON.stringify({ error: result.error }), { status: 500, headers });
        }
        
        await env.alxpertus_content.prepare(
          "UPDATE posts SET enlace = ?, estado = 'publicado' WHERE id = ?"
        ).bind(result.url, post_id).run();
        
        return new Response(JSON.stringify({ success: true, url: result.url, reddit_id: result.id }), { headers });
      }

      // === N8N WEBHOOK ENDPOINT ===
      // Envía el contenido a un webhook de n8n para publicación automática
      if (path === "/publicar/n8n" && request.method === "POST") {
        const body = await request.json();
        const { post_id, plataforma, contenido, titulo, imagen_url } = body;
        
        if (!post_id || !contenido || !plataforma) {
          return new Response(JSON.stringify({ error: "post_id, contenido y plataforma requeridos" }), { status: 400, headers });
        }
        
        // URL del webhook de n8n (configurable en env)
        const n8n_webhook = env.N8N_WEBHOOK_URL;
        
        if (!n8n_webhook) {
          return new Response(JSON.stringify({ error: "N8N_WEBHOOK_URL no configurado en env" }), { status: 500, headers });
        }
        
        // Preparar payload para n8n
        const n8n_payload = {
          action: "publicar",
          plataforma: plataforma,
          post_id: post_id,
          titulo: titulo,
          contenido: contenido,
          imagen_url: imagen_url,
          timestamp: new Date().toISOString()
        };
        
        // Enviar a n8n
        try {
          const n8n_response = await fetch(n8n_webhook, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(n8n_payload)
          });
          
          if (n8n_response.ok) {
            const n8n_result = await n8n_response.json();
            
            // Actualizar estado en DB
            await env.alxpertus_content.prepare(
              "UPDATE posts SET estado = 'publicado', enlace = ? WHERE id = ?"
            ).bind(n8n_result.url || "", post_id).run();
            
            return new Response(JSON.stringify({ 
              success: true, 
              message: "Enviado a n8n para publicación",
              n8n_response: n8n_result
            }), { headers });
          } else {
            return new Response(JSON.stringify({ error: "Error enviando a n8n" }), { status: 500, headers });
          }
        } catch (e) {
          return new Response(JSON.stringify({ error: e.message }), { status: 500, headers });
        }
      }

      // === SERIE COMPLETA CON N8N ===
      // Genera serie y envía a n8n para publicación (async)
      if (path === "/generar-serie-n8n" && request.method === "POST") {
        const body = await request.json();
        const { tipo, industria } = body;
        
        // Responder inmediatamente y procesar en background
        const responseId = Date.now().toString();
        
        waitUntil(async () => {
          try {
            console.log("Generando serie completa en background...");
            
            // Generar serie completa
            const serie = await generarSerieCompleta(env, tipo, industria);
            
            // Guardar posts
            const posts_guardados = [];
            
            for (const [plataforma, contenido] of Object.entries(serie)) {
              const postId = await guardarPost(env, {
                titulo: contenido.titulo,
                plataforma,
                tipo,
                industria,
                contenido: contenido.texto,
                estado: "borrador"
              });
              
              // Asignar imagen a blog/linkedin/x (reddit sin imagen)
              if (plataforma !== "reddit" && serie.blog?.imagen) {
                await env.alxpertus_content.prepare(
                  "UPDATE posts SET imagen_url = ? WHERE id = ?"
                ).bind(serie.blog.imagen, postId).run();
              }
              
              posts_guardados.push({ plataforma, id: postId, titulo: contenido.titulo });
            }
            
            console.log("Posts guardados:", posts_guardados.length);
            
            // Enviar todos a n8n para publicación
            const n8n_webhook = env.N8N_WEBHOOK_URL;
            
            if (n8n_webhook) {
              const n8n_payload = {
                action: "publicar_serie",
                posts: posts_guardados,
                serie: serie,
                responseId: responseId,
                timestamp: new Date().toISOString()
              };
              
              await fetch(n8n_webhook, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(n8n_payload)
              });
              
              console.log("Enviado a n8n");
            }
          } catch (e) {
            console.error("Error en generación de serie:", e);
          }
        });
        
        return new Response(JSON.stringify({
          success: true,
          message: "Serie iniciada. Procesando en background.",
          responseId: responseId
        }), { headers });
      }

      return new Response(JSON.stringify({ error: "Not found" }), { status: 404, headers });
    } catch (e) {
      return new Response(JSON.stringify({ error: e.message }), { status: 500, headers });
    }
  }
};

const TEMA_CENTRAL = "AI Agents Teams: Your New Digital Workforce in 2026";

const SERIES_BIBLE = `SERIES BIBLE — MANDATORY CONTEXT:

CHARACTERS — retired, do not reuse:
- Rachel / Rachel Jenkins: marketing director, appeared in Art. 7 and 12. RETIRED.
- Emily: marketing director, appeared in Art. 9. RETIRED.
- Sarah: marketing director, appeared in Art. 8, 15, 17. OVERUSED. Rest this character minimum 3 articles.

STATISTICS — already published, do not repeat:
- 35% sales increase + 25% complaint reduction (retail client, Art. 6, 12, 17)
- 30% campaign improvement (Sarah, Art. 8, 17)
- 37% campaign effectiveness (Emily, Art. 9, 17)
- 25% sales increase (Rachel Jenkins, Art. 12)

THESIS POSITIONS — already taken:
- AI augments, doesn't replace (Art. 5, 7)
- AI replaces experienced workers first (Art. 6, 10, 13, 16)
- AI exposes inefficiencies in workflow (Art. 8, 11, 14)
- AI redefines what expertise means (Art. 9)
- Senior talent unlocks AI potential (Art. 12)
- AI exposes insecurities, not just inefficiencies (Art. 15)

X CLAIM — retired until further notice:
- "AI replaces experienced/senior workers first"
  Used in posts 10, 13, 16. Do not use again.

NEXT ARTICLE REQUIREMENTS:
- New character: different industry, different role, not marketing, not a director
- New statistic: do not reference any number above
- New thesis: must differ from all positions listed above
- New angle for X: unrelated to replacement/displacement

FINAL OUTPUT RULES — NON-NEGOTIABLE:
- Deliver ONLY the finished article
- No subheadings that mirror the prompt structure
- No horizontal separators between sections
- No labels like "Central Story:" or "Core Thesis:"
- No explanatory notes about your choices
- Transitions between sections must be narrative, not structural
- The reader should never see the template

---`;

const X_SYSTEM_PROMPT = `You are an expert X/Twitter Article writer specializing in AI Agents and the future of work. You write long-form articles with cover images that establish authority and provoke genuine debate.

CRITICAL: These instructions are invisible scaffolding. Never let the structure show in the final output. The reader should feel a person wrote this, not that someone followed a template.

AUTHOR CONTEXT:
- Consultant with direct experience implementing AI Agent teams
- Audience: tech professionals, founders, operators, and senior managers
- Tone: sharp, direct, occasionally provocative — but always intellectually honest

FORMAT: X Article (long-form)
- Target length: 800–1,200 words
- Structure: narrative prose with H2 subheadings where natural
- Supports bold, italic, blockquotes, images
- The first 280 characters visible in the feed MUST be an irresistible hook

MANDATORY STRUCTURE:
1. TITLE — punchy, specific, under 80 characters
   a) "[Number] lessons from [specific experience]"
   b) "The [topic] problem nobody talks about"
   c) "[Contrarian claim]. Here's my proof."

2. OPENING HOOK (first 280 characters visible in feed):
   - Must make someone stop scrolling and click "Show more"
   - A counterintuitive observation OR the start of a story with immediate tension
   - BANNED: "In today's world...", "As AI continues to evolve...", "Excited to share..."

3. BODY:
   - One real, specific protagonist or case: name, age, role, industry
   - Genuine conflict: MUST resist, doubt, or fail before improving
   - Concrete measurable result
   - Second layer to thesis OR counterargument genuinely engaged

4. CLOSING: Open question inviting reader to share experience
   - BANNED: "Are you ready to face the truth?"

5. IMAGE DESCRIPTION: At the end of the article, include a line starting with "[COVER IMAGE:" followed by a detailed description of what the cover image should depict. This will be used to generate the article's visual.

STYLE:
✅ Short paragraphs (1-3 sentences)
✅ Single line breaks between ideas for visual breathing room
✅ Specificity over generality — use numbers, timeframes
✅ Conversational, like talking to a smart friend
✅ Use bold for key phrases sparingly

PROHIBITIONS:
❌ Emoji as punctuation
❌ "This changes everything" / "Game changer"
❌ Bullet-point lists as backbone
❌ Engagement bait
❌ Corporate vocabulary (leverage, synergy, ecosystem)

FINAL OUTPUT RULES — NON-NEGOTIABLE:
- Deliver ONLY the finished article
- No subheadings that mirror the prompt structure
- No horizontal separators between sections
- No labels like "Central Story:" or "Core Thesis:"
- No explanatory notes about your choices
- Transitions between sections must be narrative, not structural
- The reader should never see the template.`;

const REDDIT_SYSTEM_PROMPT = `You are an expert Reddit writer specializing in AI Agents and the future of work. You write posts that generate genuine discussion and establish quiet authority without marketing yourself.

CRITICAL: These instructions are invisible scaffolding. Never let the structure show in the final output. The reader should feel a person wrote this, not that someone followed a template.

AUTHOR CONTEXT:
- Consultant with direct experience implementing AI Agent teams
- Target subreddits: r/artificial, r/MachineLearning, r/ChatGPT, r/Entrepreneur, r/consulting
- Tone: honest, self-aware, willing to be wrong — Reddit rewards intellectual humility

FORMAT OPTIONS:
A) EXPERIENCE POST: "I've done X. Here's what I actually found."
B) QUESTION POST: "Has anyone else seen X? Trying to understand if this is just my experience."
C) CASE STUDY POST: "We implemented X at a mid-size company. Results were not what we expected."

TITLE RULES:
✅ Specific and factual: "After implementing AI Agents in 8 companies, the biggest obstacle was never the technology"
✅ Honest about uncertainty: "I thought AI Agents would replace junior staff first. I was completely wrong."
❌ BANNED: "X things you need to know about AI Agents", "The future of work is here"

POST STRUCTURE:
- OPENING: State position plainly, acknowledge counterargument immediately
- BODY: Tell what happened, include the failure or surprise, specific details
- THE HONEST PART: What did not work, what you still don't understand, what you would do differently
- CLOSING: A genuine question, not a CTA

PROHIBITIONS:
❌ No self-promotion or calls to follow
❌ No "thought leadership" framing
❌ No symmetrical lists of benefits
❌ No corporate vocabulary (leverage, synergy, ecosystem)
❌ No claiming certainty you don't have
❌ No ignoring the downside of your argument

FINAL OUTPUT RULES — NON-NEGOTIABLE:
- Deliver ONLY the finished article
- No subheadings that mirror the prompt structure
- No horizontal separators between sections
- No labels like "Central Story:" or "Core Thesis:"
- No explanatory notes about your choices
- Transitions between sections must be narrative, not structural
- The reader should never see the template.`;

async function generarContenido(env, plataforma, tipo, industria) {
  const plataformas = {
    linkedin: {
      systemPrompt: SERIES_BIBLE + `\n\nYou are an expert LinkedIn article writer specializing in AI Agents and the future of work. Your writing combines real hands-on consulting experience with honest narrative and genuinely counterintuitive perspective.

CRITICAL: These instructions are invisible scaffolding. Never let the structure show in the final output. The reader should feel a person wrote this, not that someone followed a template.

AUTHOR CONTEXT:
- Consultant with direct experience implementing AI Agent teams in mid-to-large organizations
- Audience: C-suite executives, senior managers, and high-level professionals
- Tone: reflective, direct, human — never corporate, never alarmist
- This is a content series: characters, cases, and statistics must remain consistent

FORMAT: LinkedIn Article (long-form)
- Target length: 800–1,200 words
- Structure: narrative prose with optional subheadings
- No bullet-point lists as the backbone

MANDATORY STRUCTURE:
1. TITLE — choose ONE format:
   a) "[Specific detail about a real person]. Here's what happened [concrete timeframe] later."
   b) "The uncomfortable truth about [topic] that no one in your industry wants to admit"
   c) "Why [common belief] is wrong — and what to do instead"
   RULE: The title must deliver exactly what the article promises. No bait-and-switch.

2. OPENING HOOK (first 2–3 sentences):
   - A counterintuitive observation OR the start of a story with immediate tension
   - BANNED: "As we navigate the complexities of...", "In today's rapidly evolving landscape..."

3. CENTRAL STORY:
   - One real, specific protagonist: name, age, role, industry
   - Genuine conflict: MUST resist, doubt, or fail before improving
   - BANNED: frictionless success stories

4. CORE THESIS:
   - Must go beyond 2026 consensus
   - AVOID: "AI augments, it doesn't replace", "You need an AI strategy", "Senior workers are most automatable"

5. MEASURABLE RESULT: One concrete number after the story

6. DEPTH SECTION: second layer to thesis OR counterargument genuinely engaged

7. CLOSING: Open question inviting reader to share experience
   - BANNED: "Are you ready to face the truth?"
   - CORRECT: "Where in your workflow would AI reveal something you're not ready to see?"

8. HASHTAGS: Maximum 4, at least 2 specific (#AIStrategy, #AIAgents, #EnterpriseAI)

FINAL OUTPUT RULES — NON-NEGOTIABLE:
- Deliver ONLY the finished article
- No subheadings that mirror the prompt structure
- No horizontal separators between sections
- No labels like "Central Story:" or "Core Thesis:"
- No explanatory notes about your choices
- Transitions between sections must be narrative, not structural
- The reader should never see the template.`,
      userMessage: (tipo, industria) => {
        const msgs = {
          general: "Write a LinkedIn article about AI Agents in the workplace. The protagonist is a senior professional. Their core resistance is what they struggle to accept. The thesis is an idea that goes against current consensus. The measurable result is concrete outcome.",
          industria: `Write about AI Agents in ${industria || 'business'}. Include specific case study with human story and resistance.`,
          tendencia: "Make a prediction about AI Agents that goes against current consensus with specific evidence.",
          practica: "Write about implementing AI Agents with real failures, surprises, and lessons learned."
        };
        return msgs[tipo] || msgs.general;
      }
    },
    x: {
      systemPrompt: SERIES_BIBLE + "\n\n" + X_SYSTEM_PROMPT,
      userMessage: (tipo, industria) => {
        const msgs = {
          general: "Write an X Article about AI Agents in the workplace. The protagonist is a senior professional. Their core resistance is what they struggle to accept. The thesis is an idea that goes against current consensus. The measurable result is concrete outcome. Include a cover image description at the end.",
          industria: `Write an X Article about AI Agents in ${industria || 'business'}. Include specific case study with human story and resistance. Include a cover image description at the end.`,
          tendencia: "Write an X Article making a prediction about AI Agents that goes against current consensus with specific evidence. Include a cover image description at the end.",
          practica: "Write an X Article about implementing AI Agents with real failures, surprises, and lessons learned. Include a cover image description at the end."
        };
        return msgs[tipo] || msgs.general;
      }
    },
    reddit: {
      systemPrompt: SERIES_BIBLE + "\n\n" + REDDIT_SYSTEM_PROMPT,
      userMessage: (tipo, industria) => {
        const msgs = {
          general: "Write a Reddit post (experience/observation) about AI Agents. Start with 'I've done X. Here's what I actually found.' Include honest failures and what you still don't understand. Ask a genuine question at the end.",
          industria: `Write a Reddit case study about AI Agents in ${industria || 'business'}. What happened? What broke? What would you do differently?`,
          tendencia: "Write a Reddit question post: 'Has anyone else seen X? Trying to understand if this is just my experience.' Be honest about uncertainty.",
          practica: "Write a Reddit post about implementing AI Agents - be honest about what failed, what surprised you. Reddit rewards intellectual humility."
        };
        return msgs[tipo] || msgs.general;
      }
    }
  };

  const config = plataformas[plataforma] || plataformas.linkedin;

  const response = await env.AI.run(
    "@cf/qwen/qwq-32b",
    {
      messages: [
        { role: "system", content: config.systemPrompt },
        { role: "user", content: config.userMessage(tipo, industria) + "\n\nWrite it now." }
      ],
      max_tokens: 1500
    }
  );

  let texto = response.response;
  
  // Strip reasoning blocks from reasoning models
  texto = texto.replace(/<think>[\s\S]*?<\/think>/g, '').trim();
  
  const lineas = texto.split("\n");
  const titulo = lineas[0].replace(/^#*\s*/, "").slice(0, 200);

  return { titulo, texto };
}

async function guardarPost(env, post) {
  const stmt = await env.alxpertus_content.prepare(
    "INSERT INTO posts (titulo, plataforma, tipo, industria, contenido, estado, fecha_creacion) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))"
  ).bind(post.titulo, post.plataforma, post.tipo, post.industria || null, post.contenido, post.estado || "borrador");
  
  const result = await stmt.run();
  return result.meta.last_row_id;
}

async function obtenerPosts(env, limite = 100) {
  const { results } = await env.alxpertus_content.prepare(
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
  const { results } = await env.alxpertus_content.prepare(
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
  await env.alxpertus_content.prepare(
    "UPDATE posts SET imagen_url = ? WHERE id = ?"
  ).bind(url, postId).run();
}

async function obtenerStats(env) {
  const total = await env.alxpertus_content.prepare("SELECT COUNT(*) as count FROM posts").first();
  
  const porPlataforma = {};
  for (const plat of ["linkedin", "x", "reddit"]) {
    const r = await env.alxpertus_content.prepare(`SELECT COUNT(*) as count FROM posts WHERE plataforma = ?`).bind(plat).first();
    porPlataforma[plat] = r.count;
  }

  const porTipo = {};
  for (const tipo of ["general", "industria", "tendencia", "practico"]) {
    const r = await env.alxpertus_content.prepare(`SELECT COUNT(*) as count FROM posts WHERE tipo = ?`).bind(tipo).first();
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
  const response = await fetch("https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell", {
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

async function publicarLinkedIn(env, contenido, titulo) {
  const authorUrn = "urn:li:person:78mka4g0e964zl";
  
  const linkedInPost = {
    author: authorUrn,
    lifecycleState: "PUBLISHED",
    specificContent: {
      "com.linkedin.ugc.ShareContent": {
        shareCommentary: {
          text: contenido.slice(0, 3000)
        },
        shareMediaCategory: "NONE"
      }
    },
    visibility: {
      "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
    }
  };

  const response = await fetch("https://api.linkedin.com/v2/ugcPosts", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${env.LINKEDIN_ACCESS_TOKEN}`,
      "Content-Type": "application/json",
      "X-Restli-Protocol-Version": "2.0.0"
    },
    body: JSON.stringify(linkedInPost)
  });

  if (!response.ok) {
    const err = await response.text();
    return { error: `LinkedIn API Error: ${err.slice(0, 200)}` };
  }

  const linkedInId = response.headers.get("x-restli-id") || "unknown";
  const urnParts = linkedInId.split(":");
  const postId = urnParts[urnParts.length - 1];
  
  return {
    id: postId,
    url: `https://www.linkedin.com/feed/update/urn:li:share:${postId}`
  };
}

async function publicarX(env, contenido) {
  const apiKey = env.X_API_KEY;
  const apiSecret = env.X_API_SECRET;
  const accessToken = env.X_ACCESS_TOKEN;
  const accessTokenSecret = env.X_ACCESS_TOKEN_SECRET;
  
  if (!apiKey || !apiSecret || !accessToken || !accessTokenSecret) {
    return { error: "X API credentials not configured" };
  }

  const text = contenido.slice(0, 280);
  
  const nonce = Math.random().toString(36).substring(2, 15);
  const timestamp = Math.floor(Date.now() / 1000).toString();
  
  const params = {
    oauth_consumer_key: apiKey,
    oauth_token: accessToken,
    oauth_signature_method: "HMAC-SHA1",
    oauth_timestamp: timestamp,
    oauth_nonce: nonce,
    oauth_version: "1.0",
    text: text
  };
  
  const sortedParams = Object.keys(params).sort().map(k => `${encodeURIComponent(k)}=${encodeURIComponent(params[k])}`).join('&');
  const signatureBase = `POST&${encodeURIComponent('https://api.x.com/2/tweets')}&${encodeURIComponent(sortedParams)}`;
  
  const signingKey = `${encodeURIComponent(apiSecret)}&${encodeURIComponent(accessTokenSecret)}`;
  const signature = await hmacSha1(signingKey, signatureBase);
  
  params.oauth_signature = signature;
  
  const authHeader = 'OAuth ' + Object.keys(params)
    .filter(k => k.startsWith('oauth_'))
    .map(k => `${encodeURIComponent(k)}="${encodeURIComponent(params[k])}"`)
    .join(', ');

  const response = await fetch("https://api.x.com/2/tweets", {
    method: "POST",
    headers: {
      "Authorization": authHeader,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ text })
  });

  if (!response.ok) {
    const err = await response.text();
    return { error: `X API Error: ${err.slice(0, 200)}` };
  }

  const data = await response.json();
  return {
    id: data.data.id,
    url: `https://x.com/i/status/${data.data.id}`
  };
}

async function hmacSha1(key, message) {
  const encoder = new TextEncoder();
  const keyData = encoder.encode(key);
  const msgData = encoder.encode(message);
  
  const cryptoKey = await crypto.subtle.importKey(
    "raw",
    keyData,
    { name: "HMAC", hash: "SHA-1" },
    false,
    ["sign"]
  );
  
  const signature = await crypto.subtle.sign("HMAC", cryptoKey, msgData);
  
  return btoa(String.fromCharCode(...new Uint8Array(signature)));
}

async function publicarReddit(env, titulo, contenido, subreddit) {
  const clientId = env.REDDIT_CLIENT_ID;
  const clientSecret = env.REDDIT_CLIENT_SECRET;
  const username = env.REDDIT_USERNAME;
  const password = env.REDDIT_PASSWORD;
  
  if (!clientId || !clientSecret || !username || !password) {
    return { error: "Reddit credentials not configured" };
  }

  const authString = btoa(`${clientId}:${clientSecret}`);
  
  const tokenResponse = await fetch("https://www.reddit.com/api/v1/access_token", {
    method: "POST",
    headers: {
      "Authorization": `Basic ${authString}`,
      "Content-Type": "application/x-www-form-urlencoded"
    },
    body: `grant_type=password&username=${username}&password=${password}`
  });

  if (!tokenResponse.ok) {
    const err = await tokenResponse.text();
    return { error: `Reddit auth error: ${err.slice(0, 100)}` };
  }

  const tokenData = await tokenResponse.json();
  const accessToken = tokenData.access_token;

  const redditPost = {
    sr: subreddit,
    kind: "self",
    title: titulo.slice(0, 300),
    text: contenido.slice(0, 10000)
  };

  const postResponse = await fetch("https://oauth.reddit.com/api/submit", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${accessToken}`,
      "Content-Type": "application/x-www-form-urlencoded"
    },
    body: new URLSearchParams(redditPost).toString()
  });

  if (!postResponse.ok) {
    const err = await postResponse.text();
    return { error: `Reddit post error: ${err.slice(0, 100)}` };
  }

  const postData = await postResponse.json();
  
  return {
    id: postData.json.data.id,
    url: `https://reddit.com/r/${subreddit}/comments/${postData.json.data.id}`
  };
}

// === GENERAR SERIE COMPLETA ===
async function generarSerieCompleta(env, tipo = "general", industria = null) {
  const serie = {};
  
  // Blog (con imagen)
  console.log("Generando Blog...");
  serie.blog = await generarContenido(env, "blog", tipo, industria);
  
  // LinkedIn (reutiliza imagen del blog)
  console.log("Generando LinkedIn...");
  serie.linkedin = await generarContenido(env, "linkedin", tipo, industria);
  
  // X (reutiliza imagen del blog)
  console.log("Generando X...");
  serie.x = await generarContenido(env, "x", tipo, industria);
  
  // Reddit (sin imagen)
  console.log("Generando Reddit...");
  serie.reddit = await generarContenido(env, "reddit", tipo, industria);
  
  return serie;
}