import time

class Flooding:
    def __init__(self, node_id, neighbors):
        
        self.node_id = node_id
        self.neighbors = neighbors
        self.seen_messages = set()
        
        # Limpiar mensajes antiguos cada 300 segundos (5 minutos)
        self.last_cleanup = time.time()
        self.cleanup_interval = 300
        
        print(f"[Flooding {node_id}] Inicializado con vecinos: {neighbors}")

    def create_message(self, destination, payload, ttl=5):
       
        message = {
            "msg_id": f"{self.node_id}-{int(time.time() * 1000)}",  # Más único
            "from_node": self.node_id,
            "original_sender": self.node_id,  # Para tracking
            "to": destination,
            "ttl": ttl,
            "payload": payload,
            "timestamp": time.time()
        }
        
        print(f"[Flooding {self.node_id}] Creado mensaje {message['msg_id']} para {destination}")
        return message

    def receive_message(self, message):
       
        # Limpiar mensajes antiguos periódicamente
        self._cleanup_old_messages()
        
        msg_id = message.get("msg_id", "")
        from_node = message.get("from_node", "")
        to_node = message.get("to", "")
        ttl = message.get("ttl", 0)
        payload = message.get("payload", "")
        
        print(f"[Flooding {self.node_id}] Procesando mensaje {msg_id} de {from_node} hacia {to_node} (TTL: {ttl})")
        
        # Si ya procesamos este mensaje, ignoramos
        if msg_id in self.seen_messages:
            print(f"[Flooding {self.node_id}] Mensaje {msg_id} ya procesado, ignorando")
            return []
        
        # Marcar como procesado
        self.seen_messages.add(msg_id)
        
        # Si somos el destino, procesar y no reenviar
        if to_node == self.node_id:
            original_sender = message.get("original_sender", from_node)
            print(f"[Flooding {self.node_id}] 📩 MENSAJE RECIBIDO de {original_sender}: '{payload}'")
            return []
        
        # Verificar TTL
        if ttl <= 1:  # Si TTL es 1 o menos, no reenviar
            print(f"[Flooding {self.node_id}] ⚠ TTL agotado para {msg_id}, no reenviando")
            return []
        
        # Preparar para reenvío
        forward_list = []
        new_ttl = ttl - 1
        
        # Reenviar a todos los vecinos excepto de donde vino
        for neighbor in self.neighbors:
            if neighbor != from_node:  # No devolver al remitente
                new_msg = message.copy()
                new_msg["from_node"] = self.node_id  # Actualizar remitente
                new_msg["ttl"] = new_ttl  # Decrementar TTL
                forward_list.append((neighbor, new_msg))
                print(f"[Flooding {self.node_id}] Programado reenvío a {neighbor}")
        
        print(f"[Flooding {self.node_id}] Reenviando a {len(forward_list)} vecinos")
        return forward_list
    
    def _cleanup_old_messages(self):
        
        current_time = time.time()
        if current_time - self.last_cleanup > self.cleanup_interval:
            # En un escenario real, guardaríamos timestamps de mensajes
            # Por simplicidad, limpiamos todo periódicamente
            old_count = len(self.seen_messages)
            self.seen_messages.clear()
            self.last_cleanup = current_time
            if old_count > 0:
                print(f"[Flooding {self.node_id}] Limpiados {old_count} mensajes antiguos")
    
    def get_stats(self):
        
        return {
            "node_id": self.node_id,
            "neighbors": len(self.neighbors),
            "seen_messages": len(self.seen_messages)
        }