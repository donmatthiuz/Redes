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
        
class Red:

    def __init__(self, num_vertices):
        
        self.V = num_vertices  # Número de vértices
        # Inicializar matriz de adyacencia con infinito (sin conexión)
        self.graph = [[float('inf')] * num_vertices for _ in range(num_vertices)]
        
        # La distancia de un nodo a sí mismo es 0
        for i in range(num_vertices):
            self.graph[i][i] = 0
    
    def add_edge(self, src, dest, weight):
       
        if 0 <= src < self.V and 0 <= dest < self.V:
            self.graph[src][dest] = weight
            self.graph[dest][src] = weight  # Bidireccional
        else:
            raise ValueError(f"Índices de nodos fuera de rango: src={src}, dest={dest}")
    
    def remove_edge(self, src, dest):
       
        if 0 <= src < self.V and 0 <= dest < self.V:
            self.graph[src][dest] = float('inf')
            self.graph[dest][src] = float('inf')
    
    def set_graph(self, matrix):
       
        if len(matrix) == self.V and all(len(row) == self.V for row in matrix):
            self.graph = [row[:] for row in matrix]  # Copia profunda
        else:
            raise ValueError("La matriz debe ser cuadrada y coincidir con el número de vértices")
    
    def get_neighbors(self, node):
       
        neighbors = []
        if 0 <= node < self.V:
            for i in range(self.V):
                if self.graph[node][i] != float('inf') and i != node:
                    neighbors.append((i, self.graph[node][i]))
        return neighbors
    
    def print_graph(self):
       
        print("Matriz de adyacencia de la red:")
        print("    ", end="")
        for i in range(self.V):
            print(f"{i:4}", end="")
        print()
        
        for i in range(self.V):
            print(f"{i:2}: ", end="")
            for j in range(self.V):
                if self.graph[i][j] == float('inf'):
                    print(" ∞ ", end=" ")
                else:
                    print(f"{self.graph[i][j]:3}", end=" ")
            print()