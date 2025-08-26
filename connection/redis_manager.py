import redis
import json
import threading
import time
from typing import Callable, Optional

class RedisManager:
    def __init__(self, host="lab3.redesuvg.cloud", port=6379, password="UVGRedis2025"):
        self.host = host
        self.port = port
        self.password = password
        self.redis_client = None
        self.pubsub = None
        self.running = False
        self.on_message_callback: Optional[Callable] = None
        self.listen_thread = None
        self.my_channel = None
        
    def connect(self):
        try:
            self.redis_client = redis.Redis(
                host=self.host, 
                port=self.port, 
                password=self.password,
                decode_responses=True  # Para recibir strings en lugar de bytes
            )
            
            self.redis_client.ping()
            print(f" Conectado a Redis: {self.host}:{self.port}")
            return True
            
        except redis.ConnectionError as e:
            print(f" Error conectando a Redis: {e}")
            return False
        except redis.AuthenticationError as e:
            print(f" Error de autenticación Redis: {e}")
            return False
        except Exception as e:
            print(f" Error inesperado conectando a Redis: {e}")
            return False
    
    def subscribe_to_channel(self, channel_name: str):
        if not self.redis_client:
            print(" No hay conexión a Redis")
            return False
            
        try:
            self.my_channel = channel_name
            self.pubsub = self.redis_client.pubsub()
            self.pubsub.subscribe(channel_name)
            print(f" Suscrito al canal: {channel_name}")
            return True
            
        except Exception as e:
            print(f" Error suscribiéndose al canal {channel_name}: {e}")
            return False
    
    def start_listening(self):
        if not self.pubsub:
            print(" No hay suscripción activa")
            return False
            
        self.running = True
        self.listen_thread = threading.Thread(target=self._listen_messages)
        self.listen_thread.daemon = True
        self.listen_thread.start()
        print(" Escuchando mensajes en hilo separado")
        return True
    
    def _listen_messages(self):
        try:
            for message in self.pubsub.listen():
                if not self.running:
                    break
                    
                if message['type'] == 'message':
                    channel = message['channel']
                    data = message['data']
                    
                    try:
                        # Intentar decodificar como JSON
                        parsed_message = json.loads(data)
                        
                        # Llamar al callback si existe
                        if self.on_message_callback:
                            self.on_message_callback(parsed_message, channel)
                            
                    except json.JSONDecodeError:
                        print(f" Mensaje no JSON recibido de {channel}: {data}")
                        
                    except Exception as e:
                        print(f" Error procesando mensaje de {channel}: {e}")
                        
        except Exception as e:
            print(f" Error en hilo de escucha Redis: {e}")
        finally:
            print(" Hilo de escucha Redis terminado")
    
    def publish_message(self, channel: str, message: dict) -> bool:
        """
        Publica un mensaje en un canal específico.
        """
        if not self.redis_client:
            print(" No hay conexión a Redis")
            return False
            
        try:
            json_message = json.dumps(message)
            result = self.redis_client.publish(channel, json_message)
            
            # result es el número de suscriptores que recibieron el mensaje
            if result > 0:
                print(f" Mensaje enviado a {channel} ({result} suscriptores)")
            else:
                print(f" Mensaje enviado a {channel} (sin suscriptores)")
            
            return True
            
        except Exception as e:
            print(f" Error publicando mensaje a {channel}: {e}")
            return False
    
    def set_message_callback(self, callback: Callable):
        self.on_message_callback = callback
    
    def get_active_channels(self):
        if not self.redis_client:
            return []
            
        try:
            channels = self.redis_client.pubsub_channels()
            return channels
        except Exception as e:
            print(f" No se pueden obtener canales activos: {e}")
            return []
    
    def send_to_neighbor(self, neighbor_channel: str, message: dict) -> bool:
        return self.publish_message(neighbor_channel, message)
    
    def broadcast_to_neighbors(self, neighbor_channels: list, message: dict) -> int:
        successful_sends = 0
        
        for channel in neighbor_channels:
            if self.publish_message(channel, message):
                successful_sends += 1
            time.sleep(0.01)
        
        return successful_sends
    
    def stop(self):
        print(" Deteniendo Redis Manager...")
        self.running = False
        
        if self.pubsub:
            try:
                self.pubsub.unsubscribe()
                self.pubsub.close()
            except:
                pass
        
        if self.listen_thread and self.listen_thread.is_alive():
            self.listen_thread.join(timeout=2)
        
        if self.redis_client:
            try:
                self.redis_client.close()
            except:
                pass
        
        print(" Redis Manager detenido")
    
    def is_connected(self) -> bool:
        if not self.redis_client:
            return False
            
        try:
            self.redis_client.ping()
            return True
        except:
            return False