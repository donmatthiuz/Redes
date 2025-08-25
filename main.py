# va a crear 2 nodos  
# el .env de la raiz es el usuario/puerto
from connection.Nodo import Nodo
from data.Lector import create_sample_config

if __name__ == "__main__":
    import sys
    
    # Crear archivos de configuración si no existen
    create_sample_config()
    
    if len(sys.argv) != 3:
        print("Uso: python main.py <node_id> <algoritmo>")
        print("Ejemplo: python main.py A ")
        sys.exit(1)
    
    node_id = sys.argv[1].upper()
    algorithm = sys.argv[2].lower() if len(sys.argv) > 2 else "flooding"
    port = 5000 + ord(node_id) - ord('A')  # A=5000, B=5001, C=5002, D=5003
    
    node = Nodo(node_id, port=port, algorithm=algorithm)
    node.main_executor()