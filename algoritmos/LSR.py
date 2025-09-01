import time
import json
from typing import Dict, List, Set, Tuple, Optional
from algoritmos.DJstra import SolveDjstra
from connection.Red import Red
from connection.Mensajes import Messages
from algoritmos.TIPOS import ECHO, INFO, MENSAJE, HOLA


class LSR:
    
    def __init__(self, node, node_id: str, topology: Dict[str, List[str]], names: Dict[str, str]):
    
        self.node_id = node_id
        self.names = names
        self.nodo = node
        self.my_address = names.get(node_id)
        
        if not self.my_address:
            raise ValueError(f"No se encontró dirección para nodo {node_id}")
        
        # Convertir topología de IDs a direcciones
        self.neighbor_addresses = []
        neighbor_ids = topology.get(node_id, [])
        for neighbor_id in neighbor_ids:
            neighbor_addr = names.get(neighbor_id)
            if neighbor_addr:
                self.neighbor_addresses.append(neighbor_addr)
        
        # Costos usando direcciones
        self.neighbor_costs = {}  # address -> cost (default 1)
        
        # Inicializar costos por defecto
        for neighbor_addr in self.neighbor_addresses:
            self.neighbor_costs[neighbor_addr] = 1
        
        # Base de datos de estados de enlace usando direcciones
        self.link_state_db = {}  # address -> {neighbors, sequence, timestamp}
        self.sequence_number = 0
        self.routing_table = {}  # destination_address -> {next_hop_address, cost}
        
        # Control de duplicados
        self.seen_messages = set()
        
        # Estadísticas
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
        
        # Inicializar mi entrada en la base de datos usando mi dirección
        self.link_state_db[self.my_address] = {
            "neighbors": self.neighbor_costs.copy(),
            "sequence": 0,
            "timestamp": time.time()
        }
        
        self.nodo.log_message(f"[LSR-{self.node_id}] Inicializado con dirección {self.my_address}")
        self.nodo.log_message(f"[LSR-{self.node_id}] Vecinos: {self.neighbor_addresses}")
    
    def _get_header(self, msg, key, default=None):
        """Obtener valor de un header específico"""
        headers = msg.get("headers", {})
        if isinstance(headers, dict):
            return headers.get(key, default)
        # Si headers es una lista (formato anterior)
        for header in headers if isinstance(headers, list) else []:
            if isinstance(header, dict) and key in header:
                return header[key]
        return default
    
    def _set_header(self, msg, key, value):
        """Establecer valor de un header"""
        if "headers" not in msg:
            msg["headers"] = {}
        
        if isinstance(msg["headers"], dict):
            msg["headers"][key] = value
        else:
            # Convertir formato lista a dict si es necesario
            headers_dict = {}
            for h in msg.get("headers", []):
                if isinstance(h, dict):
                    headers_dict.update(h)
            headers_dict[key] = value
            msg["headers"] = headers_dict
    
    def _generate_message_id(self, msg):
        """Generar ID único para el mensaje LSP"""
        mid = self._get_header(msg, "mid")
        if mid:
            return mid
        
        # Para LSP usar origen y secuencia
        src = msg.get("from", "unknown")
        
        # Para mensajes LSP usar secuencia
        if msg.get("seq_num") is not None:
            sequence = msg.get("seq_num", 0)
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
        if prev_hop == self.my_address:
            return False
        
        return True
    
    def create_lsp_message(self, to_addr):
        """Crear mensaje LSP en el nuevo formato"""
        self.sequence_number += 1
        current_time = time.time()
        
        # Crear mensaje en el formato especificado
        lsp_msg = {
            'type': 'info',
            'from': self.my_address,
            'to': to_addr,
            'hops': 10,
            'headers': {'alg': 'lsr'},
            'seq_num': self.sequence_number,
            'neighbors': self.neighbor_costs.copy()
        }
        
        # Actualizar mi entrada en la base de datos
        self.link_state_db[self.my_address] = {
            "neighbors": self.neighbor_costs.copy(),
            "sequence": self.sequence_number,
            "timestamp": current_time
        }
        
        self.last_lsp_time = current_time
        self.stats["lsp_sent"] += 1
        
        self.nodo.log_message(f"[LSR-{self.node_id}] LSP creado: seq={self.sequence_number}, vecinos={self.neighbor_costs}")
        
        return lsp_msg
    
    def forward_lsp(self, node, msg):
        """Reenviar LSP a todos los vecinos activos"""
        if not self.should_forward(node, msg):
            return 0
        
        # Preparar mensaje para reenvío
        forward_msg = dict(msg)
        forward_msg["hops"] = msg.get("hops", 0) - 1
        self._set_header(forward_msg, "prev", self.my_address)
        
        # Obtener vecino anterior para no reenviar
        prev_hop = self._get_header(msg, "prev")
        
        forwarded_count = 0
        current_time = time.time()
        
        # Reenviar a vecinos usando direcciones
        for neighbor_addr in self.neighbor_addresses:
            # No reenviar al que nos envió el mensaje
            if neighbor_addr == prev_hop:
                continue
            
            # Buscar neighbor_id correspondiente para verificar actividad
            neighbor_id = None
            for nid, addr in self.names.items():
                if addr == neighbor_addr:
                    neighbor_id = nid
                    break
            
            if not neighbor_id:
                continue
            
            # Verificar si el vecino está activo
            if not node.is_neighbor_active(neighbor_id, current_time):
                continue
            
            # Actualizar destino del mensaje
            forward_msg["to"] = neighbor_addr
            
            # Enviar mensaje
            if node.send_to_neighbor(neighbor_id, forward_msg):
                forwarded_count += 1
                node.log_message(f"[LSR] LSP reenviado a {neighbor_addr}")
        
        self.stats["lsp_forwarded"] += forwarded_count
        return forwarded_count
    
    def process_lsp(self, node, msg):
        """Procesar LSP recibido en el nuevo formato"""
        # El mensaje ya tiene neighbors y seq_num en el nivel superior
        sender_addr = msg.get("from", "")
        sequence = msg.get("seq_num", 0)
        neighbors_info = msg.get("neighbors", {})
        
        if not sender_addr or not isinstance(neighbors_info, dict):
            node.log_message(f"[LSR] LSP malformado de {sender_addr}")
            return
        
        node.log_message(f"[LSR] Procesando LSP de {sender_addr}, seq={sequence}")
        
        # Determinar si necesitamos actualizar
        should_update = False
        if sender_addr not in self.link_state_db:
            should_update = True
            node.log_message(f"[LSR] Nueva entrada para {sender_addr}")
        elif sequence > self.link_state_db[sender_addr]["sequence"]:
            should_update = True
            node.log_message(f"[LSR] Secuencia más nueva: {sequence} > {self.link_state_db[sender_addr]['sequence']}")
        elif sequence < self.link_state_db[sender_addr]["sequence"]:
            node.log_message(f"[LSR] LSP obsoleto de {sender_addr}")
            return
        else:
            node.log_message(f"[LSR] LSP duplicado de {sender_addr}")
            return
        
        if should_update:
            # Actualizar base de datos
            self.link_state_db[sender_addr] = {
                "neighbors": neighbors_info.copy(),
                "sequence": sequence,
                "timestamp": time.time()
            }
            
            self.stats["lsp_received"] += 1
            self.last_topology_update = time.time()
            node.log_message(f"[LSR] Base de datos actualizada para {sender_addr}")
            
            # Recalcular rutas
            self.calculate_routes(node)
            
            # Reenviar LSP
            forwarded = self.forward_lsp(node, msg)
            if forwarded > 0:
                node.log_message(f"[LSR] LSP reenviado a {forwarded} vecinos")
    
    def build_dijkstra_network(self):
        """Construir red para usar con SolveDjstra usando direcciones"""
        # Obtener todas las direcciones conocidas
        all_addresses = set([self.my_address])
        for addr_data in self.link_state_db.values():
            for neighbor_addr in addr_data["neighbors"].keys():
                all_addresses.add(neighbor_addr)
        
        # Crear mapeo
        addresses_list = sorted(list(all_addresses))
        self.addr_to_index = {addr: i for i, addr in enumerate(addresses_list)}
        self.index_to_addr = {i: addr for addr, i in self.addr_to_index.items()}
        
        # Crear red
        size = len(addresses_list)
        red = Red(size)
        
        # Llenar con enlaces conocidos
        for addr, data in self.link_state_db.items():
            if addr not in self.addr_to_index:
                continue
            
            addr_idx = self.addr_to_index[addr]
            neighbors = data["neighbors"]
            
            for neighbor_addr, cost in neighbors.items():
                if neighbor_addr in self.addr_to_index:
                    neighbor_idx = self.addr_to_index[neighbor_addr]
                    red.add_edge(addr_idx, neighbor_idx, cost)
        
        return red
    
    def calculate_routes(self, node):
        """Calcular tabla de ruteo usando Dijkstra con direcciones"""
        if not self.link_state_db:
            return
        
        try:
            # Construir red
            red = self.build_dijkstra_network()
            
            if self.my_address not in self.addr_to_index:
                return
            
            # Ejecutar Dijkstra
            solver = SolveDjstra(red)
            src_index = self.addr_to_index[self.my_address]
            routing_table_dijkstra = solver.get_routing_table(src_index)
            
            # Convertir a tabla de ruteo usando direcciones
            self.routing_table.clear()
            routes_found = 0
            
            for dest_idx, route_info in routing_table_dijkstra.items():
                if route_info['reachable']:
                    dest_addr = self.index_to_addr[dest_idx]
                    next_hop_addr = self.index_to_addr[route_info['next_hop']]
                    
                    # No agregar ruta a nosotros mismos
                    if dest_addr != self.my_address:
                        self.routing_table[dest_addr] = {
                            "next_hop": next_hop_addr,
                            "cost": route_info['distance']
                        }
                        routes_found += 1
            
            self.stats["routes_calculated"] += 1
            node.log_message(f"[LSR-{self.node_id}] Calculadas {routes_found} rutas")
            
        except Exception as e:
            self.nodo.log_message(f"[LSR-{self.node_id}] Error calculando rutas: {e}")
    
    def process_message(self, node, msg):
        """Procesar mensaje - interfaz compatible con NodoRedisFlooding"""
        msg_type = msg.get("type", "")
        
        # Verificar duplicados primero para LSPs
        if msg_type in INFO and msg.get("seq_num") is not None:
            if self.is_duplicate(msg):
                node.log_message(f"[LSR] LSP duplicado descartado")
                return
        
        # Procesar según tipo
        if msg_type in INFO:
            # Verificar si es un LSP (tiene seq_num y neighbors)
            if msg.get("seq_num") is not None and msg.get("neighbors") is not None:
                self.process_lsp(node, msg)
            else:
                self._deliver_message(node, msg)
        elif msg_type in MENSAJE:
            to_addr = msg.get("to", "")
            if to_addr == self.my_address:
                self._deliver_message(node, msg)
            else:
                # Intentar ruteo usando LSR
                self._route_message(node, msg)
        else:
            # Otros mensajes se entregan normalmente
            to_addr = msg.get("to", "")
            if to_addr == self.my_address:
                self._deliver_message(node, msg)
    
    def _route_message(self, node, msg):
        """Intentar rutear mensaje usando tabla LSR con direcciones"""
        to_addr = msg.get("to", "")
        
        if to_addr in self.routing_table:
            next_hop_addr = self.routing_table[to_addr]["next_hop"]
            
            # Encontrar neighbor_id correspondiente
            next_hop_id = None
            for nid, addr in self.names.items():
                if addr == next_hop_addr:
                    next_hop_id = nid
                    break
            
            if next_hop_id:
                node.log_message(f"[LSR] Ruteando a {to_addr} via {next_hop_addr}")
                
                if node.send_to_neighbor(next_hop_id, msg):
                    node.log_message(f"[LSR] Mensaje ruteado exitosamente")
                else:
                    node.log_message(f"[LSR] Error ruteando mensaje")
            else:
                node.log_message(f"[LSR] No se encontró ID para next_hop {next_hop_addr}")
        else:
            node.log_message(f"[LSR] No hay ruta a {to_addr}")
    
    def _deliver_message(self, node, msg):
        """Entregar mensaje al nodo local"""
        msg_type = msg.get("type", "")
        from_addr = msg.get("from", "")
        
        self.stats["messages_delivered"] += 1
        
        if msg_type in MENSAJE:
            payload = msg.get("payload", msg.get("data", ""))
            node.log_message(f"[LSR] MENSAJE RECIBIDO de {from_addr}: {msg}")
            print(f"[{self.node_id}] >>> MENSAJE: {payload}")
        elif msg_type in HOLA:
            node.handle_hello_received(msg)
        elif msg_type in ECHO:
            node.handle_echo_received(msg)
        elif msg_type in INFO:
            payload = msg.get("payload", msg.get("data", ""))
            node.log_message(f"[LSR] INFO RECIBIDO de {from_addr}: {payload}")
    
    def should_send_lsp(self) -> bool:
        """Determinar si es tiempo de enviar LSP"""
        current_time = time.time()
        return (current_time - self.last_lsp_time) > 30
    
    def get_next_hop(self, destination: str) -> Optional[str]:
        """Obtener siguiente salto para un destino (dirección)"""
        route_info = self.routing_table.get(destination)
        return route_info["next_hop"] if route_info else None
    
    def get_route_cost(self, destination: str) -> Optional[int]:
        """Obtener costo de ruta a destino (dirección)"""
        route_info = self.routing_table.get(destination)
        return route_info["cost"] if route_info else None
    
    def update_neighbor_cost(self, neighbor_addr: str, new_cost: int) -> bool:
        """Actualizar costo de vecino usando dirección"""
        if neighbor_addr in self.neighbor_costs:
            old_cost = self.neighbor_costs[neighbor_addr]
            if old_cost != new_cost:
                self.neighbor_costs[neighbor_addr] = new_cost
                print(f"[LSR-{self.node_id}] Costo a {neighbor_addr}: {old_cost} -> {new_cost}")
                
                # Actualizar base de datos
                self.link_state_db[self.my_address]["neighbors"] = self.neighbor_costs.copy()
                self.link_state_db[self.my_address]["timestamp"] = time.time()
                
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
        """Obtener tabla de ruteo con direcciones"""
        return self.routing_table.copy()
    
    def get_topology_info(self) -> Dict[str, any]:
        """Obtener información de topología con direcciones"""
        return {
            "link_state_db": {k: v.copy() for k, v in self.link_state_db.items()},
            "known_addresses": list(self.link_state_db.keys()),
            "total_nodes": len(self.link_state_db),
            "routing_table_size": len(self.routing_table),
            "my_neighbors": self.neighbor_costs.copy(),
            "my_address": self.my_address
        }