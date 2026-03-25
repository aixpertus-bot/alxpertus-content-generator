import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def generar_imagen(prompt: str, tamano: str = "1024x1024") -> dict:
    """Genera imagen con DALL-E 3"""
    
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        return {"error": "OPENAI_API_KEY no configurada en .env"}
    
    headers = {
        "Authorization": f"Bearer {openai_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "dall-e-3",
        "prompt": prompt,
        "size": tamano,
        "quality": "standard",
        "n": 1
    }
    
    try:
        response = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            return {
                "url": data['data'][0]['url'],
                "revised_prompt": data['data'][0].get('revised_prompt'),
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {"error": f"API Error: {response.status_code} - {response.text}"}
    
    except Exception as e:
        return {"error": str(e)}

def generar_prompt_imagen(tipo_post: str, industria: str = None, plataforma: str = "linkedin") -> str:
    """Genera prompt optimizado para cada tipo de post"""
    
    prompts = {
        "general": "Minimalist modern illustration showing AI agents working together in a coordinated team, digital brain network, blue and white color palette, clean professional style, suitable for LinkedIn article cover",
        
        "industria": f"Professional illustration showing AI agents specialized for {industria} industry working together, modern tech aesthetic, clean corporate style, LinkedIn article cover image",
        
        "tendencia": "Futuristic 2026 technology concept, AI agents and automation, modern minimal style, blue gradient, professional LinkedIn cover",
        
        "practico": "Step-by-step technical illustration showing how to set up AI agents, clean diagram style, professional blue tones, LinkedIn article cover"
    }
    
    return prompts.get(tipo_post, prompts["general"])

if __name__ == "__main__":
    print("🖼️ Generador de imágenes DALL-E para Alxpertus\n")
    
    tipo = input("Tipo de post (general/industria/tendencia/practico): ").strip()
    industria = input("Industria (opcional): ").strip()
    
    prompt = generar_prompt_imagen(tipo, industria)
    print(f"\nPrompt: {prompt}\n")
    
    print("Generando imagen...")
    resultado = generar_imagen(prompt)
    
    if "error" in resultado:
        print(f"❌ Error: {resultado['error']}")
    else:
        print(f"✅ Imagen generada!")
        print(f"URL: {resultado['url']}")
        print(f"Revised prompt: {resultado['revised_prompt']}")