# va a crear 2 nodos  
# el .env de la raiz es el usuario/puerto
from connection.Nodo import Nodo

import json
def create_sample_config():
    import os
    os.makedirs("data", exist_ok=True)
    
    topo_data = {
        "type": "topo",
        "config": {
            "A": ["B", "C"],
            "B": ["A", "C", "D"],
            "C": ["A", "B", "D"],
            "D": ["B", "C"]
        }
    }
    
    names_data = {
        "type": "names",
        "config": {
            "A": "nodeA@localhost",
            "B": "nodeB@localhost",
            "C": "nodeC@localhost",
            "D": "nodeD@localhost"
        }
    }
    
    with open("data/topo.txt", "w") as f:
        json.dump(topo_data, f, indent=2)
    
    with open("data/id_nodos.txt", "w") as f:
        json.dump(names_data, f, indent=2)
    
    print("✅ Archivos de configuración creados en /data/")


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
    node.start_all_processes()