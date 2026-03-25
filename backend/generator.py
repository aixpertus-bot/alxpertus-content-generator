import os
import json
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

TEMA_CENTRAL = "Equipos de Agentes IA: Tu Nueva Fuerza de Trabajo Digital en 2026"

TONO = """Eres el experto en IA de Alxpertus (Intelligent Solutions & Advanced Consulting).
Tono: consultor senior, autoritario pero accesible, profesional, con visión 2026.
Nunca hagas venta dura. Enfócate en valor educativo.
Usa datos reales 2026: multi-agent systems, +40% eficiencia, plug-and-play, CrewAI/LangGraph, etc.
Incluye siempre referencia sutil a que existen kits plug-and-play de 6 agentes por industria (sin link directo)."""

PLATAFORMAS = {
    "linkedin": {
        "formato": "post largo (500-900 palabras), educativo, preguntas para engagement, hashtags al final",
        "ejemplo": "Título: Equipos de 6 Agentes IA: Por qué en 2026 las pymes ya no contratan empleados… contratan sistemas"
    },
    "x": {
        "formato": "hilo de 6-10 tweets punchy, numerados, hashtags estratégicos",
        "ejemplo": "Tweet 1/6 → Tweet 10/6"
    },
    "reddit": {
        "formato": "post de valor + discusión, título atractivo con [Guía 2026], sin link directo en el primer post",
        "ejemplo": "r/GrowMyBusinessNow"
    }
}

TIPOS_POST = {
    "general": "Introducción a multi-agentes y su impacto en negocios",
    "industria": "Ejemplo específico por industria (Freelancers, E-commerce, Real Estate, Coaches)",
    "tendencia": "Novedades 2026, casos reales, comparativas",
    "practico": "Cómo montar tu primer equipo de 6 agentes sin código"
}

def generar_post(tema_central: str, plataforma: str, tipo_post: str, industria: str = None) -> dict:
    
    industria_context = f"Industria específica: {industria}" if industria else ""
    
    prompt = f"""{TONO}

Tema central: {tema_central}
Tipo de post: {TIPOS_POST[tipo_post]}
{industria_context}

Plataforma: {plataforma.upper()}
Formato requerido: {PLATAFORMAS[plataforma]['formato']}

Genera SOLO el contenido listo para copiar y pegar.
Para LinkedIn: título + cuerpo + hashtags
Para X: hilo completo numerado (1/6, 2/6, etc.)
Para Reddit: título + cuerpo completo

Fecha de generación: {datetime.now().strftime('%Y-%m-%d')}
"""
    
    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.3-70b-versatile",
        temperature=0.7,
        max_tokens=4000
    )
    
    contenido = chat_completion.choices[0].message.content
    
    return {
        "tema": tema_central,
        "plataforma": plataforma,
        "tipo": tipo_post,
        "industria": industria,
        "contenido": contenido,
        "fecha": datetime.now().isoformat()
    }

def generar_serie_completa(tema_central: str, industria: str = None) -> dict:
    """Genera posts para todas las plataformas y tipos"""
    resultados = {}
    
    for plataforma in ["linkedin", "x", "reddit"]:
        resultados[plataforma] = {}
        for tipo in ["general", "industria", "tendencia", "practico"]:
            try:
                resultados[plataforma][tipo] = generar_post(
                    tema_central=tema_central,
                    plataforma=plataforma,
                    tipo_post=tipo,
                    industria=industria
                )
            except Exception as e:
                resultados[plataforma][tipo] = {"error": str(e)}
    
    return resultados

def guardar_json(data: dict, filename: str = None):
    if not filename:
        filename = f"posts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return filename

if __name__ == "__main__":
    print(f"📌 Tema central: {TEMA_CENTRAL}\n")
    print("="*60)
    
    industria = input("Industria (Enter para tema general): ").strip()
    industria = industria if industria else None
    
    print("\n🎯 Generando serie completa...\n")
    
    resultados = generar_serie_completa(TEMA_CENTRAL, industria)
    
    for plataforma, tipos in resultados.items():
        print(f"\n=== {plataforma.upper()} ===")
        for tipo, data in tipos.items():
            if "error" in data:
                print(f"  {tipo}: ERROR - {data['error']}")
            else:
                print(f"\n--- {tipo.upper()} ---")
                print(data['contenido'][:500] + "..." if len(data['contenido']) > 500 else data['contenido'])
        
        print("\n" + "="*60)
    
    guardar_json(resultados)
    print("\n✅ Serie completa guardada en JSON")