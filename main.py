# va a crear 2 nodos  
# el .env de la raiz es el usuario/puerto
from connection.Nodo import Nodo
from data.Lector import create_sample_config

if __name__ == "__main__":
    import sys
    
    # Crear archivos de configuración si no existen
    create_sample_config()
    
    if len(sys.argv) != 2:
        print("Uso: python integrated_node.py <node_id>")
        print("Ejemplo: python integrated_node.py A")
        sys.exit(1)
    
    node_id = sys.argv[1]
    port = 5000 + ord(node_id) - ord('A')  # A=5000, B=5001, C=5002, D=5003
    
    node = Nodo(node_id, port=port)
    node.main_executor()