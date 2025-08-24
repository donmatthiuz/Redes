import json

class RedConfig:
    def __init__(self):
        pass
    
    def load_topology(file_path):
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            return data.get("config", {})
        except:
            return {}
        
    def load_names(file_path):
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            return data.get("config", {})
        except:
            return {}