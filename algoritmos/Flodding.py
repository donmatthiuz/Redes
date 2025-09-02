import time
import json
from connection.Mensajes import Messages
from algoritmos.TIPOS import ECHO, INFO, MENSAJE, HOLA, BROADCAST

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
        headers = msg.get("headers", {})
        if isinstance(headers, list):
            # Convertir lista de headers a diccionario
            headers_dict = {}
            for header in headers:
                if isinstance(header, dict):
                    headers_dict.update(header)
                elif isinstance(header, str):
                    headers_dict[header] = True
            return headers_dict.get(key, default)
        elif isinstance(headers, dict):
            return headers.get(key, default)
        return default
    
    def _set_header(self, msg, key, value):
        """Establecer valor de un header"""
        headers = msg.get("headers", {})
        
        # Asegurar que headers sea un diccionario
        if isinstance(headers, list):
            headers_dict = {}
            for header in headers:
                if isinstance(header, dict):
                    headers_dict.update(header)
                elif isinstance(header, str):
                    headers_dict[header] = True
            headers = headers_dict
        elif not isinstance(headers, dict):
            headers = {}
        
        headers[key] = value
        msg["headers"] = headers
    
    def _remove_header(self, msg, key):
        """Remover un header específico"""
        headers = msg.get("headers", {})
        
        # Asegurar que headers sea un diccionario
        if isinstance(headers, list):
            headers_dict = {}
            for header in headers:
                if isinstance(header, dict):
                    headers_dict.update(header)
                elif isinstance(header, str):
                    headers_dict[header] = True
            headers = headers_dict
        elif not isinstance(headers, dict):
            headers = {}
        
        if key in headers:
            del headers[key]
        
        msg["headers"] = headers
    
    def _generate_message_signature(self, msg):
        src = msg.get("from", "unknown")
        dest = msg.get("to", "unknown")
        saltos = msg.get("hops", "unknown")
        msg_type = msg.get("type", "")
        payload = msg.get("payload", "")

        # Crear hash único usando string concatenado
        signature = hash(f"{src}:{dest}:{msg_type}:{saltos}:{json.dumps(payload, sort_keys=True)}")
        return signature

    
    def is_duplicate(self, msg):
        """Verificar si el mensaje ya fue procesado"""
        signature = self._generate_message_signature(msg)
        
        if signature in self.seen_messages:
            self.stats["duplicates_dropped"] += 1
            return True
        
        self.seen_messages.add(signature)
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
        if not self.should_forward(node, msg):
            return 0

        # Crear una copia del mensaje para enviar
        forward_msg = dict(msg)
        
        # Reducir hops
        forward_msg["hops"] = msg.get("hops", 0) - 1
        
        # Marcar este nodo como prev hop para el siguiente salto
        self._set_header(forward_msg, "prev", node.node_id)

        # Nodo del que recibimos el mensaje
        prev_hop = self._get_header(msg, "prev")

        forwarded_count = 0
        current_time = time.time()

        for neighbor_id in node.neighbor_ids:
            # No reenviar al que nos envió el mensaje
            if neighbor_id == prev_hop:
                continue
            
            # Solo reenviar a vecinos activos
            if not node.is_neighbor_active(neighbor_id, current_time):
                continue

            # Preparar mensaje limpio
            clean_msg = self.prepare_message_for_send(forward_msg)
            
            # Enviar mensaje
            if node.send_to_neighbor(neighbor_id, clean_msg):
                forwarded_count += 1
                node.log_message(f"[FLOODING] Reenviado a {neighbor_id}")

        # Actualizar estadísticas
        self.stats["messages_flooded"] += forwarded_count
        return forwarded_count


    def should_flood_message_type(self, msg_type):
        """Determinar si este tipo de mensaje debe usar flooding"""
        # Solo MENSAJE e INFO usan flooding
        # HELLO y ECHO son comunicación directa entre vecinos
        return msg_type in MENSAJE or msg_type in INFO
    
    def process_message(self, node, msg):
        """Procesar mensaje recibido con flooding"""
        msg_type = msg.get("type", "")
        # HELLO y ECHO no usan flooding - procesamiento directo
        if msg_type in HOLA:
            node.update_neighbor_activity(msg.get("from", ""))
            node.log_message(f"[FLOODING] HELLO directo de {msg.get('from', '')}")
            return
        elif msg_type in ECHO:
            node.handle_echo_received(msg)
            return
        
        # Solo procesar con flooding MENSAJE e INFO
        if not self.should_flood_message_type(msg_type):
            return
        
        # Verificar duplicados
        if self.is_duplicate(msg):
            signature = self._generate_message_signature(msg)
            node.log_message(f"[FLOODING] Mensaje duplicado descartado: {signature}")
            return
        
        # Verificar si es para este nodo
        to_addr = msg.get("to", "")
        if to_addr == node.node_id or to_addr == node.my_address or to_addr in BROADCAST:
            self._deliver_message(node, msg)
            return
        
        # Reenviar mensaje
        forwarded = self.forward_message(node, msg)
        if forwarded > 0:
            signature = self._generate_message_signature(msg)
            node.log_message(f"[FLOODING] Mensaje {signature} reenviado a {forwarded} vecinos")
    
    def _deliver_message(self, node, msg):
        """Entregar mensaje al nodo local"""
        msg_type = msg.get("type", "")
        from_addr = msg.get("from", "")
        payload = msg.get("payload", "")
        
        # Limpiar headers internos antes de entregar
        clean_msg = self.prepare_message_for_send(msg)
        
        self.stats["messages_delivered"] += 1
        
        if msg_type in MENSAJE:
            node.log_message(f"[FLOODING] MENSAJE RECIBIDO de {from_addr}: {clean_msg}")
            print(f"[{node.node_id}] >>> MENSAJE: {payload}")
        elif msg_type in HOLA:
            # HELLO no debe ser procesado en flooding, solo actualizar vecino
            node.update_neighbor_activity(from_addr)
            node.log_message(f"[FLOODING] HELLO recibido de {from_addr} - vecino actualizado")
        elif msg_type in ECHO:
            node.handle_echo_received(clean_msg)
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
        
        # Asegurar que headers esté en formato diccionario
        if isinstance(mensaje.get("headers"), list):
            headers_dict = {}
            for header in mensaje["headers"]:
                if isinstance(header, dict):
                    headers_dict.update(header)
                elif isinstance(header, str):
                    headers_dict[header] = True
            mensaje["headers"] = headers_dict
        
        # Preparar mensaje limpio para envío
        clean_mensaje = self.prepare_message_for_send(mensaje)
        print(clean_mensaje)
        return clean_mensaje
    
    def prepare_message_for_send(self, msg):
        """Preparar mensaje para envío (limpiar headers internos)"""
        clean_msg = dict(msg)
        
        # Mantener solo headers públicos
        headers = clean_msg.get("headers", {})
        if isinstance(headers, dict):
            # Crear nueva estructura de headers sin headers internos
            clean_headers = {k: v for k, v in headers.items() if k not in ["prev"]}
            clean_msg["headers"] = clean_headers
        elif isinstance(headers, list):
            # Convertir y limpiar
            headers_dict = {}
            for header in headers:
                if isinstance(header, dict):
                    headers_dict.update(header)
                elif isinstance(header, str):
                    headers_dict[header] = True
            # Remover headers internos
            clean_headers = {k: v for k, v in headers_dict.items() if k not in ["prev"]}
            clean_msg["headers"] = clean_headers
        
        return clean_msg
    
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