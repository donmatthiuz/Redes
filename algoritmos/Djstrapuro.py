import heapq
from typing import Dict, List, Tuple, Optional, Set
import math

class DijkstraPure:
    """
    Implementación pura del algoritmo de Dijkstra para encontrar caminos más cortos.
    No depende de protocolos de red, solo calcula rutas basándose en una topología conocida.
    """
    
    def __init__(self):
        # Grafo representado como diccionario de adyacencia
        # nodo -> [(vecino, costo), ...]
        self.graph = {}
        
        # Cache de rutas calculadas
        self.routes_cache = {}
        
        # Estadísticas
        self.calculations_count = 0
        
    def add_node(self, node_id: str):
        """Agregar un nodo al grafo"""
        if node_id not in self.graph:
            self.graph[node_id] = []
            self._clear_cache()
    
    def add_edge(self, from_node: str, to_node: str, cost: int):
        """
        Agregar una arista entre dos nodos con un costo específico.
        Crea automáticamente los nodos si no existen.
        """
        # Asegurar que los nodos existen
        self.add_node(from_node)
        self.add_node(to_node)
        
        # Agregar arista bidireccional (grafo no dirigido)
        self._add_directed_edge(from_node, to_node, cost)
        self._add_directed_edge(to_node, from_node, cost)
        
        self._clear_cache()
    
    def _add_directed_edge(self, from_node: str, to_node: str, cost: int):
        """Agregar arista dirigida"""
        # Remover arista existente si existe
        self.graph[from_node] = [(neighbor, c) for neighbor, c in self.graph[from_node] 
                                if neighbor != to_node]
        # Agregar nueva arista
        self.graph[from_node].append((to_node, cost))
    
    def remove_edge(self, from_node: str, to_node: str):
        """Remover arista entre dos nodos"""
        if from_node in self.graph:
            self.graph[from_node] = [(neighbor, cost) for neighbor, cost in self.graph[from_node]
                                   if neighbor != to_node]
        if to_node in self.graph:
            self.graph[to_node] = [(neighbor, cost) for neighbor, cost in self.graph[to_node]
                                 if neighbor != from_node]
        self._clear_cache()
    
    def update_edge_cost(self, from_node: str, to_node: str, new_cost: int):
        """Actualizar el costo de una arista existente"""
        if from_node in self.graph and to_node in self.graph:
            self.add_edge(from_node, to_node, new_cost)
    
    def _clear_cache(self):
        """Limpiar cache de rutas calculadas"""
        self.routes_cache = {}
    
    def dijkstra(self, start_node: str) -> Dict[str, Dict[str, any]]:
        """
        Ejecutar algoritmo de Dijkstra desde un nodo origen.
        
        Returns:
            Dict con formato: {
                nodo_destino: {
                    'distance': costo_total,
                    'path': [nodo1, nodo2, ...],
                    'next_hop': primer_nodo_en_el_camino,
                    'reachable': True/False
                }
            }
        """
        if start_node not in self.graph:
            return {}
        
        # Verificar cache
        if start_node in self.routes_cache:
            return self.routes_cache[start_node].copy()
        
        self.calculations_count += 1
        
        # Inicialización
        distances = {node: math.inf for node in self.graph}
        distances[start_node] = 0
        
        # Para reconstruir el camino
        previous = {node: None for node in self.graph}
        
        # Cola de prioridad: (distancia, nodo)
        priority_queue = [(0, start_node)]
        
        # Nodos visitados
        visited = set()
        
        while priority_queue:
            current_distance, current_node = heapq.heappop(priority_queue)
            
            # Si ya visitamos este nodo, continuar
            if current_node in visited:
                continue
            
            # Marcar como visitado
            visited.add(current_node)
            
            # Explorar vecinos
            for neighbor, edge_cost in self.graph[current_node]:
                if neighbor in visited:
                    continue
                
                # Calcular nueva distancia
                new_distance = current_distance + edge_cost
                
                # Si encontramos un camino mejor
                if new_distance < distances[neighbor]:
                    distances[neighbor] = new_distance
                    previous[neighbor] = current_node
                    heapq.heappush(priority_queue, (new_distance, neighbor))
        
        # Construir tabla de resultados
        results = {}
        for node in self.graph:
            if node == start_node:
                continue
            
            if distances[node] == math.inf:
                # Nodo no alcanzable
                results[node] = {
                    'distance': math.inf,
                    'path': [],
                    'next_hop': None,
                    'reachable': False
                }
            else:
                # Reconstruir camino
                path = self._reconstruct_path(previous, start_node, node)
                next_hop = path[1] if len(path) > 1 else node
                
                results[node] = {
                    'distance': distances[node],
                    'path': path,
                    'next_hop': next_hop,
                    'reachable': True
                }
        
        # Guardar en cache
        self.routes_cache[start_node] = results.copy()
        
        return results
    
    def _reconstruct_path(self, previous: Dict[str, str], start: str, end: str) -> List[str]:
        """Reconstruir el camino desde start hasta end usando el diccionario previous"""
        path = []
        current = end
        
        while current is not None:
            path.append(current)
            current = previous[current]
        
        path.reverse()
        return path
    
    def get_shortest_path(self, start_node: str, end_node: str) -> Tuple[List[str], int]:
        """
        Obtener el camino más corto entre dos nodos específicos.
        
        Returns:
            (camino, costo_total) o ([], inf) si no hay camino
        """
        routes = self.dijkstra(start_node)
        
        if end_node not in routes or not routes[end_node]['reachable']:
            return [], math.inf
        
        return routes[end_node]['path'], routes[end_node]['distance']
    
    def get_next_hop(self, start_node: str, destination: str) -> Optional[str]:
        """Obtener el siguiente salto para llegar a un destino"""
        routes = self.dijkstra(start_node)
        
        if destination not in routes or not routes[destination]['reachable']:
            return None
        
        return routes[destination]['next_hop']
    
    def get_distance(self, start_node: str, destination: str) -> int:
        """Obtener la distancia más corta a un destino"""
        routes = self.dijkstra(start_node)
        
        if destination not in routes or not routes[destination]['reachable']:
            return math.inf
        
        return routes[destination]['distance']
    
    def is_reachable(self, start_node: str, destination: str) -> bool:
        """Verificar si un destino es alcanzable desde el origen"""
        routes = self.dijkstra(start_node)
        return destination in routes and routes[destination]['reachable']
    
    def get_routing_table(self, start_node: str) -> Dict[str, Dict[str, any]]:
        """
        Obtener tabla de ruteo completa desde un nodo origen.
        Compatible con el formato usado en LSR.
        """
        routes = self.dijkstra(start_node)
        routing_table = {}
        
        for destination, route_info in routes.items():
            if route_info['reachable']:
                routing_table[destination] = {
                    'next_hop': route_info['next_hop'],
                    'cost': route_info['distance']
                }
        
        return routing_table
    
    def load_topology(self, topology: Dict[str, Dict[str, int]]):
        """
        Cargar topología desde un diccionario.
        
        Formato esperado:
        {
            'nodo_A': {'nodo_B': costo, 'nodo_C': costo},
            'nodo_B': {'nodo_A': costo, 'nodo_D': costo},
            ...
        }
        """
        self.graph = {}
        self._clear_cache()
        
        # Agregar todos los nodos primero
        for node in topology:
            self.add_node(node)
        
        # Agregar aristas
        for from_node, neighbors in topology.items():
            for to_node, cost in neighbors.items():
                self._add_directed_edge(from_node, to_node, cost)
    
    def get_topology(self) -> Dict[str, Dict[str, int]]:
        """Obtener la topología actual como diccionario"""
        topology = {}
        for node, edges in self.graph.items():
            topology[node] = {neighbor: cost for neighbor, cost in edges}
        return topology
    
    def get_nodes(self) -> List[str]:
        """Obtener lista de todos los nodos"""
        return list(self.graph.keys())
    
    def get_neighbors(self, node: str) -> List[str]:
        """Obtener lista de vecinos de un nodo"""
        if node not in self.graph:
            return []
        return [neighbor for neighbor, _ in self.graph[node]]
    
    def get_stats(self) -> Dict[str, any]:
        """Obtener estadísticas del algoritmo"""
        return {
            'nodes_count': len(self.graph),
            'edges_count': sum(len(edges) for edges in self.graph.values()) // 2,  # Dividir por 2 porque son bidireccionales
            'calculations_performed': self.calculations_count,
            'cached_routes': len(self.routes_cache)
        }
    
    def print_graph(self):
        """Imprimir representación del grafo"""
        print("Grafo actual:")
        for node, edges in self.graph.items():
            neighbors = [f"{neighbor}({cost})" for neighbor, cost in edges]
            print(f"  {node}: {neighbors}")
    
    def print_routing_table(self, start_node: str):
        """Imprimir tabla de ruteo para un nodo"""
        if start_node not in self.graph:
            print(f"Nodo {start_node} no existe en el grafo")
            return
        
        routes = self.dijkstra(start_node)
        print(f"\nTabla de ruteo para {start_node}:")
        print("Destino\t\tNext Hop\tCosto\tCamino Completo")
        print("-" * 60)
        
        for destination, route_info in routes.items():
            if route_info['reachable']:
                path_str = " -> ".join(route_info['path'])
                print(f"{destination}\t\t{route_info['next_hop']}\t\t{route_info['distance']}\t{path_str}")
            else:
                print(f"{destination}\t\t-\t\t∞\tNo alcanzable")

