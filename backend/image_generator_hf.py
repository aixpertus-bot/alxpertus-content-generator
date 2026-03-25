import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

HF_API_URL = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-dev"
HF_API_KEY = os.getenv("HUGGING_FACE_TOKEN")

def generar_imagen(prompt: str, tamano: str = "1024x1024") -> dict:
    """Genera imagen con FLUX via Hugging Face"""
    
    if not HF_API_KEY:
        return {"error": "HUGGING_FACE_TOKEN no configurado en .env"}
    
    headers = {
        "Authorization": f"Bearer {HF_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "inputs": prompt,
        "parameters": {
            "width": 1024,
            "height": 1024,
            "num_inference_steps": 25,
            "guidance_scale": 3.5
        }
    }
    
    try:
        response = requests.post(
            HF_API_URL,
            headers=headers,
            json=payload,
            timeout=120
        )
        
        if response.status_code == 200:
            return {
                "imagen_bytes": response.content,
                "prompt": prompt,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {"error": f"API Error: {response.status_code} - {response.text[:200]}"}
    
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
    print("🖼️ Generador de imágenes FLUX para Alxpertus\n")
    
    prompt = input("Prompt: ").strip()
    
    print("Generando imagen...")
    resultado = generar_imagen(prompt)
    
    if "error" in resultado:
        print(f"❌ Error: {resultado['error']}")
    else:
        filename = f"imagen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        with open(filename, "wb") as f:
            f.write(resultado['imagen_bytes'])
        print(f"✅ Imagen guardada: {filename}")