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
    """
    Clase que representa una red como grafo con matriz de adyacencia
    """
    def __init__(self, num_vertices):
        """
        Inicializa la red con el número de vértices especificado
        
        Args:
            num_vertices (int): Número de nodos en la red
        """
        self.V = num_vertices  # Número de vértices
        # Inicializar matriz de adyacencia con infinito (sin conexión)
        self.graph = [[float('inf')] * num_vertices for _ in range(num_vertices)]
        
        # La distancia de un nodo a sí mismo es 0
        for i in range(num_vertices):
            self.graph[i][i] = 0
    
    def add_edge(self, src, dest, weight):
        """
        Añade una arista bidireccional entre dos nodos
        
        Args:
            src (int): Nodo origen
            dest (int): Nodo destino  
            weight (int): Peso de la arista
        """
        if 0 <= src < self.V and 0 <= dest < self.V:
            self.graph[src][dest] = weight
            self.graph[dest][src] = weight  # Bidireccional
        else:
            raise ValueError(f"Índices de nodos fuera de rango: src={src}, dest={dest}")
    
    def remove_edge(self, src, dest):
        """
        Elimina la arista entre dos nodos
        
        Args:
            src (int): Nodo origen
            dest (int): Nodo destino
        """
        if 0 <= src < self.V and 0 <= dest < self.V:
            self.graph[src][dest] = float('inf')
            self.graph[dest][src] = float('inf')
    
    def set_graph(self, matrix):
        """
        Establece toda la matriz de adyacencia
        
        Args:
            matrix (List[List[int]]): Matriz de adyacencia
        """
        if len(matrix) == self.V and all(len(row) == self.V for row in matrix):
            self.graph = [row[:] for row in matrix]  # Copia profunda
        else:
            raise ValueError("La matriz debe ser cuadrada y coincidir con el número de vértices")
    
    def get_neighbors(self, node):
        """
        Obtiene los vecinos directos de un nodo
        
        Args:
            node (int): Índice del nodo
            
        Returns:
            List[Tuple[int, int]]: Lista de tuplas (vecino, peso)
        """
        neighbors = []
        if 0 <= node < self.V:
            for i in range(self.V):
                if self.graph[node][i] != float('inf') and i != node:
                    neighbors.append((i, self.graph[node][i]))
        return neighbors
    
    def print_graph(self):
        """Imprime la matriz de adyacencia de forma legible"""
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