from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import sys
import os
import threading

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generator_en import generar_post, TEMA_CENTRAL
from db.database import (
    guardar_post, obtener_posts, obtener_post_por_id, obtener_estadisticas,
    actualizar_enlace, actualizar_imagen, programar_post, obtener_posts_programados,
    marcar_publicado, obtener_posts_publicados
)
from image_generator_hf import generar_imagen, generar_prompt_imagen, guardar_imagen_local
from publish import publicar_post, actualizar_metricas_post
from scheduler import scheduler, iniciar_scheduler, detener_scheduler

app = FastAPI(title="Alxpertus Content Generator API", version="2.0.0")

# Mount static files for images
os.makedirs("static/images", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

class PostRequest(BaseModel):
    plataforma: str
    tipo: str
    industria: Optional[str] = None

class PostWithImageRequest(BaseModel):
    plataforma: str
    tipo: str
    industria: Optional[str] = None
    generar_imagen: bool = True

class PostResponse(BaseModel):
    id: int
    titulo: str
    plataforma: str
    tipo: str
    industria: Optional[str]
    fecha_creacion: str
    imagen_url: Optional[str] = None
    estado: str = "borrador"

class StatsResponse(BaseModel):
    total: int
    por_plataforma: dict
    por_tipo: dict

@app.get("/")
def root():
    return {
        "message": "Alxpertus Content API v2.0",
        "tema_central": TEMA_CENTRAL,
        "scheduler": scheduler.ejecutando
    }

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "scheduler_activo": scheduler.ejecutando,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/generar", response_model=PostResponse)
def generar(request: PostRequest):
    """Genera un post sin imagen"""
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
        
        return PostResponse(
            id=post_id,
            titulo=titulo,
            plataforma=request.plataforma,
            tipo=request.tipo,
            industria=request.industria,
            fecha_creacion=datetime.now().isoformat(),
            estado="borrador"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generar-y-guardar")
def generar_y_guardar(request: PostWithImageRequest):
    """Genera un post y opcionalmente genera la imagen automáticamente"""
    try:
        # Generar contenido
        result = generar_post(
            tema_central=TEMA_CENTRAL,
            plataforma=request.plataforma,
            tipo_post=request.tipo,
            industria=request.industria
        )
        
        titulo = result['contenido'].split('\n')[0][:500]
        
        # Guardar post
        post_id = guardar_post(
            titulo=titulo,
            plataforma=request.plataforma,
            tipo=request.tipo,
            contenido=result['contenido'],
            industria=request.industria
        )
        
        imagen_url = None
        
        # Generar imagen automáticamente si se solicita
        if request.generar_imagen:
            try:
                prompt = generar_prompt_imagen(request.tipo, request.industria, request.plataforma)
                img_result = generar_imagen(prompt)
                
                if "error" not in img_result:
                    filename = f"imagen_post_{post_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    filepath = guardar_imagen_local(img_result["imagen_bytes"], filename)
                    actualizar_imagen(post_id, filepath)
                    imagen_url = filepath
            except Exception as img_error:
                print(f"Error generando imagen: {img_error}")
        
        return {
            "id": post_id,
            "contenido": result['contenido'],
            "plataforma": request.plataforma,
            "tipo": request.tipo,
            "imagen_url": imagen_url,
            "imagen_generada": imagen_url is not None
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generar-serie")
def generar_serie_optimizada(tipo: str = "general", industria: Optional[str] = None):
    """Genera serie optimizada: Blog + LinkedIn + X (misma imagen) + Reddit (sin imagen)"""
    try:
        from generator_en import generar_serie, guardar_serie
        
        # Generar contenidos
        print("🔄 Generando serie optimizada...")
        resultados = generar_serie(TEMA_CENTRAL, tipo, industria)
        
        # Guardar en base de datos con UNA imagen
        posts_guardados = guardar_serie(resultados, tipo, industria)
        
        # Obtener imagen de uno de los posts con imagen
        imagen_url = None
        for plat in ["blog", "linkedin", "x"]:
            if posts_guardados[plat].get("imagen_url"):
                imagen_url = posts_guardados[plat]["imagen_url"]
                break
        
        return {
            "message": "Serie optimizada generada (Blog + LinkedIn + X con misma imagen + Reddit sin imagen)",
            "posts": posts_guardados,
            "imagen_compartida": imagen_url
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/posts", response_model=List[PostResponse])
def list_posts(plataforma: Optional[str] = None, limite: int = 50, estado: Optional[str] = None):
    posts = obtener_posts(filtro_plataforma=plataforma, limite=limite)
    
    if estado:
        posts = [p for p in posts if p.estado == estado]
    
    return [
        PostResponse(
            id=p.id,
            titulo=p.titulo,
            plataforma=p.plataforma,
            tipo=p.tipo,
            industria=p.industria,
            fecha_creacion=p.fecha_creacion.isoformat(),
            imagen_url=p.imagen_url,
            estado=p.estado
        )
        for p in posts
    ]

@app.get("/posts/{post_id}")
def get_post(post_id: int):
    post = obtener_post_por_id(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post no encontrado")
    
    return {
        "id": post.id,
        "titulo": post.titulo,
        "plataforma": post.plataforma,
        "tipo": post.tipo,
        "industria": post.industria,
        "contenido": post.contenido,
        "imagen_url": post.imagen_url,
        "imagen_generada": post.imagen_generada,
        "enlace": post.enlace,
        "fecha_programada": post.fecha_programada.isoformat() if post.fecha_programada else None,
        "fecha_publicacion": post.fecha_publicacion.isoformat() if post.fecha_publicacion else None,
        "estado": post.estado,
        "fecha_creacion": post.fecha_creacion.isoformat(),
        "visualizaciones": post.visualizaciones,
        "likes": post.likes,
        "comentarios": post.comentarios,
        "shares": post.shares,
        "engagement_rate": post.engagement_rate
    }

@app.get("/posts/publicados")
def get_published_posts(limite: int = 50):
    posts = obtener_posts_publicados(limite)
    return [
        {
            "id": p.id,
            "titulo": p.titulo,
            "plataforma": p.plataforma,
            "enlace": p.enlace,
            "fecha_publicacion": p.fecha_publicacion.isoformat() if p.fecha_publicacion else None,
            "visualizaciones": p.visualizaciones,
            "likes": p.likes,
            "comentarios": p.comentarios,
            "shares": p.shares,
            "engagement_rate": p.engagement_rate
        }
        for p in posts
    ]

@app.post("/posts/{post_id}/publicar")
def publish_post(post_id: int):
    """Publica un post en la plataforma correspondiente"""
    try:
        resultado = publicar_post(post_id)
        
        if resultado.get("success"):
            return {
                "success": True,
                "message": "Post publicado exitosamente",
                "platform": resultado.get("platform"),
                "url": resultado.get("url"),
                "post_id": resultado.get("post_id")
            }
        else:
            raise HTTPException(status_code=500, detail=resultado.get("error", "Error desconocido"))
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/posts/{post_id}/imagen")
def generate_image(post_id: int):
    """Genera una imagen para el post"""
    try:
        post = obtener_post_por_id(post_id)
        if not post:
            raise HTTPException(status_code=404, detail="Post no encontrado")
        
        prompt = generar_prompt_imagen(post.tipo, post.industria, post.plataforma)
        result = generar_imagen(prompt)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        # Save image
        filename = f"imagen_post_{post_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = guardar_imagen_local(result["imagen_bytes"], filename)
        actualizar_imagen(post_id, filepath)
        
        return {
            "post_id": post_id,
            "imagen_url": filepath,
            "prompt_usado": prompt,
            "message": "Imagen generada exitosamente"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/posts/{post_id}/actualizar-metricas")
def update_post_metrics(post_id: int):
    """Actualiza las métricas de un post publicado"""
    try:
        resultado = actualizar_metricas_post(post_id)
        
        if resultado.get("success"):
            return {
                "success": True,
                "metricas": resultado.get("metricas")
            }
        else:
            return {
                "success": False,
                "error": resultado.get("error", "Error desconocido")
            }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.put("/posts/{post_id}/enlace")
def set_enlace(post_id: int, enlace: str):
    actualizar_enlace(post_id, enlace)
    return {"message": "Enlace actualizado", "post_id": post_id}

class ScheduleRequest(BaseModel):
    fecha_programada: str

@app.post("/posts/{post_id}/programar")
def schedule_post(post_id: int, request: ScheduleRequest):
    """Programa un post para publicación automática"""
    try:
        fecha = datetime.fromisoformat(request.fecha_programada)
        
        if fecha <= datetime.now():
            raise HTTPException(status_code=400, detail="La fecha debe ser futura")
        
        programar_post(post_id, fecha)
        
        return {
            "message": "Post programado",
            "post_id": post_id,
            "fecha_programada": fecha.isoformat(),
            "fecha_legible": fecha.strftime("%Y-%m-%d %H:%M")
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Usa ISO format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/posts/programados")
def list_scheduled_posts():
    posts = obtener_posts_programados()
    return [
        {
            "id": p.id,
            "titulo": p.titulo,
            "plataforma": p.plataforma,
            "tipo": p.tipo,
            "industria": p.industria,
            "imagen_url": p.imagen_url,
            "contenido_preview": p.contenido[:200] + "..." if len(p.contenido) > 200 else p.contenido,
            "fecha_programada": p.fecha_programada.isoformat() if p.fecha_programada else None,
            "fecha_programada_legible": p.fecha_programada.strftime("%Y-%m-%d %H:%M") if p.fecha_programada else None,
            "estado": p.estado
        }
        for p in posts
    ]

@app.get("/stats")
def stats():
    return obtener_estadisticas()

@app.get("/stats/detallado")
def stats_detailed():
    """Estadísticas detalladas incluyendo métricas de engagement"""
    stats = obtener_estadisticas()
    
    # Agregar stats de posts publicados
    posts_publicados = obtener_posts_publicados(limite=1000)
    
    if posts_publicados:
        avg_engagement = sum(p.engagement_rate for p in posts_publicados) / len(posts_publicados)
        total_alcance = sum(p.alcance for p in posts_publicados)
        
        stats["engagement"] = {
            "posts_publicados": len(posts_publicados),
            "engagement_promedio": round(avg_engagement, 2),
            "alcance_total": total_alcance,
            "visualizaciones_totales": sum(p.visualizaciones for p in posts_publicados),
            "likes_totales": sum(p.likes for p in posts_publicados),
            "comentarios_totales": sum(p.comentarios for p in posts_publicados),
            "shares_totales": sum(p.shares for p in posts_publicados)
        }
    
    return stats

# === ENDPOINTS DEL SCHEDULER ===

@app.get("/scheduler/estado")
def scheduler_status():
    """Retorna el estado del scheduler"""
    return scheduler.estado()

@app.post("/scheduler/iniciar")
def start_scheduler():
    """Inicia el programador automático"""
    if not scheduler.ejecutando:
        iniciar_scheduler()
        return {"message": "Scheduler iniciado", "ejecutando": True}
    return {"message": "Scheduler ya está ejecutándose", "ejecutando": True}

@app.post("/scheduler/detener")
def stop_scheduler():
    """Detiene el programador automático"""
    if scheduler.ejecutando:
        detener_scheduler()
        return {"message": "Scheduler detenido", "ejecutando": False}
    return {"message": "Scheduler no está ejecutándose", "ejecutando": False}

@app.post("/scheduler/publicar-ahora")
def publish_now():
    """Fuerza la publicación de posts programados"""
    scheduler.publicar_post_programado()
    return {"message": "Publicación iniciada"}

@app.post("/scheduler/generar-serie")
def generate_series_now():
    """Fuerza la generación de una serie completa"""
    scheduler.generar_posts_serie()
    return {"message": "Generación de serie iniciada"}

@app.post("/scheduler/actualizar-metricas")
def update_metrics_now():
    """Fuerza la actualización de métricas"""
    scheduler.actualizar_metricas_todos()
    return {"message": "Actualización de métricas iniciada"}

if __name__ == "__main__":
    import uvicorn
    
    # Iniciar scheduler automáticamente
    print("🚀 Iniciando scheduler...")
    iniciar_scheduler()
    
    # Iniciar servidor
    print("🚀 Iniciando servidor API...")
    uvicorn.run(app, host="0.0.0.0", port=8000)