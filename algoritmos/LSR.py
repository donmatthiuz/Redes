import time
import json
from typing import Dict, List, Set, Tuple, Optional
from algoritmos.DJstra import SolveDjstra
from connection.Red import Red
from connection.Mensajes import Messages
from algoritmos.TIPOS import ECHO, INFO, MENSAJE, HOLA


class LSR:
    """
    Link State Routing - Adaptado para NodoRedisFlooding
    """
    
    def __init__(self, node_id: str, topology: Dict[str, List[str]]):
        """
        Inicializar LSR
        
        Args:
            node_id: Identificador del nodo
            topology: Diccionario de topología {node_id: [neighbors]}
        """
        self.node_id = node_id
        self.topology = topology
        self.neighbors = topology.get(node_id, [])  # Lista de neighbor_ids
        self.neighbor_costs = {}  # neighbor_id -> cost (default 1)
        
        # Inicializar costos por defecto
        for neighbor in self.neighbors:
            self.neighbor_costs[neighbor] = 1
        
        self.link_state_db = {}  # node_id -> {neighbors, sequence, timestamp}
        self.sequence_number = 0
        self.routing_table = {}  # destination -> {next_hop, cost}
        
        # Control de duplicados - compatible con NodoRedisFlooding
        self.seen_messages = set()
        
        # Estadísticas compatibles con get_stats()
        self.stats = {
            "lsp_sent": 0,
            "lsp_received": 0, 
            "lsp_forwarded": 0,
            "duplicates_dropped": 0,
            "routes_calculated": 0,
            "messages_delivered": 0
        }
        
        # Timestamps
        self.last_topology_update = 0
        self.last_lsp_time = 0
        
        # Inicializar mi entrada en la base de datos
        self.link_state_db[self.node_id] = {
            "neighbors": self.neighbor_costs.copy(),
            "sequence": 0,
            "timestamp": time.time()
        }
        
        print(f"[LSR-{self.node_id}] Inicializado con vecinos: {self.neighbors}")
    
    def _get_header(self, msg, key, default=None):
        """Obtener valor de un header específico"""
        for header in msg.get("headers", []):
            if isinstance(header, dict) and key in header:
                return header[key]
        return default
    
    def _set_header(self, msg, key, value):
        """Establecer valor de un header"""
        headers = msg.get("headers", [])
        # Remover header existente
        headers = [h for h in headers if not (isinstance(h, dict) and key in h)]
        # Agregar nuevo header
        headers.append({key: value})
        msg["headers"] = headers
    
    def _generate_message_id(self, msg):
        """Generar ID único para el mensaje LSP"""
        mid = self._get_header(msg, "mid")
        if mid:
            return mid
        
        # Para LSP usar origen y secuencia
        src = msg.get("from", "unknown")
        payload = msg.get("payload", {})
        
        if isinstance(payload, dict) and payload.get("type") == "lsp":
            sequence = payload.get("sequence", 0)
            mid = f"{src}:lsp:{sequence}"
        else:
            mid = f"{src}:info:{int(time.time() * 1000000)}"
        
        self._set_header(msg, "mid", mid)
        return mid
    
    def is_duplicate(self, msg):
        """Verificar si el mensaje LSP ya fue procesado"""
        mid = self._generate_message_id(msg)
        
        if mid in self.seen_messages:
            self.stats["duplicates_dropped"] += 1
            return True
        
        self.seen_messages.add(mid)
        return False
    
    def should_forward(self, node, msg):
        """Determinar si el mensaje LSP debe ser reenviado"""
        # Verificar hops
        hops = msg.get("hops", 0)
        if hops <= 0:
            return False
        
        # Verificar que no vino de nosotros
        prev_hop = self._get_header(msg, "prev")
        if prev_hop == node.node_id:
            return False
        
        return True
    
    def create_lsp_message(self, to_addr):
        """Crear mensaje LSP usando Messages.create_lsp_message"""
        self.sequence_number += 1
        current_time = time.time()
        
        print("LSP", self.neighbor_costs.copy())
        # Usar el método específico de Messages
        lsp_msg = Messages.create_lsp_message(
            from_addr="",  # Se llenará en el nodo
            to_addr=to_addr,
            neighbors=self.neighbor_costs.copy(),
            seq_num=self.sequence_number,
            algorithm="lsr",
            hops=10
        )
        
        # Actualizar mi entrada en la base de datos
        self.link_state_db[self.node_id] = {
            "neighbors": self.neighbor_costs.copy(),
            "sequence": self.sequence_number,
            "timestamp": current_time
        }
        
        self.last_lsp_time = current_time
        self.stats["lsp_sent"] += 1
        
        return lsp_msg
    
    def forward_lsp(self, node, msg):
        """Reenviar LSP a todos los vecinos activos"""
        if not self.should_forward(node, msg):
            return 0
        
        # Preparar mensaje para reenvío
        forward_msg = dict(msg)
        forward_msg["hops"] = msg.get("hops", 0) - 1
        self._set_header(forward_msg, "prev", node.node_id)
        
        # Obtener vecino anterior para no reenviar
        prev_hop = self._get_header(msg, "prev")
        
        forwarded_count = 0
        current_time = time.time()
        
        for neighbor_id in node.neighbor_ids:
            # No reenviar al que nos envió el mensaje
            if neighbor_id == prev_hop:
                continue
            
            # Verificar si el vecino está activo
            if not node.is_neighbor_active(neighbor_id, current_time):
                continue
            
            # Enviar mensaje
            if node.send_to_neighbor(neighbor_id, forward_msg):
                forwarded_count += 1
                node.log_message(f"[LSR] LSP reenviado a {neighbor_id}")
        
        self.stats["lsp_forwarded"] += forwarded_count
        return forwarded_count
    
    def process_lsp(self, node, msg):
        """Procesar LSP recibido"""
        payload = msg.get("payload", {})
        if not isinstance(payload, dict) or payload.get("type") != "lsp":
            return
        
        sender = msg.get("from", "")
        sequence = payload.get("sequence", 0)
        neighbors_info = payload.get("neighbors", {})
        
        node.log_message(f"[LSR] Procesando LSP de {sender}, seq={sequence}")
        
        # Determinar si necesitamos actualizar
        should_update = False
        if sender not in self.link_state_db:
            should_update = True
        elif sequence > self.link_state_db[sender]["sequence"]:
            should_update = True
        elif sequence < self.link_state_db[sender]["sequence"]:
            node.log_message(f"[LSR] LSP obsoleto de {sender}")
            return
        
        if should_update:
            # Actualizar base de datos
            self.link_state_db[sender] = {
                "neighbors": neighbors_info.copy(),
                "sequence": sequence,
                "timestamp": time.time()
            }
            
            self.last_topology_update = time.time()
            node.log_message(f"[LSR] Base de datos actualizada para {sender}")
            
            # Recalcular rutas
            self.calculate_routes(node)
            
            # Reenviar LSP
            forwarded = self.forward_lsp(node, msg)
            if forwarded > 0:
                node.log_message(f"[LSR] LSP reenviado a {forwarded} vecinos")
    
    def build_dijkstra_network(self):
        """Construir red para usar con SolveDjstra"""
        # Obtener todos los nodos conocidos
        all_nodes = set([self.node_id])
        for node_data in self.link_state_db.values():
            for neighbor in node_data["neighbors"].keys():
                all_nodes.add(neighbor)
        
        # Crear mapeo
        nodes_list = sorted(list(all_nodes))
        self.node_to_index = {node: i for i, node in enumerate(nodes_list)}
        self.index_to_node = {i: node for node, i in self.node_to_index.items()}
        
        # Crear red
        size = len(nodes_list)
        red = Red(size)
        
        # Llenar con enlaces conocidos
        for node, data in self.link_state_db.items():
            if node not in self.node_to_index:
                continue
            
            node_idx = self.node_to_index[node]
            neighbors = data["neighbors"]
            
            for neighbor, cost in neighbors.items():
                if neighbor in self.node_to_index:
                    neighbor_idx = self.node_to_index[neighbor]
                    red.add_edge(node_idx, neighbor_idx, cost)
        
        return red
    
    def calculate_routes(self, node):
        """Calcular tabla de ruteo usando Dijkstra"""
        if not self.link_state_db:
            return
        
        try:
            # Construir red
            red = self.build_dijkstra_network()
            
            if self.node_id not in self.node_to_index:
                return
            
            # Ejecutar Dijkstra
            solver = SolveDjstra(red)
            src_index = self.node_to_index[self.node_id]
            routing_table_dijkstra = solver.get_routing_table(src_index)
            
            # Convertir a tabla de ruteo
            self.routing_table.clear()
            routes_found = 0
            
            for dest_idx, route_info in routing_table_dijkstra.items():
                if route_info['reachable']:
                    dest_node = self.index_to_node[dest_idx]
                    next_hop_node = self.index_to_node[route_info['next_hop']]
                    
                    self.routing_table[dest_node] = {
                        "next_hop": next_hop_node,
                        "cost": route_info['distance']
                    }
                    routes_found += 1
            
            self.stats["routes_calculated"] += 1
            node.log_message(f"[LSR-{self.node_id}] Calculadas {routes_found} rutas")
            
        except Exception as e:
            print(f"[LSR-{self.node_id}] Error calculando rutas: {e}")
    
    def process_message(self, node, msg):
        """Procesar mensaje - interfaz compatible con NodoRedisFlooding"""
        msg_type = msg.get("type", "")
        
        # Verificar duplicados primero
        if self.is_duplicate(msg):
            node.log_message(f"[LSR] Mensaje duplicado descartado")
            return
        
        # Procesar según tipo
        if msg_type in INFO:
            payload = msg.get("payload", {})
            if isinstance(payload, dict) and payload.get("type") == "lsp":
                self.process_lsp(node, msg)
            else:
                self._deliver_message(node, msg)
        else:
            # Otros mensajes se entregan normalmente
            to_addr = msg.get("to", "")
            if to_addr == node.my_address:
                self._deliver_message(node, msg)
            else:
                # Intentar ruteo usando LSR
                self._route_message(node, msg)
    
    def _route_message(self, node, msg):
        """Intentar rutear mensaje usando tabla LSR"""
        to_addr = msg.get("to", "")
        
        # Buscar destino en nombres
        dest_node = None
        for nid, addr in node.names.items():
            if addr == to_addr:
                dest_node = nid
                break
        
        if dest_node and dest_node in self.routing_table:
            next_hop = self.routing_table[dest_node]["next_hop"]
            node.log_message(f"[LSR] Ruteando a {dest_node} via {next_hop}")
            
            if node.send_to_neighbor(next_hop, msg):
                node.log_message(f"[LSR] Mensaje ruteado exitosamente")
            else:
                node.log_message(f"[LSR] Error ruteando mensaje")
        else:
            node.log_message(f"[LSR] No hay ruta a {dest_node}")
    
    def _deliver_message(self, node, msg):
        """Entregar mensaje al nodo local"""
        msg_type = msg.get("type", "")
        from_addr = msg.get("from", "")
        payload = msg.get("payload", "")
        
        self.stats["messages_delivered"] += 1
        
        if msg_type in MENSAJE:
            node.log_message(f"[LSR] MENSAJE RECIBIDO de {from_addr}: {msg}")
            print(f"[{node.node_id}] >>> MENSAJE: {payload}")
        elif msg_type in HOLA:
            node.handle_hello_received(msg)
        elif msg_type in ECHO:
            node.handle_echo_received(msg)
        elif msg_type in INFO:
            node.log_message(f"[LSR] INFO RECIBIDO de {from_addr}: {payload}")
    
    def should_send_lsp(self) -> bool:
        """Determinar si es tiempo de enviar LSP"""
        current_time = time.time()
        return (current_time - self.last_lsp_time) > 30
    
    def get_next_hop(self, destination: str) -> Optional[str]:
        """Obtener siguiente salto para un destino"""
        route_info = self.routing_table.get(destination)
        return route_info["next_hop"] if route_info else None
    
    def get_route_cost(self, destination: str) -> Optional[int]:
        """Obtener costo de ruta a destino"""
        route_info = self.routing_table.get(destination)
        return route_info["cost"] if route_info else None
    
    def update_neighbor_cost(self, neighbor: str, new_cost: int) -> bool:
        """Actualizar costo de vecino"""
        if neighbor in self.neighbor_costs:
            old_cost = self.neighbor_costs[neighbor]
            if old_cost != new_cost:
                self.neighbor_costs[neighbor] = new_cost
                print(f"[LSR-{self.node_id}] Costo a {neighbor}: {old_cost} -> {new_cost}")
                
                # Actualizar base de datos
                self.link_state_db[self.node_id]["neighbors"] = self.neighbor_costs.copy()
                self.link_state_db[self.node_id]["timestamp"] = time.time()
                
                # Forzar nuevo LSP
                self.last_lsp_time = 0
                return True
        return False
    
    def get_stats(self):
        """Obtener estadísticas - compatible con NodoRedisFlooding"""
        return dict(self.stats)
    
    def reset_stats(self):
        """Resetear estadísticas"""
        self.stats = {
            "lsp_sent": 0,
            "lsp_received": 0,
            "lsp_forwarded": 0,
            "duplicates_dropped": 0,
            "routes_calculated": 0,
            "messages_delivered": 0
        }
    
    def get_routing_table(self) -> Dict[str, Dict[str, any]]:
        """Obtener tabla de ruteo"""
        return self.routing_table.copy()
    
    def get_topology_info(self) -> Dict[str, any]:
        """Obtener información de topología"""
        return {
            "link_state_db": {k: v.copy() for k, v in self.link_state_db.items()},
            "known_nodes": list(self.link_state_db.keys()),
            "total_nodes": len(self.link_state_db),
            "routing_table_size": len(self.routing_table),
            "my_neighbors": self.neighbor_costs.copy()
        }