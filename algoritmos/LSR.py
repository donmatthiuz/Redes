import time
import json
from typing import Dict, List, Set, Tuple, Optional
from algoritmos.Flodding import Flooding
from algoritmos.DJstra import SolveDjstra
from connection.Red import Red

class LSR:
    def __init__(self, node_id: str, neighbors: Dict[str, int]):

        self.node_id = node_id
        self.neighbors = neighbors  
        self.link_state_db = {}  
        self.sequence_number = 0
        self.routing_table = {} 
        
        self.flooding = Flooding(node_id, list(neighbors.keys()))
        
        self.lsp_history = set()
        
        self.last_topology_update = 0
        
        print(f"[LSR-{self.node_id}] Inicializado con vecinos: {neighbors}")
    
    def create_lsp(self) -> dict:
        self.sequence_number += 1
        
        lsp = {
            "proto": "lsr",
            "type": "lsp",
            "from": self.node_id,
            "sequence": self.sequence_number,
            "timestamp": time.time(),
            "neighbors": self.neighbors, 
            "ttl": 10
        }
        
        lsp_id = f"{self.node_id}-{self.sequence_number}"
        self.link_state_db[self.node_id] = {
            "neighbors": self.neighbors.copy(),
            "sequence": self.sequence_number,
            "timestamp": time.time()
        }
        
        print(f"[LSR-{self.node_id}] LSP creado: seq={self.sequence_number}")
        return lsp
    
    def process_lsp(self, lsp: dict) -> List[Tuple[str, dict]]:
        sender = lsp["from"]
        sequence = lsp["sequence"]
        lsp_id = f"{sender}-{sequence}"
        
        if lsp_id in self.lsp_history:
            return []
        
        if lsp["ttl"] <= 0:
            return []
        
        self.lsp_history.add(lsp_id)
        
        should_update = False
        if sender not in self.link_state_db:
            should_update = True
        elif sequence > self.link_state_db[sender]["sequence"]:
            should_update = True
        
        if should_update:
            self.link_state_db[sender] = {
                "neighbors": lsp["neighbors"],
                "sequence": sequence,
                "timestamp": lsp["timestamp"]
            }
            
            print(f"[LSR-{self.node_id}] LSP actualizado de {sender}, seq={sequence}")
            self.last_topology_update = time.time()
            
            self.calculate_routes()
            
            forward_list = []
            lsp_copy = lsp.copy()
            lsp_copy["ttl"] -= 1
            
            for neighbor in self.neighbors:
                if neighbor != sender: 
                    forward_list.append((neighbor, lsp_copy))
            
            return forward_list
        
        return []
    
    def build_topology_graph(self) -> Tuple[Dict[str, int], List[List[int]]]:
        all_nodes = set([self.node_id])
        for node_data in self.link_state_db.values():
            for neighbor in node_data["neighbors"]:
                all_nodes.add(neighbor)
        
        nodes_list = sorted(list(all_nodes))
        node_to_index = {node: i for i, node in enumerate(nodes_list)}
        
        size = len(nodes_list)
        graph = [[float('inf')] * size for _ in range(size)]
        
        for i in range(size):
            graph[i][i] = 0
        
        for node, data in self.link_state_db.items():
            if node in node_to_index:
                node_idx = node_to_index[node]
                for neighbor, cost in data["neighbors"].items():
                    if neighbor in node_to_index:
                        neighbor_idx = node_to_index[neighbor]
                        graph[node_idx][neighbor_idx] = cost
        
        return node_to_index, graph
    
    def calculate_routes(self):
        if not self.link_state_db:
            return
        
        try:
            node_mapping, adj_matrix = self.build_topology_graph()
            
            if self.node_id not in node_mapping:
                return
            
            network = Red(len(node_mapping))
            network.graph = adj_matrix
            
            src_index = node_mapping[self.node_id]
            dijkstra_solver = SolveDjstra(network)
            distances, next_hops = self.dijkstra_with_path(adj_matrix, src_index)
            
            self.routing_table.clear()
            index_to_node = {i: node for node, i in node_mapping.items()}
            
            for dest_idx, distance in enumerate(distances):
                if dest_idx != src_index and distance != float('inf'):
                    dest_node = index_to_node[dest_idx]
                    next_hop_idx = next_hops[dest_idx]
                    next_hop_node = index_to_node[next_hop_idx]
                    
                    self.routing_table[dest_node] = {
                        "next_hop": next_hop_node,
                        "cost": distance
                    }
            
            print(f"[LSR-{self.node_id}] Tabla de ruteo actualizada: {self.routing_table}")
            
        except Exception as e:
            print(f"[LSR-{self.node_id}] Error calculando rutas: {e}")
    
    def dijkstra_with_path(self, graph: List[List[int]], src: int) -> Tuple[List[int], List[int]]:
        V = len(graph)
        dist = [float('inf')] * V
        dist[src] = 0
        spt_set = [False] * V
        next_hop = [-1] * V
        
        next_hop[src] = src
        
        for _ in range(V):
            min_dist = float('inf')
            u = -1
            for v in range(V):
                if not spt_set[v] and dist[v] < min_dist:
                    min_dist = dist[v]
                    u = v
            
            if u == -1: 
                break
                
            spt_set[u] = True
            
            for v in range(V):
                if (not spt_set[v] and 
                    graph[u][v] != float('inf') and 
                    dist[u] + graph[u][v] < dist[v]):
                    
                    dist[v] = dist[u] + graph[u][v]
                    
                    if u == src:
                        next_hop[v] = v 
                    else:
                        next_hop[v] = next_hop[u]  
        
        return dist, next_hop
    
    def get_next_hop(self, destination: str) -> Optional[str]:
        if destination in self.routing_table:
            return self.routing_table[destination]["next_hop"]
        return None
    
    def should_send_lsp(self) -> bool:
        current_time = time.time()
        if not hasattr(self, 'last_lsp_time'):
            self.last_lsp_time = 0
        
        return (current_time - self.last_lsp_time) > 30
    
    def update_neighbor_cost(self, neighbor: str, new_cost: int):
        if neighbor in self.neighbors:
            old_cost = self.neighbors[neighbor]
            self.neighbors[neighbor] = new_cost
            print(f"[LSR-{self.node_id}] Costo a {neighbor} cambió: {old_cost} → {new_cost}")
            
            self.last_lsp_time = 0
    
    def remove_neighbor(self, neighbor: str):
        if neighbor in self.neighbors:
            del self.neighbors[neighbor]
            print(f"[LSR-{self.node_id}] Vecino {neighbor} eliminado")
            
            self.flooding.neighbors = list(self.neighbors.keys())
            
            self.last_lsp_time = 0
    
    def add_neighbor(self, neighbor: str, cost: int):
        self.neighbors[neighbor] = cost
        print(f"[LSR-{self.node_id}] Nuevo vecino {neighbor} agregado con costo {cost}")
        
        self.flooding.neighbors = list(self.neighbors.keys())
        
        self.last_lsp_time = 0
    
    def get_routing_table(self) -> Dict:
        return self.routing_table.copy()
    
    def get_topology_info(self) -> Dict:
        return {
            "link_state_db": self.link_state_db.copy(),
            "known_nodes": list(self.link_state_db.keys()),
            "last_update": self.last_topology_update
        }