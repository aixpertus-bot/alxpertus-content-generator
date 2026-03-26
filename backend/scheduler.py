import schedule
import time
import threading
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

class PublicadorAutomatico:
    """Gestor de publicación automática de posts"""
    
    def __init__(self):
        self.ejecutando = False
        self.hilo = None
    
    def publicar_post_programado(self):
        """Publica todos los posts que están programados para ahora"""
        from db.database import obtener_posts_por_publicar, obtener_post_por_id
        from publish import publicar_post
        
        print(f"\n⏰ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Verificando posts programados...")
        
        posts = obtener_posts_por_publicar()
        
        if not posts:
            print("  No hay posts pendientes para publicar")
            return
        
        print(f"  Encontrados {len(posts)} posts para publicar")
        
        for post in posts:
            try:
                print(f"  📤 Publicando post #{post.id} ({post.plataforma})...")
                
                # Generar imagen si no existe
                if not post.imagen_generada:
                    print(f"    🖼️ Generando imagen...")
                    from image_generator_hf import generar_imagen, generar_prompt_imagen, guardar_imagen_local
                    
                    prompt = generar_prompt_imagen(post.tipo, post.industria, post.plataforma)
                    resultado = generar_imagen(prompt)
                    
                    if "error" not in resultado:
                        filename = f"imagen_post_{post.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                        filepath = guardar_imagen_local(resultado["imagen_bytes"], filename)
                        
                        from db.database import actualizar_imagen
                        actualizar_imagen(post.id, filepath)
                        print(f"    ✅ Imagen guardada: {filepath}")
                    else:
                        print(f"    ⚠️ Error generando imagen: {resultado.get('error')}")
                
                # Publicar
                resultado = publicar_post(post.id)
                
                if resultado.get("success"):
                    print(f"    ✅ Post publicado: {resultado.get('url')}")
                else:
                    print(f"    ❌ Error: {resultado.get('error')}")
                    
            except Exception as e:
                print(f"    ❌ Error inesperado: {str(e)}")
    
    def generar_posts_serie(self):
        """Genera una serie de posts para todas las plataformas"""
        from generator_en import generar_post, TEMA_CENTRAL
        from db.database import guardar_post
        
        print(f"\n🔄 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Generando serie completa...")
        
        plataformas = ["linkedin", "x", "reddit"]
        tipo = "general"  # Por defecto
        
        for plat in plataformas:
            try:
                print(f"  📝 Generando post para {plat.upper()}...")
                
                resultado = generar_post(
                    tema_central=TEMA_CENTRAL,
                    plataforma=plat,
                    tipo_post=tipo
                )
                
                titulo = resultado['contenido'].split('\n')[0][:500]
                
                post_id = guardar_post(
                    titulo=titulo,
                    plataforma=plat,
                    tipo=tipo,
                    contenido=resultado['contenido']
                )
                
                print(f"    ✅ Post #{post_id} guardado para {plat}")
                
                # Generar imagen automáticamente
                from image_generator_hf import generar_imagen, generar_prompt_imagen, guardar_imagen_local
                
                prompt = generar_prompt_imagen(tipo, None, plat)
                img_resultado = generar_imagen(prompt)
                
                if "error" not in img_resultado:
                    filename = f"imagen_post_{post_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    filepath = guardar_imagen_local(img_resultado["imagen_bytes"], filename)
                    
                    from db.database import actualizar_imagen
                    actualizar_imagen(post_id, filepath)
                    print(f"    🖼️ Imagen generada: {filepath}")
                
            except Exception as e:
                print(f"    ❌ Error: {str(e)}")
        
        print("  ✅ Serie completa generada")
    
    def actualizar_metricas_todos(self):
        """Actualiza las métricas de todos los posts publicados"""
        from db.database import obtener_posts_publicados
        from publish import actualizar_metricas_post
        
        print(f"\n📊 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Actualizando métricas...")
        
        posts = obtener_posts_publicados(limite=50)
        
        if not posts:
            print("  No hay posts publicados para actualizar")
            return
        
        print(f"  Actualizando {len(posts)} posts...")
        
        for post in posts:
            try:
                resultado = actualizar_metricas_post(post.id)
                if resultado.get("success"):
                    print(f"    ✅ Post #{post.id} actualizado")
                else:
                    print(f"    ⚠️ Post #{post.id}: {resultado.get('error', 'Error')}")
            except Exception as e:
                print(f"    ❌ Error con post #{post.id}: {str(e)}")
        
        print("  ✅ Métricas actualizadas")
    
    def iniciar(self):
        """Inicia el programador de publicaciones"""
        if self.ejecutando:
            print("⚠️ El programador ya está ejecutándose")
            return
        
        print("🚀 Iniciando programador de publicaciones...")
        
        # Programar tareas
        # Revisar cada 15 minutos si hay posts para publicar
        schedule.every(15).minutes.do(self.publicar_post_programado)
        
        # Generar serie diaria a las 8:00 AM
        schedule.every().day.at("08:00").do(self.generar_posts_serie)
        
        # Actualizar métricas cada hora
        schedule.every(1).hours.do(self.actualizar_metricas_todos)
        
        # También publicar inmediatamente al iniciar
        self.publicar_post_programado()
        
        self.ejecutando = True
        
        # Iniciar hilo separado
        self.hilo = threading.Thread(target=self._ejecutar_loop, daemon=True)
        self.hilo.start()
        
        print("✅ Programador iniciado")
        print("   - Revisión de posts programados: cada 15 minutos")
        print("   - Generación de serie diaria: 8:00 AM")
        print("   - Actualización de métricas: cada hora")
    
    def _ejecutar_loop(self):
        """Ejecuta el loop del programador"""
        while self.ejecutando:
            schedule.run_pending()
            time.sleep(60)  # Verificar cada minuto
    
    def detener(self):
        """Detiene el programador"""
        self.ejecutando = False
        schedule.clear()
        print("⏹️ Programador detenido")
    
    def estado(self):
        """Retorna el estado del programador"""
        return {
            "ejecutando": self.ejecutando,
            "proximos_jobs": [
                {"job": str(job), "proximo": job.next_run}
                for job in schedule.get_jobs()
            ]
        }


# Instancia global
scheduler = PublicadorAutomatico()


def iniciar_scheduler():
    """Función de conveniencia para iniciar el scheduler"""
    scheduler.iniciar()


def detener_scheduler():
    """Función de conveniencia para detener el scheduler"""
    scheduler.detener()


if __name__ == "__main__":
    print("⏰ Alxpertus Content Scheduler")
    print("=" * 40)
    
    print("\n1. Iniciar scheduler")
    print("2. Detener scheduler")
    print("3. Ver estado")
    print("4. Publicar ahora")
    print("5. Generar serie ahora")
    print("6. Actualizar métricas")
    print("7. Salir")
    
    opcion = input("\nSelecciona opción: ").strip()
    
    if opcion == "1":
        iniciar_scheduler()
    elif opcion == "2":
        detener_scheduler()
    elif opcion == "3":
        estado = scheduler.estado()
        print(f"Ejecutando: {estado['ejecutando']}")
        print("Próximos jobs:")
        for job in estado['proximos_jobs']:
            print(f"  - {job['job']}: {job['proximo']}")
    elif opcion == "4":
        scheduler.publicar_post_programado()
    elif opcion == "5":
        scheduler.generar_posts_serie()
    elif opcion == "6":
        scheduler.actualizar_metricas_todos()