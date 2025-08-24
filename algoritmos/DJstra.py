
from connection.Red import Red

class SolveDjstra:
    """
    Implementación del algoritmo de Dijkstra para encontrar rutas más cortas
    """
    def __init__(self, mi_red: Red):
        """
        Inicializa el solver de Dijkstra con una red
        
        Args:
            mi_red (Red): Instancia de la red a procesar
        """
        self.red = mi_red

    def min_distance(self, dist, spt_set):
        """
        Encuentra el vértice con la distancia mínima que no está en el SPT
        
        Args:
            dist (List[int]): Array de distancias
            spt_set (List[bool]): Array que indica si el vértice está en SPT
            
        Returns:
            int: Índice del vértice con distancia mínima
        """
        min_dist = float('inf')
        min_index = -1
        
        for v in range(self.red.V):
            if dist[v] < min_dist and not spt_set[v]:
                min_dist = dist[v]
                min_index = v
        
        return min_index

    def print_solution(self, dist, src):
        """
        Imprime la solución de Dijkstra
        
        Args:
            dist (List[int]): Array de distancias más cortas
            src (int): Nodo fuente
        """
        print(f"\nDistancias más cortas desde el nodo {src}:")
        print("Nodo\tDistancia\tRuta")
        print("-" * 30)
        for node in range(self.red.V):
            if dist[node] == float('inf'):
                print(f"{node}\t∞\t\tNo alcanzable")
            else:
                print(f"{node}\t{dist[node]}")

    def dijkstra(self, src):
        """
        Ejecuta el algoritmo de Dijkstra desde un nodo fuente
        
        Args:
            src (int): Nodo fuente
            
        Returns:
            Tuple[List[int], List[int]]: (distancias, predecesores)
        """
        if not (0 <= src < self.red.V):
            raise ValueError(f"Nodo fuente {src} fuera de rango")
        
        # Inicializar distancias y conjunto SPT
        dist = [float('inf')] * self.red.V
        dist[src] = 0
        spt_set = [False] * self.red.V
        parent = [-1] * self.red.V  # Para reconstruir rutas
        
        # Procesar todos los vértices
        for _ in range(self.red.V):
            # Encontrar el vértice con distancia mínima
            u = self.min_distance(dist, spt_set)
            
            if u == -1:  # No hay más vértices alcanzables
                break
                
            # Marcar el vértice como procesado
            spt_set[u] = True
            
            # Actualizar distancias de los vecinos
            for v in range(self.red.V):
                # Condiciones para actualizar dist[v]:
                # 1. No está en SPT
                # 2. Existe arista de u a v
                # 3. La nueva ruta es más corta
                if (not spt_set[v] and 
                    self.red.graph[u][v] != float('inf') and 
                    dist[u] != float('inf') and
                    dist[u] + self.red.graph[u][v] < dist[v]):
                    
                    dist[v] = dist[u] + self.red.graph[u][v]
                    parent[v] = u
        
        return dist, parent

    def dijkstra_with_paths(self, src):
        """
        Versión extendida que también devuelve las rutas completas
        
        Args:
            src (int): Nodo fuente
            
        Returns:
            Tuple[List[int], Dict[int, List[int]]]: (distancias, rutas)
        """
        dist, parent = self.dijkstra(src)
        
        # Reconstruir rutas
        paths = {}
        for dest in range(self.red.V):
            if dist[dest] != float('inf'):
                path = []
                current = dest
                while current != -1:
                    path.append(current)
                    current = parent[current]
                path.reverse()
                paths[dest] = path
            else:
                paths[dest] = []  # No hay ruta
        
        return dist, paths

    def get_shortest_path(self, src, dest):
        """
        Obtiene la ruta más corta entre dos nodos específicos
        
        Args:
            src (int): Nodo origen
            dest (int): Nodo destino
            
        Returns:
            Tuple[int, List[int]]: (distancia, ruta)
        """
        if not (0 <= src < self.red.V and 0 <= dest < self.red.V):
            raise ValueError("Nodos fuera de rango")
        
        dist, paths = self.dijkstra_with_paths(src)
        return dist[dest], paths[dest]

    def get_routing_table(self, src):
        """
        Genera una tabla de ruteo desde un nodo fuente
        
        Args:
            src (int): Nodo fuente
            
        Returns:
            Dict[int, Dict]: Tabla de ruteo con next_hop y distancia
        """
        dist, parent = self.dijkstra(src)
        routing_table = {}
        
        for dest in range(self.red.V):
            if dest != src and dist[dest] != float('inf'):
                # Encontrar el próximo salto
                next_hop = dest
                while parent[next_hop] != src and parent[next_hop] != -1:
                    next_hop = parent[next_hop]
                
                routing_table[dest] = {
                    'next_hop': next_hop,
                    'distance': dist[dest],
                    'reachable': True
                }
            elif dest != src:
                routing_table[dest] = {
                    'next_hop': -1,
                    'distance': float('inf'),
                    'reachable': False
                }
        
        return routing_table