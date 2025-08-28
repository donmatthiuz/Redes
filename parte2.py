import time
import sys
from connection.NodoconRedis import NodoRedisFlooding

def message_handler(msg, channel):
    print(f"Mensaje recibido en {channel}: {msg}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python main.py <node_id> <algoritmo>")
        print("Ejemplo: python main.py A ")
        sys.exit(1)
    node_id = sys.argv[1].upper()
    algorithm = sys.argv[2].lower() if len(sys.argv) > 2 else "flooding"
    node = NodoRedisFlooding(node_id)
    node.run()