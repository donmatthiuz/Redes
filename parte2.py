import time
import sys
from connection.redis_manager import RedisManager
from connection.NodoconRedis import NodoRedisSimple

def message_handler(msg, channel):
    print(f"Mensaje recibido en {channel}: {msg}")

""" if __name__ == "__main__":
    # Crear el manager
    manager = RedisManager()
    
    # Conectar a Redis
    if not manager.connect():
        print("No se pudo conectar a Redis")
        exit(1)
    
    # Configurar callback
    manager.set_message_callback(message_handler)
    
    # Suscribirse a un canal
    canal = "SaquenAChen"
    if not manager.subscribe_to_channel(canal):
        print("No se pudo suscribir al canal")
        exit(1)
    
    # Empezar a escuchar mensajes en un hilo separado
    manager.start_listening()
    
    # Publicar un mensaje
    manager.publish_message(canal, {"texto": "Hola desde RedisManager"})
    
    # Esperar un poco para recibir el mensaje
    time.sleep(2)
    
    # Detener el manager
    manager.stop()
 """


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python main.py <node_id> <algoritmo>")
        print("Ejemplo: python main.py A ")
        sys.exit(1)
    node_id = sys.argv[1].upper()
    algorithm = sys.argv[2].lower() if len(sys.argv) > 2 else "flooding"
    node = NodoRedisSimple(node_id)
    node.run()