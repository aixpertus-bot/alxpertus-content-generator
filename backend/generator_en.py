import os
import re
import json
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

TEMA_CENTRAL = "AI Agent Teams: Your New Digital Workforce in 2026"

# Plataformas
PLATAFORMAS_CON_IMAGEN = ["linkedin", "x", "blog"]
PLATAFORMAS_SIN_IMAGEN = ["reddit"]

def generar_post(tema_central: str, plataforma: str, tipo_post: str, industria: str = None) -> dict:
    """Generate content in English only"""
    
    industria_context = f"for {industria} industry" if industria else ""
    
    # Prompts específicos por plataforma
    prompts = {
        "blog": f"""You are writing a professional SEO-optimized blog article in English about {tema_central} {industria_context}.
Write a comprehensive, well-structured article (1500-2000 words) with:
- Catchy SEO title (H1)
- Meta description (150 chars)
- Introduction (hook the reader)
- 4-5 main sections with H2 headings
- Practical insights and examples
- Conclusion with CTA
Write in English only.""",

        "linkedin": f"""You are writing a LinkedIn ARTICLE (long-form post) in English about {tema_central} {industria_context}.
Write a comprehensive article (800-1200 words) with:
- Compelling title
- Personal story or hook opening
- Core content with insights
- Data points or examples
- Key takeaways
- Thought-provoking question at end
- Hashtags (3-5 max)
This will be published as a LinkedIn Article, so make it substantive and valuable.
Write in English only.""",

        "x": f"""You are writing an X/Twitter thread starter in English about {tema_central} {industria_context}.
Write a tweet/com thread starter (100-200 words) with:
- Attention-grabbing hook
- Key insight or value
- End with "🧵" or "Read more 👇" to point to the blog link
The image will be attached separately. This text should make people want to click.
Write in English only.""",

        "reddit": f"""You are writing a Reddit post in English about {tema_central} {industria_context}.
Write a value-driven post (200-400 words) with:
- Attractive title with [Guide 2026]
- Genuine, honest content
- Include real failures/lessons learned
- Helpful for the community
- Genuine question at the end
Write in English only."""
    }
    
    prompt = prompts.get(plataforma, prompts["linkedin"])
    
    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": "You are a professional writer. You write ONLY in English. Never write in Spanish."},
            {"role": "user", "content": prompt}
        ],
        model="llama-3.3-70b-versatile",
        temperature=0.7,
        max_tokens=4000
    )
    
    contenido = chat_completion.choices[0].message.content
    contenido = re.sub(r'<think>[\s\S]*?', '', contenido).strip()
    
    return {
        "tema": tema_central,
        "plataforma": plataforma,
        "tipo": tipo_post,
        "industria": industria,
        "contenido": contenido,
        "fecha": datetime.now().isoformat()
    }


def generar_serie(tema_central: str, tipo_post: str = "general", industria: str = None) -> dict:
    """Genera una serie optimizada: Blog + LinkedIn (article) + X (thread intro + link) + Reddit (sin imagen)"""
    
    resultados = {}
    imagen_url = None
    
    print("  📝 Generando Blog...")
    resultados["blog"] = generar_post(tema_central, "blog", tipo_post, industria)
    
    print("  📱 Generando LinkedIn Article...")
    resultados["linkedin"] = generar_post(tema_central, "linkedin", tipo_post, industria)
    
    print("  🐦 Generando X thread starter...")
    resultados["x"] = generar_post(tema_central, "x", tipo_post, industria)
    
    print("  🤖 Generando Reddit...")
    resultados["reddit"] = generar_post(tema_central, "reddit", tipo_post, industria)
    
    return resultados


def guardar_serie(resultados: dict, tipo_post: str, industria: str = None) -> dict:
    """Guarda la serie completa en la base de datos"""
    from db.database import guardar_post, actualizar_imagen
    from image_generator_hf import generar_imagen, generar_prompt_imagen, guardar_imagen_local
    
    posts_guardados = {}
    imagen_url = None
    
    for plataforma in ["blog", "linkedin", "x", "reddit"]:
        contenido = resultados[plataforma]["contenido"]
        titulo = contenido.split('\n')[0][:500]
        
        post_id = guardar_post(
            titulo=titulo,
            plataforma=plataforma,
            tipo=tipo_post,
            contenido=contenido,
            industria=industria
        )
        
        # Generar imagen UNA SOLA VEZ para blog/linkedin/x
        if plataforma in PLATAFORMAS_CON_IMAGEN and not imagen_url:
            print(f"  🖼️ Generando imagen...")
            try:
                prompt = generar_prompt_imagen(tipo_post, industria, plataforma)
                img_result = generar_imagen(prompt)
                
                if "error" not in img_result:
                    filename = f"imagen_blog_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    filepath = guardar_imagen_local(img_result["imagen_bytes"], filename)
                    imagen_url = filepath
                    print(f"    ✅ Imagen: {filepath}")
            except Exception as e:
                print(f"    ❌ Error: {e}")
        
        # Asignar imagen a blog, linkedin y x
        if plataforma in PLATAFORMAS_CON_IMAGEN and imagen_url:
            actualizar_imagen(post_id, imagen_url)
        
        posts_guardados[plataforma] = {
            "id": post_id,
            "plataforma": plataforma,
            "titulo": titulo[:80],
            "imagen_url": imagen_url if plataforma in PLATAFORMAS_CON_IMAGEN else None
        }
    
    return posts_guardados