import time

class Flooding:
    def __init__(self, node_id, node_address, neighbors):
        self.node_id = node_id
        self.node_address = node_address  # Dirección completa como "foo@bar.com/123"
        self.neighbors = neighbors
        self.seen_messages = set()
        
        # Limpiar mensajes antiguos cada 300 segundos (5 minutos)
        self.last_cleanup = time.time()
        self.cleanup_interval = 300
        
        print(f"[Flooding {node_id}] Inicializado con dirección {node_address}")
        print(f"[Flooding {node_id}] Vecinos: {neighbors}")

    def create_message(self, destination_address, payload, ttl=5):
        """Crear un nuevo mensaje de datos para flooding"""
        message = {
            "proto": "flooding",
            "type": "message",
            "from": self.node_address,
            "to": destination_address,
            "ttl": ttl,
            "headers": [
                {"msg_id": f"{self.node_id}-{int(time.time() * 1000)}"},
                {"original_sender": self.node_address},
                {"timestamp": time.time()}
            ],
            "payload": payload
        }
        
        print(f"[Flooding {self.node_id}] Creado mensaje para {destination_address}")
        return message

    def create_hello_message(self):
        """Crear mensaje HELLO para descubrimiento de vecinos"""
        message = {
            "proto": "flooding",
            "type": "hello",
            "from": self.node_address,
            "to": "broadcast",
            "ttl": 1,
            "headers": [
                {"node_id": self.node_id},
                {"timestamp": time.time()}
            ],
            "payload": {
                "neighbors": self.neighbors,
                "node_address": self.node_address
            }
        }
        
        print(f"[Flooding {self.node_id}] Creado mensaje HELLO")
        return message

    def create_echo_message(self, original_message):
        """Crear mensaje de respuesta ECHO"""
        original_sender = self._get_header_value(original_message, "original_sender")
        
        message = {
            "proto": "flooding",
            "type": "echo",
            "from": self.node_address,
            "to": original_sender or original_message["from"],
            "ttl": 5,
            "headers": [
                {"response_to": self._get_header_value(original_message, "msg_id")},
                {"timestamp": time.time()}
            ],
            "payload": f"Echo response from {self.node_address}"
        }
        
        return message

    def _get_header_value(self, message, key):
        """Extraer valor de los headers"""
        headers = message.get("headers", [])
        for header in headers:
            if key in header:
                return header[key]
        return None

    def _update_headers(self, message, updates):
        """Actualizar headers del mensaje"""
        headers = message.get("headers", [])
        
        # Crear nuevo header con updates
        for key, value in updates.items():
            # Buscar si ya existe el header
            found = False
            for header in headers:
                if key in header:
                    header[key] = value
                    found = True
                    break
            
            # Si no existe, agregarlo
            if not found:
                headers.append({key: value})
        
        message["headers"] = headers

    def process_hello(self, message):
        """Procesar mensaje HELLO de un vecino"""
        from_addr = message.get("from", "")
        payload = message.get("payload", {})
        remote_neighbors = payload.get("neighbors", [])
        
        print(f"[Flooding {self.node_id}] HELLO recibido de {from_addr}")
        print(f"[Flooding {self.node_id}] Vecinos remotos: {remote_neighbors}")
        
        # Verificar si somos vecinos mutuos
        node_id = self._get_header_value(message, "node_id")
        if node_id in self.neighbors:
            print(f"[Flooding {self.node_id}] Confirmado vecino: {node_id} ({from_addr})")
            return True
        else:
            print(f"[Flooding {self.node_id}] {node_id} no es nuestro vecino configurado")
            return False

    def receive_message(self, message):
        """Procesar mensaje recibido y determinar reenvíos"""
        # Limpiar mensajes antiguos periódicamente
        self._cleanup_old_messages()
        
        proto = message.get("proto", "")
        msg_type = message.get("type", "")
        
        # Solo procesar mensajes con protocolo flooding
        if proto != "flooding":
            print(f"[Flooding {self.node_id}] Protocolo {proto} no soportado")
            return []
        
        # Si es un mensaje HELLO, procesarlo por separado
        if msg_type == "hello":
            self.process_hello(message)
            return []  # Los HELLO no se reenvían
        
        # Si es ECHO, solo imprimir y no reenviar
        if msg_type == "echo":
            print(f"[Flooding {self.node_id}] ECHO recibido: {message.get('payload', '')}")
            return []
        
        # Procesar mensajes de datos
        if msg_type != "message":
            print(f"[Flooding {self.node_id}] Tipo de mensaje desconocido: {msg_type}")
            return []
        
        msg_id = self._get_header_value(message, "msg_id")
        from_addr = message.get("from", "")
        to_addr = message.get("to", "")
        ttl = message.get("ttl", 0)
        payload = message.get("payload", "")
        
        print(f"[Flooding {self.node_id}] Procesando mensaje {msg_id} de {from_addr} hacia {to_addr} (TTL: {ttl})")
        
        # Si ya procesamos este mensaje, ignoramos
        if msg_id and msg_id in self.seen_messages:
            print(f"[Flooding {self.node_id}] Mensaje {msg_id} ya procesado, ignorando")
            return []
        
        # Marcar como procesado
        if msg_id:
            self.seen_messages.add(msg_id)
        
        # Si somos el destino, procesar y no reenviar
        if to_addr == self.node_address:
            original_sender = self._get_header_value(message, "original_sender") or from_addr
            print(f"[Flooding {self.node_id}] MENSAJE RECIBIDO de {original_sender}: '{payload}'")
            return []
        
        # Verificar TTL
        if ttl <= 1:
            print(f"[Flooding {self.node_id}] TTL agotado para {msg_id}, no reenviando")
            return []
        
        # Preparar para reenvío
        forward_list = []
        new_ttl = ttl - 1
        
        # Reenviar a todos los vecinos excepto de donde vino
        for neighbor_addr in self.neighbors.values():
            if neighbor_addr != from_addr:
                # Crear copia del mensaje
                new_msg = message.copy()
                new_msg["from"] = self.node_address
                new_msg["ttl"] = new_ttl
                
                # Actualizar headers
                self._update_headers(new_msg, {"forwarded_by": self.node_address})
                
                forward_list.append((neighbor_addr, new_msg))
                print(f"[Flooding {self.node_id}] Programado reenvío a {neighbor_addr}")
        
        print(f"[Flooding {self.node_id}] Reenviando a {len(forward_list)} vecinos")
        return forward_list

    def _cleanup_old_messages(self):
        """Limpiar mensajes antiguos para evitar acumulación de memoria"""
        current_time = time.time()
        if current_time - self.last_cleanup > self.cleanup_interval:
            old_count = len(self.seen_messages)
            self.seen_messages.clear()
            self.last_cleanup = current_time
            if old_count > 0:
                print(f"[Flooding {self.node_id}] Limpiados {old_count} mensajes antiguos")

    def get_stats(self):
        """Obtener estadísticas del nodo"""
        return {
            "node_id": self.node_id,
            "node_address": self.node_address,
            "neighbors": len(self.neighbors),
            "seen_messages": len(self.seen_messages)
        }