from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generator import generar_post, TEMA_CENTRAL
from db.database import guardar_post, obtener_posts, obtener_estadisticas, actualizar_enlace, actualizar_imagen, programar_post, obtener_posts_programados, marcar_publicado
from image_generator import generar_imagen, generar_prompt_imagen

app = FastAPI(title="Alxpertus Content Generator API", version="1.0.0")

class PostRequest(BaseModel):
    plataforma: str
    tipo: str
    industria: Optional[str] = None

class PostResponse(BaseModel):
    id: int
    titulo: str
    plataforma: str
    tipo: str
    industria: Optional[str]
    fecha_creacion: str

class StatsResponse(BaseModel):
    total: int
    por_plataforma: dict
    por_tipo: dict

@app.get("/")
def root():
    return {"message": "Alxpertus Content API", "tema_central": TEMA_CENTRAL}

@app.post("/generar")
def generar(request: PostRequest):
    try:
        result = generar_post(
            tema_central=TEMA_CENTRAL,
            plataforma=request.plataforma,
            tipo_post=request.tipo,
            industria=request.industria
        )
        
        titulo = result['contenido'].split('\n')[0][:500]
        
        post_id = guardar_post(
            titulo=titulo,
            plataforma=request.plataforma,
            tipo=request.tipo,
            contenido=result['contenido'],
            industria=request.industria
        )
        
        return {
            "id": post_id,
            "contenido": result['contenido'],
            "plataforma": request.plataforma,
            "tipo": request.tipo
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/posts", response_model=List[PostResponse])
def list_posts(plataforma: Optional[str] = None, limite: int = 50):
    posts = obtener_posts(filtro_plataforma=plataforma, limite=limite)
    return [
        PostResponse(
            id=p.id,
            titulo=p.titulo,
            plataforma=p.plataforma,
            tipo=p.tipo,
            industria=p.industria,
            fecha_creacion=p.fecha_creacion.isoformat()
        )
        for p in posts
    ]

@app.get("/posts/{post_id}")
def get_post(post_id: int):
    posts = obtener_posts(limite=1000)
    for p in posts:
        if p.id == post_id:
            return {
                "id": p.id,
                "titulo": p.titulo,
                "plataforma": p.plataforma,
                "tipo": p.tipo,
                "industria": p.industria,
                "contenido": p.contenido,
                "imagen_url": p.imagen_url,
                "enlace": p.enlace,
                "fecha_programada": p.fecha_programada.isoformat() if p.fecha_programada else None,
                "estado": p.estado,
                "fecha_creacion": p.fecha_creacion.isoformat()
            }
    raise HTTPException(status_code=404, detail="Post no encontrado")

@app.put("/posts/{post_id}/enlace")
def set_enlace(post_id: int, enlace: str):
    actualizar_enlace(post_id, enlace)
    return {"message": "Enlace actualizado", "post_id": post_id}

@app.get("/stats", response_model=StatsResponse)
def stats():
    return obtener_estadisticas()

@app.post("/posts/{post_id}/imagen")
def generate_image(post_id: int):
    try:
        posts = obtener_posts(limite=1000)
        post = None
        for p in posts:
            if p.id == post_id:
                post = p
                break
        
        if not post:
            raise HTTPException(status_code=404, detail="Post no encontrado")
        
        prompt = generar_prompt_imagen(post.tipo, post.industria, post.plataforma)
        result = generar_imagen(prompt)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        actualizar_imagen(post_id, result["url"])
        
        return {
            "post_id": post_id,
            "imagen_url": result["url"],
            "prompt_usado": prompt,
            "revised_prompt": result.get("revised_prompt")
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ScheduleRequest(BaseModel):
    fecha_programada: str

@app.post("/posts/{post_id}/programar")
def schedule_post(post_id: int, request: ScheduleRequest):
    try:
        fecha = datetime.fromisoformat(request.fecha_programada)
        programar_post(post_id, fecha)
        return {"message": "Post programado", "post_id": post_id, "fecha_programada": fecha.isoformat()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Fecha inválida: {str(e)}")

@app.get("/posts/programados")
def list_scheduled_posts():
    posts = obtener_posts_programados()
    return [
        {
            "id": p.id,
            "titulo": p.titulo,
            "plataforma": p.plataforma,
            "tipo": p.tipo,
            "fecha_programada": p.fecha_programada.isoformat() if p.fecha_programada else None,
            "estado": p.estado
        }
        for p in posts
    ]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)