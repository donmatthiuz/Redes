import time
import json
from typing import Dict, List, Set, Tuple, Optional
from algoritmos.DJstra import SolveDjstra
from connection.Red import Red

class LSR:
    """
    Link State Routing - Implementación mejorada para integración con NodoRedisSimple
    """
    
    def __init__(self, node_id: str, neighbors: Dict[str, int]):
        """
        Inicializar LSR
        
        Args:
            node_id: Identificador del nodo
            neighbors: Diccionario {neighbor_id: cost}
        """
        self.node_id = node_id
        self.neighbors = neighbors.copy()  # neighbor_id -> cost
        self.link_state_db = {}  # node_id -> {neighbors, sequence, timestamp}
        self.sequence_number = 0
        self.routing_table = {}  # destination -> {next_hop, cost}
        
        # Control de duplicados y TTL
        self.lsp_history = set()  # Almacenar IDs de LSPs ya procesados
        
        # Timestamps para control de tiempo
        self.last_topology_update = 0
        self.last_lsp_time = 0
        
        # Inicializar con mi propia información en la base de datos
        self.link_state_db[self.node_id] = {
            "neighbors": self.neighbors.copy(),
            "sequence": 0,
            "timestamp": time.time()
        }
        
        print(f"[LSR-{self.node_id}] Inicializado con vecinos: {neighbors}")
        print(f"[LSR-{self.node_id}] Base de datos inicial: {self.link_state_db}")
    
    def create_lsp(self) -> dict:
        """
        Crear Link State Packet con el formato estándar de mensajes
        
        Returns:
            dict: LSP formateado para envío
        """
        self.sequence_number += 1
        current_time = time.time()
        
        lsp = {
            "proto": "lsr",
            "type": "lsp",
            "from": self.node_id,
            "to": "broadcast",  # LSPs son broadcast
            "sequence": self.sequence_number,
            "timestamp": current_time,
            "neighbors": self.neighbors.copy(),  # Estado actual de mis enlaces
            "ttl": 10,  # TTL para evitar loops infinitos
            "headers": [self.node_id],  # Header con mi ID para tracking
            "payload": f"LSP from {self.node_id} seq={self.sequence_number}"
        }
        
        # Actualizar mi entrada en la base de datos
        self.link_state_db[self.node_id] = {
            "neighbors": self.neighbors.copy(),
            "sequence": self.sequence_number,
            "timestamp": current_time
        }
        
        self.last_lsp_time = current_time
        print(f"[LSR-{self.node_id}] LSP creado con secuencia={self.sequence_number}, vecinos={self.neighbors}")
        
        return lsp
    
    def process_lsp(self, lsp: dict) -> List[Tuple[str, dict]]:
        """
        Procesar LSP recibido y determinar reenvíos necesarios
        
        Args:
            lsp: LSP recibido
            
        Returns:
            List[Tuple[str, dict]]: Lista de (neighbor_id, lsp_to_forward)
        """
        sender = lsp.get("from", "")
        sequence = lsp.get("sequence", 0)
        timestamp = lsp.get("timestamp", time.time())
        neighbors_info = lsp.get("neighbors", {})
        ttl = lsp.get("ttl", 0)
        
        # Crear ID único para este LSP
        lsp_id = f"{sender}-{sequence}"
        
        print(f"[LSR-{self.node_id}] Procesando LSP de {sender}, seq={sequence}, TTL={ttl}")
        
        # Verificar duplicados
        if lsp_id in self.lsp_history:
            print(f"[LSR-{self.node_id}] LSP duplicado {lsp_id}, ignorando")
            return []
        
        # Verificar TTL
        if ttl <= 0:
            print(f"[LSR-{self.node_id}] LSP con TTL=0, descartando")
            return []
        
        # Marcar como procesado
        self.lsp_history.add(lsp_id)
        
        # Determinar si necesitamos actualizar nuestra base de datos
        should_update = False
        update_reason = ""
        
        if sender not in self.link_state_db:
            should_update = True
            update_reason = "nuevo nodo"
        elif sequence > self.link_state_db[sender]["sequence"]:
            should_update = True
            update_reason = f"secuencia más reciente ({sequence} > {self.link_state_db[sender]['sequence']})"
        elif sequence < self.link_state_db[sender]["sequence"]:
            print(f"[LSR-{self.node_id}] LSP obsoleto de {sender}, seq={sequence} < {self.link_state_db[sender]['sequence']}")
            return []  # No reenviar LSPs obsoletos
        
        forward_list = []
        
        if should_update:
            # Actualizar base de datos
            old_neighbors = self.link_state_db.get(sender, {}).get("neighbors", {})
            self.link_state_db[sender] = {
                "neighbors": neighbors_info.copy(),
                "sequence": sequence,
                "timestamp": timestamp
            }
            
            print(f"[LSR-{self.node_id}] Base de datos actualizada: {sender} -> {update_reason}")
            print(f"[LSR-{self.node_id}] Vecinos de {sender}: {old_neighbors} -> {neighbors_info}")
            
            self.last_topology_update = time.time()
            
            # Recalcular rutas con la nueva información
            self.calculate_routes()
            
            # Preparar LSP para reenvío (decrementar TTL)
            forward_lsp = lsp.copy()
            forward_lsp["ttl"] = ttl - 1
            
            # Reenviar a todos los vecinos excepto el origen
            for neighbor_id in self.neighbors.keys():
                if neighbor_id != sender:  # No reenviar al origen
                    forward_list.append((neighbor_id, forward_lsp))
            
            print(f"[LSR-{self.node_id}] LSP será reenviado a {len(forward_list)} vecinos")
        
        else:
            print(f"[LSR-{self.node_id}] LSP de {sender} no requiere actualización")
        
        return forward_list
    
    def build_topology_graph(self) -> Tuple[Dict[str, int], List[List[int]]]:
        """
        Construir grafo de la topología conocida para Dijkstra
        
        Returns:
            Tuple[Dict[str, int], List[List[int]]]: (node_mapping, adjacency_matrix)
        """
        # Obtener todos los nodos conocidos
        all_nodes = set([self.node_id])
        for node_data in self.link_state_db.values():
            for neighbor in node_data["neighbors"].keys():
                all_nodes.add(neighbor)
        
        # Crear mapeo ordenado
        nodes_list = sorted(list(all_nodes))
        node_to_index = {node: i for i, node in enumerate(nodes_list)}
        
        # Crear matriz de adyacencia
        size = len(nodes_list)
        graph = [[float('inf')] * size for _ in range(size)]
        
        # Distancia a sí mismo es 0
        for i in range(size):
            graph[i][i] = 0
        
        # Llenar matriz con costos conocidos
        for node, data in self.link_state_db.items():
            if node not in node_to_index:
                continue
                
            node_idx = node_to_index[node]
            neighbors = data["neighbors"]
            
            for neighbor, cost in neighbors.items():
                if neighbor in node_to_index:
                    neighbor_idx = node_to_index[neighbor]
                    graph[node_idx][neighbor_idx] = cost
        
        print(f"[LSR-{self.node_id}] Grafo construido: {len(nodes_list)} nodos")
        print(f"[LSR-{self.node_id}] Nodos: {nodes_list}")
        
        return node_to_index, graph
    
    def dijkstra_with_path(self, graph: List[List[int]], src: int) -> Tuple[List[int], List[int]]:
        """
        Algoritmo de Dijkstra modificado que también devuelve next-hops
        
        Args:
            graph: Matriz de adyacencia
            src: Índice del nodo fuente
            
        Returns:
            Tuple[List[int], List[int]]: (distances, next_hops)
        """
        V = len(graph)
        dist = [float('inf')] * V
        dist[src] = 0
        spt_set = [False] * V  # Shortest Path Tree set
        next_hop = [-1] * V
        
        # El next-hop para el nodo fuente es él mismo
        next_hop[src] = src
        
        for _ in range(V):
            # Encontrar vértice con distancia mínima no procesado
            min_dist = float('inf')
            u = -1
            
            for v in range(V):
                if not spt_set[v] and dist[v] < min_dist:
                    min_dist = dist[v]
                    u = v
            
            if u == -1:  # No hay más nodos alcanzables
                break
                
            spt_set[u] = True
            
            # Actualizar distancias de los vecinos del vértice seleccionado
            for v in range(V):
                if (not spt_set[v] and 
                    graph[u][v] != float('inf') and 
                    dist[u] + graph[u][v] < dist[v]):
                    
                    dist[v] = dist[u] + graph[u][v]
                    
                    # Determinar next-hop
                    if u == src:
                        # Vecino directo del origen
                        next_hop[v] = v
                    else:
                        # Heredar next-hop del predecesor
                        next_hop[v] = next_hop[u]
        
        return dist, next_hop
    
    def calculate_routes(self):
        """
        Calcular tabla de ruteo usando Dijkstra sobre la topología conocida
        """
        if not self.link_state_db:
            print(f"[LSR-{self.node_id}] No hay información de topología para calcular rutas")
            return
        
        try:
            # Construir grafo
            node_mapping, adj_matrix = self.build_topology_graph()
            
            if self.node_id not in node_mapping:
                print(f"[LSR-{self.node_id}] No se encontró en el mapeo de nodos")
                return
            
            # Ejecutar Dijkstra
            src_index = node_mapping[self.node_id]
            distances, next_hops = self.dijkstra_with_path(adj_matrix, src_index)
            
            # Construir tabla de ruteo
            self.routing_table.clear()
            index_to_node = {i: node for node, i in node_mapping.items()}
            
            routes_found = 0
            for dest_idx, distance in enumerate(distances):
                if dest_idx != src_index and distance != float('inf'):
                    dest_node = index_to_node[dest_idx]
                    next_hop_idx = next_hops[dest_idx]
                    next_hop_node = index_to_node[next_hop_idx]
                    
                    self.routing_table[dest_node] = {
                        "next_hop": next_hop_node,
                        "cost": distance
                    }
                    routes_found += 1
            
            print(f"[LSR-{self.node_id}] Tabla de ruteo recalculada: {routes_found} rutas")
            for dest, route_info in self.routing_table.items():
                print(f"[LSR-{self.node_id}]   {dest} -> next_hop: {route_info['next_hop']}, cost: {route_info['cost']}")
            
        except Exception as e:
            print(f"[LSR-{self.node_id}] Error calculando rutas: {e}")
            import traceback
            traceback.print_exc()
    
    def get_next_hop(self, destination: str) -> Optional[str]:
        """
        Obtener el siguiente salto para un destino
        
        Args:
            destination: ID del nodo destino
            
        Returns:
            str|None: ID del siguiente nodo, o None si no hay ruta
        """
        route_info = self.routing_table.get(destination)
        if route_info:
            return route_info["next_hop"]
        return None
    
    def get_route_cost(self, destination: str) -> Optional[int]:
        """
        Obtener el costo de la ruta a un destino
        
        Args:
            destination: ID del nodo destino
            
        Returns:
            int|None: Costo de la ruta, o None si no hay ruta
        """
        route_info = self.routing_table.get(destination)
        if route_info:
            return route_info["cost"]
        return None
    
    def should_send_lsp(self) -> bool:
        """
        Determinar si es tiempo de enviar un nuevo LSP
        
        Returns:
            bool: True si debe enviarse LSP
        """
        current_time = time.time()
        # Enviar LSP cada 30 segundos o si es el primer LSP
        return (current_time - self.last_lsp_time) > 30
    
    def update_neighbor_cost(self, neighbor: str, new_cost: int) -> bool:
        """
        Actualizar el costo hacia un vecino
        
        Args:
            neighbor: ID del vecino
            new_cost: Nuevo costo del enlace
            
        Returns:
            bool: True si hubo cambio
        """
        if neighbor in self.neighbors:
            old_cost = self.neighbors[neighbor]
            if old_cost != new_cost:
                self.neighbors[neighbor] = new_cost
                print(f"[LSR-{self.node_id}] Costo a {neighbor} actualizado: {old_cost} -> {new_cost}")
                
                # Actualizar mi entrada en la base de datos
                self.link_state_db[self.node_id]["neighbors"] = self.neighbors.copy()
                self.link_state_db[self.node_id]["timestamp"] = time.time()
                
                # Forzar envío de nuevo LSP
                self.last_lsp_time = 0
                return True
        return False
    
    def remove_neighbor(self, neighbor: str) -> bool:
        """
        Eliminar un vecino
        
        Args:
            neighbor: ID del vecino a eliminar
            
        Returns:
            bool: True si se eliminó
        """
        if neighbor in self.neighbors:
            del self.neighbors[neighbor]
            print(f"[LSR-{self.node_id}] Vecino {neighbor} eliminado")
            
            # Actualizar base de datos
            self.link_state_db[self.node_id]["neighbors"] = self.neighbors.copy()
            self.link_state_db[self.node_id]["timestamp"] = time.time()
            
            # Forzar nuevo LSP
            self.last_lsp_time = 0
            return True
        return False
    
    def add_neighbor(self, neighbor: str, cost: int) -> bool:
        """
        Agregar un nuevo vecino
        
        Args:
            neighbor: ID del nuevo vecino
            cost: Costo del enlace
            
        Returns:
            bool: True si se agregó
        """
        if neighbor not in self.neighbors:
            self.neighbors[neighbor] = cost
            print(f"[LSR-{self.node_id}] Nuevo vecino {neighbor} agregado con costo {cost}")
            
            # Actualizar base de datos
            self.link_state_db[self.node_id]["neighbors"] = self.neighbors.copy()
            self.link_state_db[self.node_id]["timestamp"] = time.time()
            
            # Forzar nuevo LSP
            self.last_lsp_time = 0
            return True
        return False
    
    def get_routing_table(self) -> Dict[str, Dict[str, any]]:
        """
        Obtener copia de la tabla de ruteo
        
        Returns:
            Dict: Copia de la tabla de ruteo
        """
        return self.routing_table.copy()
    
    def get_topology_info(self) -> Dict[str, any]:
        """
        Obtener información completa de la topología conocida
        
        Returns:
            Dict: Información de topología
        """
        return {
            "link_state_db": {k: v.copy() for k, v in self.link_state_db.items()},
            "known_nodes": list(self.link_state_db.keys()),
            "total_nodes": len(self.link_state_db),
            "last_update": self.last_topology_update,
            "my_neighbors": self.neighbors.copy(),
            "routing_table_size": len(self.routing_table)
        }
    
    def get_statistics(self) -> Dict[str, any]:
        """
        Obtener estadísticas del protocolo LSR
        
        Returns:
            Dict: Estadísticas
        """
        current_time = time.time()
        return {
            "node_id": self.node_id,
            "sequence_number": self.sequence_number,
            "known_nodes": len(self.link_state_db),
            "direct_neighbors": len(self.neighbors),
            "routing_table_entries": len(self.routing_table),
            "lsp_history_size": len(self.lsp_history),
            "time_since_last_lsp": current_time - self.last_lsp_time,
            "time_since_last_topology_update": current_time - self.last_topology_update,
            "should_send_lsp": self.should_send_lsp()
        }
    
    def debug_print_state(self):
        """Imprimir estado completo para debugging"""
        print(f"\n=== DEBUG LSR {self.node_id} ===")
        print(f"Vecinos directos: {self.neighbors}")
        print(f"Base de datos de estados de enlace:")
        for node, data in self.link_state_db.items():
            print(f"  {node}: {data}")
        print(f"Tabla de ruteo:")
        for dest, route in self.routing_table.items():
            print(f"  {dest}: {route}")
        print(f"Estadísticas: {self.get_statistics()}")
        print("=" * 30)