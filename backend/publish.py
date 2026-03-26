import os
import requests
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class LinkedInPublisher:
    """Publicador de LinkedIn usando la API v2"""
    
    def __init__(self):
        self.access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
        self.base_url = "https://api.linkedin.com/v2"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }
    
    def _obtener_user_urn(self) -> str:
        """Obtiene el URN del usuario actual usando múltiples métodos"""
        # Método 1: Intentar /me endpoint
        try:
            response = requests.get(
                f"{self.base_url}/me",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                user_id = data.get("id")
                return f"urn:li:person:{user_id}"
        except:
            pass
        
        # Método 2: Intentar con endpoint de perfilLite
        try:
            response = requests.get(
                f"{self.base_url}/me",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "X-Restli-Protocol-Version": "2.0.0",
                    "Authorization-Extra-Override": "true"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                user_id = data.get("id")
                return f"urn:li:person:{user_id}"
        except:
            pass
        
        # Método 3: Returnar URN genérico si el token tiene w_member_social
        # El API debería permitirnos publicar con el token directamente
        return "urn:li:person:UNKNOWN"

    def publicar(self, contenido: str, titulo: str = None, imagen_url: str = None) -> dict:
        """Publica un artículo en LinkedIn"""
        
        try:
            # Obtener el URN del usuario
            author_urn = self._obtener_user_urn()
            if not author_urn:
                return {
                    "success": False,
                    "error": "No se pudo obtener el ID de usuario de LinkedIn. Token inválido o expirado."
                }
            
            # Preparar el contenido
            if titulo:
                article_text = f"{titulo}\n\n{contenido}"
            else:
                article_text = contenido
            
            # LinkedIn tiene límite de 3000 caracteres
            article_text = article_text[:3000]
            
            # Publicar como post simple
            post_data = {
                "author": author_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": article_text
                        },
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
            
            response = requests.post(
                f"{self.base_url}/ugcPosts",
                headers=self.headers,
                json=post_data,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                post_id = data.get("id", "")
                return {
                    "success": True,
                    "platform": "linkedin",
                    "post_id": post_id,
                    "url": f"https://www.linkedin.com/feed/update/{post_id}",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "success": False,
                    "error": f"LinkedIn API Error: {response.status_code} - {response.text[:200]}",
                    "status_code": response.status_code
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _subir_imagen(self, imagen_path: str) -> str:
        """Sube una imagen a LinkedIn y retorna el URN"""
        try:
            # Primero necesitamos el ID de usuario
            me_response = requests.get(
                f"{self.base_url}/me",
                headers=self.headers,
                timeout=10
            )
            
            if me_response.status_code != 200:
                return None
            
            person_id = me_response.json().get("id")
            if not person_id:
                return None
            
            # Subir imagen
            with open(imagen_path, "rb") as f:
                image_data = f.read()
            
            # LinkedIn requiere-registerUpload para imágenes
            register_response = requests.post(
                f"{self.base_url}/assets",
                headers=self.headers,
                json={
                    "registerUploadRequest": {
                        "recipes": ["urn:li:assetRecipe:ACTOR_CARD_100x100"],
                        "owner": f"urn:li:person:{person_id}",
                        "serviceRelationships": [{
                            "relationshipType": "OWNER",
                            "identifier": "urn:li:userGeneratedContent"
                        }]
                    }
                },
                timeout=30
            )
            
            if register_response.status_code != 200:
                print(f"Error registering upload: {register_response.text}")
                return None
            
            upload_url = register_response.json().get("value", {}).get("uploadMechanism", {}).get("com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest", {}).get("uploadUrl")
            
            if not upload_url:
                return None
            
            # Subir la imagen
            upload_response = requests.post(
                upload_url,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "image/png"
                },
                data=image_data,
                timeout=60
            )
            
            if upload_response.status_code in [200, 201]:
                asset_urn = register_response.json().get("value", {}).get("asset")
                return asset_urn
            
            return None
            
        except Exception as e:
            print(f"Error uploading image: {e}")
            return None
    
    def obtener_metricas(self, post_id: str) -> dict:
        """Obtiene métricas del post"""
        try:
            response = requests.get(
                f"{self.base_url}/ugcPosts/{post_id}",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "visualizaciones": data.get("totalShadows", 0),
                    "likes": data.get("totalLikes", 0),
                    "comentarios": data.get("totalComments", 0)
                }
        except:
            pass
        
        return {"visualizaciones": 0, "likes": 0, "comentarios": 0}


class XPublisher:
    """Publicador de X/Twitter"""
    
    def __init__(self):
        self.api_key = os.getenv("X_API_KEY")
        self.api_secret = os.getenv("X_API_SECRET")
        self.access_token = os.getenv("X_ACCESS_TOKEN")
        self.access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")
        self.bearer_token = os.getenv("X_BEARER_TOKEN")
        
        # URL de API de X
        self.tweet_url = "https://api.twitter.com/2/tweets"
        self.media_url = "https://upload.twitter.com/1.1/media/upload.json"
    
    def publicar(self, contenido: str, titulo: str = None, imagen_url: str = None) -> dict:
        """Publica un tweet (con imagen si está disponible)"""
        
        try:
            if not self.bearer_token:
                return {
                    "success": False,
                    "error": "X/Bearer Token no configurado en .env"
                }
            
            headers = {
                "Authorization": f"Bearer {self.bearer_token}",
                "Content-Type": "application/json"
            }
            
            # Preparar texto del tweet
            if titulo:
                tweet_text = f"{titulo}\n\n{contenido}"
            else:
                tweet_text = contenido
            
            # X tiene límite de 280 caracteres, enviar como artículo largo
            tweet_data = {
                "text": tweet_text[:280]
            }
            
            response = requests.post(
                self.tweet_url,
                headers=headers,
                json=tweet_data,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                tweet_id = data.get("data", {}).get("id", "")
                return {
                    "success": True,
                    "platform": "x",
                    "post_id": tweet_id,
                    "url": f"https://twitter.com/i/status/{tweet_id}",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "success": False,
                    "error": f"X API Error: {response.status_code} - {response.text[:200]}",
                    "status_code": response.status_code
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def obtener_metricas(self, tweet_id: str) -> dict:
        """Obtiene métricas del tweet"""
        try:
            headers = {
                "Authorization": f"Bearer {self.bearer_token}"
            }
            
            response = requests.get(
                f"https://api.twitter.com/2/tweets/{tweet_id}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "visualizaciones": data.get("data", {}).get("public_metrics", {}).get("impression_count", 0),
                    "likes": data.get("data", {}).get("public_metrics", {}).get("like_count", 0),
                    "retweets": data.get("data", {}).get("public_metrics", {}).get("retweet_count", 0),
                    "replies": data.get("data", {}).get("public_metrics", {}).get("reply_count", 0)
                }
        except:
            pass
        
        return {"visualizaciones": 0, "likes": 0, "retweets": 0, "replies": 0}


class RedditPublisher:
    """Publicador de Reddit"""
    
    def __init__(self):
        self.client_id = os.getenv("REDDIT_CLIENT_ID")
        self.client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        self.username = os.getenv("REDDIT_USERNAME")
        self.password = os.getenv("REDDIT_PASSWORD")
        self.subreddit = os.getenv("REDDIT_SUBREDDIT", "GrowMyBusinessNow")
        
        self.access_token = None
        self._obtener_token()
    
    def _obtener_token(self):
        """Obtiene token de acceso de Reddit"""
        try:
            auth = requests.auth.HTTPBasicAuth(self.client_id, self.client_secret)
            data = {
                "grant_type": "password",
                "username": self.username,
                "password": self.password
            }
            headers = {"User-Agent": "AlxpertusContentGenerator/1.0"}
            
            response = requests.post(
                "https://www.reddit.com/api/v1/access_token",
                auth=auth,
                data=data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                self.access_token = response.json().get("access_token")
                
        except:
            pass
    
    def publicar(self, contenido: str, titulo: str = None, imagen_url: str = None) -> dict:
        """Publica un post en Reddit"""
        
        try:
            if not self.access_token:
                return {
                    "success": False,
                    "error": "Reddit credentials no configuradas en .env"
                }
            
            headers = {
                "Authorization": f"bearer {self.access_token}",
                "User-Agent": "AlxpertusContentGenerator/1.0"
            }
            
            # Preparar datos del post
            post_data = {
                "sr": self.subreddit,
                "kind": "self",
                "title": titulo[:300] if titulo else "AI Agent Teams in 2026",
                "text": contenido
            }
            
            response = requests.post(
                "https://oauth.reddit.com/api/submit",
                headers=headers,
                data=post_data,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                post_id = data.get("data", {}).get("id", "")
                permalink = data.get("data", {}).get("permalink", "")
                
                return {
                    "success": True,
                    "platform": "reddit",
                    "post_id": post_id,
                    "url": f"https://reddit.com{permalink}",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "success": False,
                    "error": f"Reddit API Error: {response.status_code} - {response.text[:200]}",
                    "status_code": response.status_code
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def obtener_metricas(self, post_id: str) -> dict:
        """Obtiene métricas del post de Reddit"""
        try:
            headers = {
                "Authorization": f"bearer {self.access_token}",
                "User-Agent": "AlxpertusContentGenerator/1.0"
            }
            
            response = requests.get(
                f"https://oauth.reddit.com/api/info.json?id=t3_{post_id}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                children = data.get("data", {}).get("children", [])
                if children:
                    post_data = children[0].get("data", {})
                    return {
                        "visualizaciones": post_data.get("view_count", 0),
                        "upvotes": post_data.get("ups", 0),
                        "downvotes": post_data.get("downs", 0),
                        "comentarios": post_data.get("num_comments", 0)
                    }
        except:
            pass
        
        return {"visualizaciones": 0, "upvotes": 0, "comentarios": 0}


def obtener_publicador(plataforma: str):
    """Obtiene el publicador adecuado según la plataforma"""
    publicadores = {
        "linkedin": LinkedInPublisher,
        "x": XPublisher,
        "reddit": RedditPublisher
    }
    
    publicador_class = publicadores.get(plataforma.lower())
    if publicador_class:
        return publicador_class()
    return None


def publicar_post(post_id: int) -> dict:
    """Publica un post en la plataforma correspondiente"""
    
    from db.database import obtener_post_por_id, marcar_publicado, marcar_error
    
    # Obtener el post
    post = obtener_post_por_id(post_id)
    if not post:
        return {"success": False, "error": "Post no encontrado"}
    
    # Obtener el publicador adecuado
    publicador = obtener_publicador(post.plataforma)
    if not publicador:
        return {"success": False, "error": f"Plataforma {post.plataforma} no soportada"}
    
    # Publicar
    resultado = publicador.publicar(
        contenido=post.contenido,
        titulo=post.titulo,
        imagen_url=post.imagen_url
    )
    
    if resultado.get("success"):
        # Marcar como publicado
        enlace = resultado.get("url", "")
        marcar_publicado(post_id, enlace)
        return {
            "success": True,
            "platform": post.plataforma,
            "url": enlace,
            "post_id": resultado.get("post_id")
        }
    else:
        # Marcar como error
        marcar_error(post_id, resultado.get("error", "Error desconocido"))
        return resultado


def actualizar_metricas_post(post_id: int) -> dict:
    """Actualiza las métricas de un post publicado"""
    
    from db.database import obtener_post_por_id, actualizar_metricas
    
    post = obtener_post_por_id(post_id)
    if not post or not post.enlace:
        return {"success": False, "error": "Post no encontrado o sin enlace"}
    
    publicador = obtener_publicador(post.plataforma)
    if not publicador:
        return {"success": False, "error": "Publicador no encontrado"}
    
    # Extraer ID del post desde el enlace
    post_id_external = post.enlace.split("/")[-1]
    
    metricas = publicador.obtener_metricas(post_id_external)
    
    # Actualizar en base de datos
    actualizar_metricas(
        post_id,
        visualizaciones=metricas.get("visualizaciones", 0),
        likes=metricas.get("likes", metricas.get("upvotes", 0)),
        comentarios=metricas.get("comentarios", 0),
        shares=metricas.get("retweets", 0)
    )
    
    return {"success": True, "metricas": metricas}


if __name__ == "__main__":
    print("🖥️ Alxpertus Post Publisher")
    print("=" * 40)
    print("Testing publication connection...")
    
    # Test LinkedIn
    print("\n📱 LinkedIn:")
    linkedin = LinkedInPublisher()
    print(f"  Token configured: {bool(linkedin.access_token)}")
    
    # Test X
    print("\n🐦 X/Twitter:")
    x = XPublisher()
    print(f"  Bearer Token configured: {bool(x.bearer_token)}")
    
    # Test Reddit
    print("\n🤖 Reddit:")
    reddit = RedditPublisher()
    print(f"  Access Token: {'Configured' if reddit.access_token else 'Not configured'}")
    
    print("\n✅ Publisher module ready")