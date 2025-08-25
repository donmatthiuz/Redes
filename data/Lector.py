import json

def create_sample_config():
    import os
    os.makedirs("data", exist_ok=True)
    
    topo_data = {
        "type": "topo",
        "config": {
            "A": ["B"],
            "B": ["A"]
         
        }
    }
    
    names_data = {
        "type": "names",
        "config": {
            "A": "nodeA@localhost",
            "B": "nodeB@localhost",
          
        }
    }
    
    with open("data/topo.txt", "w") as f:
        json.dump(topo_data, f, indent=2)
    
    with open("data/id_nodos.txt", "w") as f:
        json.dump(names_data, f, indent=2)
    
    print("✅ Archivos de configuración creados en /data/")

