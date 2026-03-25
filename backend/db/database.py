from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class Post(Base):
    __tablename__ = 'posts'
    
    id = Column(Integer, primary_key=True)
    titulo = Column(String(500))
    plataforma = Column(String(50))
    tipo = Column(String(50))
    industria = Column(String(100), nullable=True)
    contenido = Column(Text)
    enlace = Column(String(500), nullable=True)
    imagen_url = Column(String(500), nullable=True)
    fecha_creacion = Column(DateTime, default=datetime.now)
    fecha_publicacion = Column(DateTime, nullable=True)
    fecha_programada = Column(DateTime, nullable=True)
    estado = Column(String(20), default="pendiente")

engine = create_engine('sqlite:///contenido.db', echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def guardar_post(titulo: str, plataforma: str, tipo: str, contenido: str, industria: str = None, enlace: str = None) -> int:
    session = Session()
    post = Post(
        titulo=titulo,
        plataforma=plataforma,
        tipo=tipo,
        industria=industria,
        contenido=contenido,
        enlace=enlace
    )
    session.add(post)
    session.commit()
    post_id = post.id
    session.close()
    return post_id

def obtener_posts(filtro_plataforma: str = None, limite: int = 50):
    session = Session()
    query = session.query(Post)
    
    if filtro_plataforma:
        query = query.filter(Post.plataforma == filtro_plataforma)
    
    posts = query.order_by(Post.fecha_creacion.desc()).limit(limite).all()
    session.close()
    return posts

def obtener_estadisticas():
    session = Session()
    
    total = session.query(Post).count()
    por_plataforma = {}
    for plat in ['linkedin', 'x', 'reddit']:
        por_plataforma[plat] = session.query(Post).filter(Post.plataforma == plat).count()
    
    por_tipo = {}
    for tipo in ['general', 'industria', 'tendencia', 'practico']:
        por_tipo[tipo] = session.query(Post).filter(Post.tipo == tipo).count()
    
    session.close()
    
    return {
        "total": total,
        "por_plataforma": por_plataforma,
        "por_tipo": por_tipo
    }

def actualizar_enlace(post_id: int, enlace: str):
    session = Session()
    post = session.query(Post).filter(Post.id == post_id).first()
    if post:
        post.enlace = enlace
        session.commit()
    session.close()

def actualizar_imagen(post_id: int, imagen_url: str):
    session = Session()
    post = session.query(Post).filter(Post.id == post_id).first()
    if post:
        post.imagen_url = imagen_url
        session.commit()
    session.close()

def programar_post(post_id: int, fecha_programada: datetime):
    session = Session()
    post = session.query(Post).filter(Post.id == post_id).first()
    if post:
        post.fecha_programada = fecha_programada
        post.estado = "programado"
        session.commit()
    session.close()

def obtener_posts_programados():
    session = Session()
    posts = session.query(Post).filter(
        Post.estado == "programado",
        Post.fecha_programada != None
    ).order_by(Post.fecha_programada.asc()).all()
    session.close()
    return posts

def marcar_publicado(post_id: int):
    session = Session()
    post = session.query(Post).filter(Post.id == post_id).first()
    if post:
        post.estado = "publicado"
        post.fecha_publicacion = datetime.now()
        session.commit()
    session.close()