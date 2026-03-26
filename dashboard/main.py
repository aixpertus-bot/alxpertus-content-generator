import streamlit as st
import requests
import json
import os
from datetime import datetime

API_URL = os.environ.get("API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Alxpertus Content Generator", 
    page_icon="🤖", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #3b82f6 0%, #8b5cf6 100%);
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .publish-box {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 2px solid #3b82f6;
        border-radius: 12px;
        padding: 20px;
        margin: 20px 0;
    }
    .metric-card {
        background: #1e293b;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
    }
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .borrador { background: #f59e0b; color: white; }
    .programado { background: #3b82f6; color: white; }
    .publicado { background: #10b981; color: white; }
    .error { background: #ef4444; color: white; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <h1 style="color: white; margin: 0;">🤖 Alxpertus Content Generator</h1>
    <p style="color: #e2e8f0; margin: 5px 0 0 0;">AI-Powered Automated Content Publishing for LinkedIn, X & Reddit</p>
</div>
""", unsafe_allow_html=True)

# Check scheduler status
try:
    scheduler_status = requests.get(f"{API_URL}/scheduler/estado", timeout=5).json()
    scheduler_activo = scheduler_status.get("ejecutando", False)
except:
    scheduler_activo = False

# Sidebar with scheduler control
with st.sidebar:
    st.header("⏰ Auto-Publisher")
    
    if scheduler_activo:
        st.success("🟢 Scheduler ACTIVO")
        st.info("Posts se publican automáticamente según programación")
    else:
        st.warning("🔴 Scheduler INACTIVO")
    
    if st.button("▶️ Iniciar Scheduler" if not scheduler_activo else "⏹️ Detener Scheduler"):
        try:
            endpoint = "/scheduler/detener" if scheduler_activo else "/scheduler/iniciar"
            requests.post(f"{API_URL}{endpoint}", timeout=10)
            st.rerun()
        except:
            st.error("Error de conexión")
    
    st.divider()
    
    st.markdown("### 📊 Estado del Sistema")
    
    try:
        stats = requests.get(f"{API_URL}/stats/detallado", timeout=5).json()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Posts", stats.get("total", 0))
        with col2:
            st.metric("Published", stats.get("por_estado", {}).get("publicado", 0))
        with col3:
            st.metric("Total Views", 0)
        with col4:
            st.metric("Engagement Rate", "0%")
        
        # Detailed metrics
        if "engagement" in stats and isinstance(stats["engagement"], dict):
            st.markdown("### 📊 Detailed Metrics")
            st.divider()
            st.markdown("### 📈 Engagement")
            st.metric("Avg Engagement", f"{stats['engagement'].get('engagement_promedio', 0):.2f}%")
            st.metric("Total Views", stats['engagement'].get('visualizaciones_totales', 0))
    except:
        st.error("No se pudo conectar al servidor")

tabs = st.tabs(["🚀 Generate & Publish", "📄 Posts", "📅 Scheduled", "📊 Analytics"])

with tabs[0]:
    st.header("🚀 Generate & Auto-Publish")
    
    col1, col2 = st.columns(2)
    
    with col1:
        generar_todas = st.checkbox("🔄 Generate optimized series (Blog + LinkedIn + X with same image + Reddit without image)", value=False)
        
        plataforma = st.selectbox(
            "Platform", 
            ["blog", "linkedin", "x", "reddit"],
            format_func=lambda x: {
                "blog": "📝 Blog",
                "linkedin": "📱 LinkedIn",
                "x": "🐦 X/Twitter", 
                "reddit": "🤖 Reddit"
            }[x]
        ) if not generar_todas else "todas"
        
        tipo = st.selectbox(
            "Post type", 
            ["general", "industria", "tendencia", "practico"],
            format_func=lambda x: {
                "general": "📚 General",
                "industria": "🏭 Industry",
                "tendencia": "📈 Trend",
                "practico": "🛠️ Practical"
            }[x]
        )
    
    with col2:
        industria = st.text_input("Industry (optional)", placeholder="e.g., E-commerce, Real Estate")
        industria = industria if industria else None
        
        # Publicación automática
        publicacion_automatica = st.checkbox("⚡ Publicar automáticamente", value=True)
        
        if publicacion_automatica:
            programacion = st.selectbox(
                "Programación",
                ["ahora", "1h", "3h", "6h", "12h", "24h", "personalizado"],
                format_func=lambda x: {
                    "ahora": "Inmediatamente",
                    "1h": "En 1 hora",
                    "3h": "En 3 horas",
                    "6h": "En 6 horas",
                    "12h": "En 12 horas",
                    "24h": "Mañana a esta hora",
                    "personalizado": "Fecha personalizada"
                }[x]
            )
        else:
            programacion = None
    
    if st.button("🚀 Generate & Publish", type="primary", use_container_width=True):
        with st.spinner("Generando contenido y publicidad..."):
            try:
                if generar_todas:
                    # Generate series for all platforms
                    response = requests.post(
                        f"{API_URL}/generar-serie",
                        json={"tipo": tipo, "industria": industria},
                        timeout=60
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Handle both dict and list responses
                        if isinstance(data.get('posts'), dict):
                            posts_list = list(data['posts'].values())
                            st.success(f"✅ Serie optimizada generada: {len(posts_list)} posts!")
                            
                            for post in posts_list:
                                if post.get('imagen_url'):
                                    st.image(post['imagen_url'], width=150)
                        else:
                            posts_list = data.get('posts', [])
                            st.success(f"✅ Serie de {len(posts_list)} posts generada!")
                            
                            for post in posts_list:
                                if post.get('imagen_url'):
                                    st.image(post['imagen_url'], width=150)
                            if publicacion_automatica and post.get('imagen_url'):
                                # Auto publish
                                pub_response = requests.post(f"{API_URL}/posts/{post['id']}/publicar", timeout=30)
                                if pub_response.status_code == 200:
                                    st.success(f"✅ {post['plataforma'].upper()} publicado: {pub_response.json().get('url')}")
                                else:
                                    st.error(f"❌ Error publicando {post['plataforma']}")
                    else:
                        st.error(f"Error: {response.text}")
                else:
                    # Generate single post with image
                    response = requests.post(
                        f"{API_URL}/generar-y-guardar",
                        json={"plataforma": plataforma, "tipo": tipo, "industria": industria, "generar_imagen": True},
                        timeout=60
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        st.success(f"✅ Post generado (ID: {data['id']})")
                        
                        if data.get('imagen_url'):
                            st.image(data['imagen_url'], caption="Generated image", width=300)
                        
                        # Auto publish if enabled
                        if publicacion_automatica:
                            with st.spinner("Publicando en plataforma..."):
                                pub_response = requests.post(f"{API_URL}/posts/{data['id']}/publicar", timeout=30)
                                
                                if pub_response.status_code == 200:
                                    pub_data = pub_response.json()
                                    st.success(f"✅Publicado: {pub_data.get('url')}")
                                else:
                                    st.error(f"Error publicando: {pub_response.text}")
                    else:
                        st.error(f"Error: {response.text}")
                        
            except Exception as e:
                st.error(f"Error de conexión: {str(e)}")
                st.info("💡 Asegúrate de que el servidor esté corriendo: python3 start_full.py")

with tabs[1]:
    st.header("📄 All Posts")
    
    try:
        response = requests.get(f"{API_URL}/posts", params={"limite": 100}, timeout=10)
        posts = response.json()
        
        if not isinstance(posts, list):
            st.error(f"Error: Received {type(posts)} instead of list")
            posts = []
        
        if not posts:
            st.info("No posts yet. Generate one in the first tab!")
        else:
            # Filter
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                filtro_estado = st.selectbox("Filter by status", ["all", "borrador", "programado", "publicado", "error"])
            with col_f2:
                filtro_plat = st.selectbox("Filter by platform", ["all", "blog", "linkedin", "x", "reddit"])
            
            posts_filtrados = posts
            if filtro_estado != "all":
                posts_filtrados = [p for p in posts_filtrados if p.get("estado") == filtro_estado]
            if filtro_plat != "all":
                posts_filtrados = [p for p in posts_filtrados if p.get("plataforma") == filtro_plat]
            
            for post in posts_filtrados:
                estado_class = post.get("estado", "borrador")
                estado_label = {"borrador": "📝", "programado": "⏰", "publicado": "✅", "error": "❌"}.get(estado_class, "📝")
                
                # Mostrar preview directamente sin necesidad de botón
                with st.expander(f"{estado_label} #{post['id']} - {post['plataforma'].upper()} | {post['tipo']} | {post.get('estado', 'borrador')}"):
                    # Imagen (si existe)
                    if post.get('imagen_url'):
                        img_path = post['imagen_url']
                        if not img_path.startswith('http'):
                            img_path = f"http://localhost:8000/{img_path}"
                        st.image(img_path, caption=f"🖼️ Imagen compartida", use_container_width=True)
                    
                    # Título
                    st.markdown(f"### 📝 {post['titulo'][:150]}")
                    
                    if post.get('industria'):
                        st.markdown(f"**🏭 Industria:** {post['industria']}")
                    
                    st.markdown("---")
                    
                    # Preview del contenido (primeros 500 caracteres)
                    try:
                        detail_resp = requests.get(f"{API_URL}/posts/{post['id']}", timeout=10)
                        if detail_resp.status_code == 200:
                            full_post = detail_resp.json()
                            contenido_preview = full_post.get('contenido', '')[:800]
                            st.markdown("#### 📄 Preview del contenido:")
                            st.markdown(contenido_preview + "..." if len(full_post.get('contenido', '')) > 800 else contenido_preview)
                            
                            st.markdown("---")
                            
                            # Acciones
                            col_acc1, col_acc2, col_acc3 = st.columns(3)
                            
                            with col_acc1:
                                st.download_button(
                                    label="📋 Copiar contenido",
                                    data=full_post.get('contenido', ''),
                                    file_name=f"{post['plataforma']}_{post['id']}.txt",
                                    mime="text/plain",
                                    use_container_width=True
                                )
                            
                            with col_acc2:
                                if post.get('estado') == 'borrador':
                                    if st.button(f"📤 Publicar #{post['id']}", key=f"pub_{post['id']}"):
                                        try:
                                            r = requests.post(f"{API_URL}/posts/{post['id']}/publicar", timeout=30)
                                            if r.status_code == 200:
                                                st.success("Publicado!")
                                                st.rerun()
                                            else:
                                                st.error(f"Error: {r.text[:100]}")
                                        except Exception as e:
                                            st.error(f"Error: {e}")
                            
                            with col_acc3:
                                if post.get('enlace'):
                                    st.markdown(f"🔗 [Ver publicación]({post['enlace']})")
                    except Exception as e:
                        st.error(f"Error cargando contenido: {e}")
    except Exception as e:
        st.error(f"Error: {str(e)}")

with tabs[2]:
    st.header("📅 Scheduled Posts")
    
    try:
        response = requests.get(f"{API_URL}/posts/programados", timeout=10)
        posts = response.json()
        
        if not posts:
            st.info("No scheduled posts. Program one from the Posts tab!")
        else:
            for post in posts:
                with st.expander(f"#{post['id']} - {post['plataforma'].upper()} - {post.get('fecha_programada_legible', 'Sin fecha')}"):
                    st.markdown(f"**Titulo:** {post['titulo'][:80]}...")
                    st.markdown(f"**Tipo:** {post['tipo']}")
                    if post.get('industria'):
                        st.markdown(f"**Industria:** {post['industria']}")
                    if post.get('imagen_url'):
                        st.image(post['imagen_url'], width=200)
                    st.markdown(f"**Programado para:** {post.get('fecha_programada_legible')}")
                    
                    if st.button(f"🔄 Repogramar #{post['id']}", key=f"reschedule_{post['id']}"):
                        st.info("Usa el endpoint de API para reprogramar")
    except Exception as e:
        st.error(f"Error: {str(e)}")

with tabs[3]:
    st.header("📊 Analytics & Performance")
    
    try:
        stats = requests.get(f"{API_URL}/stats/detallado", timeout=10).json()
        
        # Overview metrics
        st.markdown("### 📈 Overview")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Posts", stats.get("total", 0))
        with col2:
            st.metric("Published", stats.get("por_estado", {}).get("publicado", 0))
        
        # Safely get engagement data
        engagement_data = stats.get("engagement")
        if isinstance(engagement_data, dict):
            with col3:
                st.metric("Total Views", engagement_data.get("visualizaciones_totales", 0))
            with col4:
                st.metric("Engagement Rate", f"{engagement_data.get('engagement_promedio', 0):.2f}%")
        else:
            with col3:
                st.metric("Total Views", 0)
            with col4:
                st.metric("Engagement Rate", "0%")
        
        # Detailed metrics
        if "engagement" in stats:
            st.markdown("### 📊 Detailed Metrics")
            
            col_m1, col_m2 = st.columns(2)
            
            with col_m1:
                st.markdown("#### 📱 By Platform")
                for plat, count in stats.get("por_plataforma", {}).items():
                    st.write(f"**{plat.upper()}:** {count} posts")
            
            with col_m2:
                st.markdown("#### 📈 Engagement by Platform")
                eng_data = stats.get("engagement", {})
                st.metric("Total Views", eng_data.get("visualizaciones_totales", 0))
                st.metric("Total Likes", eng_data.get("likes_totales", 0))
                st.metric("Total Comments", eng_data.get("comentarios_totales", 0))
                st.metric("Total Shares", eng_data.get("shares_totales", 0))
        
        # Published posts with metrics
        st.markdown("### 📄 Published Posts")
        
        try:
            pub_posts = requests.get(f"{API_URL}/posts/publicados", timeout=10).json()
            
            if pub_posts:
                for p in pub_posts:
                    with st.expander(f"#{p['id']} - {p['plataforma'].upper()} - {p.get('fecha_publicacion', 'N/A')[:10]}"):
                        st.markdown(f"**Titulo:** {p['titulo'][:60]}...")
                        st.markdown(f"🔗 [Link]({p.get('enlace', '#')})")
                        
                        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                        with col_m1:
                            st.metric("Views", p.get('visualizaciones', 0))
                        with col_m2:
                            st.metric("Likes", p.get('likes', 0))
                        with col_m3:
                            st.metric("Comments", p.get('comentarios', 0))
                        with col_m4:
                            st.metric("Engagement", f"{p.get('engagement_rate', 0):.2f}%")
                        
                        if st.button(f"🔄 Update Metrics #{p['id']}", key=f"upd_{p['id']}"):
                            try:
                                r = requests.post(f"{API_URL}/posts/{p['id']}/actualizar-metricas", timeout=30)
                                if r.status_code == 200:
                                    st.success("Metrics updated!")
                                    st.rerun()
                            except:
                                st.error("Error")
            else:
                st.info("No published posts yet")
        except Exception as e:
            st.error(f"Error: {e}")
        
    except Exception as e:
        st.error(f"Error loading analytics: {str(e)}")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #64748b;">
    <p>🤖 <strong>Alxpertus Content Generator v2.0</strong> - Automated AI Content Publishing</p>
    <p>💡 El sistema genera contenido EN INGLÉS automáticamente y lo publica en LinkedIn/X/Reddit</p>
</div>
""", unsafe_allow_html=True)