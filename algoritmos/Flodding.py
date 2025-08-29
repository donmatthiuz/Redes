import time
import json
from connection.Mensajes import Messages
from algoritmos.TIPOS import ECHO, INFO, MENSAJE, HOLA

class Flooding:
    """Algoritmo de Flooding para el protocolo de red"""
    
    def __init__(self):
        self.seen_messages = set()  # Control de duplicados
        self.stats = {
            "messages_flooded": 0,
            "duplicates_dropped": 0,
            "messages_delivered": 0
        }
    
    def _get_header(self, msg, key, default=None):
        """Obtener valor de un header específico"""
        for header in msg.get("headers", []):
            if key in header:
                return header[key]
        return default
    
    def _set_header(self, msg, key, value):
        """Establecer valor de un header"""
        headers = msg.get("headers", [])
        # Remover header existente si existe
        headers = [h for h in headers if key not in h]
        # Agregar nuevo header
        headers.append({key: value})
        msg["headers"] = headers
    
    def _generate_message_id(self, msg):
        """Generar ID único para el mensaje"""
        mid = self._get_header(msg, "mid")
        if mid:
            return mid
        
        # Generar MID basado en origen y timestamp
        src = msg.get("from", "unknown")
        payload = msg.get("payload", {})
        
        # Buscar secuencia en payload
        seq = None
        if isinstance(payload, dict):
            seq = payload.get("seq") or payload.get("id")
        
        if seq is None:
            seq = int(time.time() * 1_000_000)  # Microsegundos como seq
        
        mid = f"{src}:{seq}"
        self._set_header(msg, "mid", mid)
        return mid
    
    def is_duplicate(self, msg):
        """Verificar si el mensaje ya fue procesado"""
        mid = self._generate_message_id(msg)
        
        if mid in self.seen_messages:
            self.stats["duplicates_dropped"] += 1
            return True
        
        self.seen_messages.add(mid)
        return False
    
    def should_forward(self, node, msg):
        """Determinar si el mensaje debe ser reenviado"""
        # Verificar hops
        hops = msg.get("hops", 0)
        if hops <= 0:
            return False
        
        # Verificar que no vino de nosotros
        prev_hop = self._get_header(msg, "prev")
        if prev_hop == node.node_id or prev_hop == node.my_address:
            return False
        
        return True
    
    def forward_message(self, node, msg):
        """Reenviar mensaje a todos los vecinos activos"""
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
                node.log_message(f"[FLOODING] Reenviado a {neighbor_id}")
        
        self.stats["messages_flooded"] += forwarded_count
        return forwarded_count
    
    def process_message(self, node, msg):
        """Procesar mensaje recibido con flooding"""
        msg_type = msg.get("type", "")
        
        # Verificar duplicados
        if self.is_duplicate(msg):
            node.log_message(f"[FLOODING] Mensaje duplicado descartado: {self._get_header(msg, 'mid')}")
            return
        
        # Verificar si es para este nodo
        to_addr = msg.get("to", "")
        if to_addr == node.node_id or to_addr == node.my_address:
            self._deliver_message(node, msg)
            return
        
        # Reenviar mensaje
        forwarded = self.forward_message(node, msg)
        if forwarded > 0:
            mid = self._get_header(msg, "mid")
            node.log_message(f"[FLOODING] Mensaje {mid} reenviado a {forwarded} vecinos")
    
    def _deliver_message(self, node, msg):
        """Entregar mensaje al nodo local"""
        msg_type = msg.get("type", "")
        from_addr = msg.get("from", "")
        payload = msg.get("payload", "")
        
        self.stats["messages_delivered"] += 1
        
        if msg_type in MENSAJE:
            node.log_message(f"[FLOODING] MENSAJE RECIBIDO de {from_addr}: {msg}")
            print(f"[{node.node_id}] >>> MENSAJE: {payload}")
        elif msg_type in HOLA:
            node.handle_hello_received(msg)
        elif msg_type in ECHO:
            node.handle_echo_received(msg)
        elif msg_type in INFO:
            node.log_message(f"[FLOODING] INFO RECIBIDO de {from_addr}: {payload}")
    
    def create_data_message(self, from_addr, to_addr, data, hops=10):
        """Crear mensaje de datos para envío"""

        mensaje = Messages.create_data_message(
            from_addr=from_addr,
            to_addr=to_addr,
            payload=data,
            algorithm="flooding",
            hops=hops
        )
        print(mensaje)
        return mensaje
        
    
    def get_stats(self):
        """Obtener estadísticas del algoritmo"""
        return dict(self.stats)
    
    def reset_stats(self):
        """Resetear estadísticas"""
        self.stats = {
            "messages_flooded": 0,
            "duplicates_dropped": 0,
            "messages_delivered": 0
        }