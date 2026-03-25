import streamlit as st
import requests
import json
from datetime import datetime

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Alxpertus Content Generator", page_icon="🤖", layout="wide")

st.title("🤖 Alxpertus Content Generator")
st.markdown(f"**Tema central:** Equipos de Agentes IA: Tu Nueva Fuerza de Trabajo Digital en 2026")

tabs = st.tabs(["📝 Generar", "📅 Programar", "🖼️ Imágenes", "📋 Historial", "📊 Estadísticas"])

with tabs[0]:
    st.header("Generar Nuevo Post")
    
    col1, col2 = st.columns(2)
    
    with col1:
        plataforma = st.selectbox("Plataforma", ["linkedin", "x", "reddit"])
        tipo = st.selectbox("Tipo de post", ["general", "industria", "tendencia", "practico"])
    
    with col2:
        industria = st.text_input("Industria (opcional)", placeholder="e.g., Real Estate, E-commerce, Coaches")
        industria = industria if industria else None
    
    if st.button("🚀 Generar Post", type="primary"):
        with st.spinner("Generando contenido..."):
            try:
                response = requests.post(
                    f"{API_URL}/generar",
                    json={"plataforma": plataforma, "tipo": tipo, "industria": industria}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    st.success(f"✅ Post generado (ID: {data['id']})")
                    
                    st.text_area("Contenido generado:", value=data['contenido'], height=400)
                    
                    st.download_button(
                        label="📋 Copiar contenido",
                        data=data['contenido'],
                        file_name=f"{plataforma}_{tipo}_{datetime.now().strftime('%Y%m%d')}.txt",
                        mime="text/plain"
                    )
                    
                    with st.expander("Actualizar enlace de publicación"):
                        enlace = st.text_input("Enlace del post publicado")
                        if st.button("Guardar enlace"):
                            requests.put(f"{API_URL}/posts/{data['id']}/enlace", params={"enlace": enlace})
                            st.success("Enlace guardado!")
                else:
                    st.error(f"Error: {response.text}")
            except Exception as e:
                st.error(f"Error de conexión: {str(e)}")
                st.info("💡 Asegúrate de que el servidor API esté corriendo: python backend/api/main.py")

with tabs[1]:
    st.header("Programar Publicación")
    
    try:
        response = requests.get(f"{API_URL}/posts", params={"limite": 100})
        posts = response.json()
        
        if not posts:
            st.info("No hay posts disponibles. Genera uno primero en la pestaña 'Generar'.")
        else:
            post_options = {f"#{p['id']} - {p['plataforma'].upper()} | {p['tipo']}": p['id'] for p in posts}
            selected = st.selectbox("Seleccionar post", list(post_options.keys()))
            post_id = post_options[selected]
            
            st.subheader("Seleccionar fecha y hora")
            col1, col2 = st.columns(2)
            with col1:
                fecha = st.date_input("Fecha", min_value=datetime.now().date())
            with col2:
                hora = st.time_input("Hora", value=datetime.now().time())
            
            if st.button("📅 Programar", type="primary"):
                fecha_dt = datetime.combine(fecha, hora)
                response = requests.post(
                    f"{API_URL}/posts/{post_id}/programar",
                    json={"fecha_programada": fecha_dt.isoformat()}
                )
                if response.status_code == 200:
                    st.success(f"✅ Post programado para {fecha_dt.strftime('%d/%m/%Y %H:%M')}")
                else:
                    st.error(f"Error: {response.text}")
            
            st.subheader("Posts Programados")
            try:
                response = requests.get(f"{API_URL}/posts/programados")
                programmed = response.json()
                if programmed:
                    for p in programmed:
                        st.write(f"• #{p['id']} - {p['plataforma'].upper()} - {p['fecha_programada'][:16].replace('T', ' ')}")
                else:
                    st.info("No hay posts programados.")
            except:
                pass
                
    except Exception as e:
        st.error(f"Error: {str(e)}")

with tabs[2]:
    st.header("Generar Imágenes con DALL-E")
    
    try:
        response = requests.get(f"{API_URL}/posts", params={"limite": 100})
        posts = response.json()
        
        if not posts:
            st.info("No hay posts disponibles.")
        else:
            post_options = {f"#{p['id']} - {p['plataforma'].upper()} | {p['tipo']}": p['id'] for p in posts}
            selected = st.selectbox("Seleccionar post para imagen", list(post_options.keys()))
            post_id = post_options[selected]
            
            if st.button("🖼️ Generar Imagen", type="primary"):
                with st.spinner("Generando imagen con DALL-E 3..."):
                    try:
                        response = requests.post(f"{API_URL}/posts/{post_id}/imagen")
                        if response.status_code == 200:
                            data = response.json()
                            st.success("✅ Imagen generada!")
                            st.image(data['imagen_url'], caption="Imagen generada", use_container_width=True)
                            st.markdown(f"**Prompt usado:** {data['prompt_usado']}")
                            if data.get('revised_prompt'):
                                st.markdown(f"*Prompt revisado por DALL-E: {data['revised_prompt']}*")
                        else:
                            st.error(f"Error: {response.text}")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
                        st.info("💡 Asegúrate de tener OPENAI_API_KEY configurada en .env")
                        
    except Exception as e:
        st.error(f"Error: {str(e)}")

with tabs[3]:
    st.header("Historial de Posts")
    
    filtro_plataforma = st.selectbox("Filtrar por plataforma", ["todos", "linkedin", "x", "reddit"])
    
    try:
        filtro = None if filtro_plataforma == "todos" else filtro_plataforma
        response = requests.get(f"{API_URL}/posts", params={"plataforma": filtro, "limite": 100})
        posts = response.json()
        
        if posts:
            for post in posts:
                with st.expander(f"#{post['id']} - {post['plataforma'].upper()} | {post['tipo']} | {post['fecha_creacion'][:10]}"):
                    st.markdown(f"**Título:** {post['titulo']}")
                    if post.get('industria'):
                        st.markdown(f"**Industria:** {post['industria']}")
                    
                    detalle = requests.get(f"{API_URL}/posts/{post['id']}")
                    if detalle.status_code == 200:
                        datos = detalle.json()
                        st.text_area("Contenido:", value=datos.get('contenido', ''), height=200)
                        
                        if datos.get('imagen_url'):
                            st.image(datos['imagen_url'], caption="Imagen asociada", width=300)
                        if datos.get('enlace'):
                            st.markdown(f"🔗 **Enlace:** {datos['enlace']}")
        else:
            st.info("No hay posts generados aún.")
    except Exception as e:
        st.error(f"Error: {str(e)}")

with tabs[4]:
    st.header("Estadísticas")
    
    try:
        response = requests.get(f"{API_URL}/stats")
        stats = response.json()
        
        st.metric("Total Posts", stats['total'])
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Por Plataforma")
            for plat, count in stats['por_plataforma'].items():
                st.write(f"**{plat.upper()}:** {count}")
        
        with col2:
            st.subheader("Por Tipo")
            for tipo, count in stats['por_tipo'].items():
                st.write(f"**{tipo}:** {count}")
                
    except Exception as e:
        st.error(f"Error: {str(e)}")

st.markdown("---")
st.markdown("💡 **Tips:**")
st.markdown("- Para generar serie completa: corre `python backend/generator.py`")
st.markdown("- API disponible en: `http://localhost:8000`")