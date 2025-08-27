import time
import threading
import json
from connection.Red import RedConfig
from connection.redis_manager import RedisManager
from logs.Logs import Log
from algoritmos.Flodding import Flooding  # Usar el Flooding corregido

class NodoRedisSimple:
    def __init__(self, node_id, topology_file="data/topo.txt", names_file="data/id_nodos.txt"):
        self.node_id = node_id
        self.running = False
        
        # Log
        self.log = Log(f"./logs/{node_id}.txt")
        
        # Cargar configuración
        self.topology = RedConfig.load_topology(topology_file)
        self.names = RedConfig.load_names(names_file)
        
        # Obtener mis vecinos (node_ids) y mi dirección completa
        self.neighbor_ids = self.topology.get(node_id, [])
        self.my_address = self.names.get(node_id)
        
        if not self.my_address:
            raise ValueError(f"No se encontró dirección para nodo {node_id}")
        
        # Crear diccionario de vecinos: node_id -> dirección
        self.neighbors = {}
        for neighbor_id in self.neighbor_ids:
            neighbor_addr = self.names.get(neighbor_id)
            if neighbor_addr:
                self.neighbors[neighbor_id] = neighbor_addr
        
        # Inicializar algoritmo flooding con direcciones completas
        self.flooding = Flooding(node_id, self.my_address, self.neighbors)
        
        # Redis Manager
        self.redis_manager = RedisManager()
        
        # Estado de vecinos descubiertos
        self.active_neighbors = set()
        
        # Lock para thread safety
        self.lock = threading.Lock()
        
        self.log.write(f"[Nodo {self.node_id}] Inicializado - Dirección: {self.my_address}")
        self.log.write(f"[Nodo {self.node_id}] Vecinos: {self.neighbors}")

    def _setup_redis(self):
        """Configurar Redis"""
        try:
            if not self.redis_manager.connect():
                self.log.write(f"[Nodo {self.node_id}] ERROR: No se pudo conectar a Redis")
                return False
            
            # Configurar callback
            self.redis_manager.set_message_callback(self._on_redis_message)
            
            # Suscribirse al canal del nodo
            if not self.redis_manager.subscribe_to_channel(self.node_id):
                self.log.write(f"[Nodo {self.node_id}] ERROR: No se pudo suscribir al canal")
                return False
            
            # Iniciar escucha
            if not self.redis_manager.start_listening():
                self.log.write(f"[Nodo {self.node_id}] ERROR: No se pudo iniciar escucha")
                return False
            
            self.log.write(f"[Nodo {self.node_id}] Redis configurado - Canal: {self.node_id}")
            return True
            
        except Exception as e:
            self.log.write(f"[Nodo {self.node_id}] ERROR configurando Redis: {e}")
            return False

    def _validate_message_format(self, message):
        """Validar que el mensaje tenga el formato correcto"""
        required_fields = ["proto", "type", "from", "to", "ttl", "headers", "payload"]
        
        for field in required_fields:
            if field not in message:
                self.log.write(f"[Nodo {self.node_id}] Mensaje inválido: falta campo '{field}'")
                return False
        
        # Validar que headers sea una lista
        if not isinstance(message.get("headers"), list):
            self.log.write(f"[Nodo {self.node_id}] Mensaje inválido: 'headers' debe ser una lista")
            return False
            
        return True

    def _on_redis_message(self, message, channel):
        """Procesar mensajes recibidos de Redis"""
        try:
            # Validar formato del mensaje
            if not self._validate_message_format(message):
                return
            
            proto = message.get("proto", "")
            msg_type = message.get("type", "")
            from_addr = message.get("from", "")
            
            self.log.write(f"[Nodo {self.node_id}] Mensaje {proto}/{msg_type} recibido de {from_addr}")
            
            # Solo procesar mensajes flooding
            if proto != "flooding":
                self.log.write(f"[Nodo {self.node_id}] Protocolo {proto} no soportado")
                return
            
            if msg_type == "hello":
                # Procesar HELLO
                if self.flooding.process_hello(message):
                    neighbor_id = self._get_node_id_by_address(from_addr)
                    if neighbor_id:
                        with self.lock:
                            self.active_neighbors.add(neighbor_id)
                        self.log.write(f"[Nodo {self.node_id}] Vecino activo: {neighbor_id}")
                
            elif msg_type in ["message", "echo"]:
                # Procesar mensaje de datos o echo
                forwards = self.flooding.receive_message(message)
                
                # Reenviar si es necesario
                for neighbor_addr, forward_msg in forwards:
                    neighbor_id = self._get_node_id_by_address(neighbor_addr)
                    if neighbor_id:
                        self._send_to_neighbor(neighbor_id, forward_msg)
                        
            else:
                self.log.write(f"[Nodo {self.node_id}] Tipo de mensaje no reconocido: {msg_type}")
                
        except Exception as e:
            self.log.write(f"[Nodo {self.node_id}] ERROR procesando mensaje: {e}")

    def _get_node_id_by_address(self, address):
        """Obtener node_id a partir de una dirección"""
        for node_id, addr in self.names.items():
            if addr == address:
                return node_id
        return None

    def _send_to_neighbor(self, neighbor_id, message):
        """Enviar mensaje a un vecino específico usando el formato correcto"""
        try:
            # Validar formato antes de enviar
            if not self._validate_message_format(message):
                self.log.write(f"[Nodo {self.node_id}] No se puede enviar mensaje con formato inválido")
                return False
                
            if self.redis_manager.send_to_neighbor(neighbor_id, message):
                self.log.write(f"[Nodo {self.node_id}] Mensaje enviado a {neighbor_id}")
                return True
            else:
                self.log.write(f"[Nodo {self.node_id}] Error enviando a {neighbor_id}")
                return False
        except Exception as e:
            self.log.write(f"[Nodo {self.node_id}] ERROR enviando a {neighbor_id}: {e}")
            return False

    def send_hello_messages(self):
        """Enviar mensajes HELLO a todos los vecinos"""
        hello_msg = self.flooding.create_hello_message()
        
        sent_count = 0
        for neighbor_id in self.neighbor_ids:
            if self._send_to_neighbor(neighbor_id, hello_msg):
                sent_count += 1
            
        self.log.write(f"[Nodo {self.node_id}] HELLO enviado a {sent_count}/{len(self.neighbor_ids)} vecinos")

    def send_data_message(self, destination_input, payload):
        """Enviar mensaje de datos"""
        try:
            # Determinar dirección de destino
            destination_addr = None
            
            # Si es un node_id, convertir a dirección
            if destination_input in self.names:
                destination_addr = self.names[destination_input]
            # Si ya es una dirección, usarla directamente
            elif "@" in destination_input:
                destination_addr = destination_input
            else:
                self.log.write(f"[Nodo {self.node_id}] Destino no válido: {destination_input}")
                return
            
            # Crear mensaje usando flooding
            message = self.flooding.create_message(destination_addr, payload)
            
            # Procesar como si fuera recibido localmente (para iniciar flooding)
            forwards = self.flooding.receive_message(message)
            
            # Reenviar a vecinos
            sent_count = 0
            for neighbor_addr, forward_msg in forwards:
                neighbor_id = self._get_node_id_by_address(neighbor_addr)
                if neighbor_id and self._send_to_neighbor(neighbor_id, forward_msg):
                    sent_count += 1
                
            self.log.write(f"[Nodo {self.node_id}] Mensaje iniciado hacia {destination_addr}: '{payload}' ({sent_count} reenvíos)")
            
        except Exception as e:
            self.log.write(f"[Nodo {self.node_id}] ERROR enviando mensaje: {e}")

    def send_echo_message(self, destination_input):
        """Enviar mensaje ECHO (ping)"""
        try:
            # Crear mensaje de datos que será contestado automáticamente
            test_payload = f"Echo test from {self.node_id}"
            self.send_data_message(destination_input, test_payload)
            
        except Exception as e:
            self.log.write(f"[Nodo {self.node_id}] ERROR enviando echo: {e}")

    def _periodic_hello(self):
        """Enviar HELLOs periódicamente en un hilo separado"""
        while self.running:
            try:
                self.send_hello_messages()
                time.sleep(30)  # Cada 30 segundos
            except Exception as e:
                self.log.write(f"[Nodo {self.node_id}] ERROR en HELLO periódico: {e}")
                time.sleep(5)

    def start(self):
        """Iniciar el nodo"""
        if not self._setup_redis():
            return False
            
        self.running = True
        
        # Enviar HELLO inicial
        self.send_hello_messages()
        
        # Iniciar hilo para HELLOs periódicos
        hello_thread = threading.Thread(target=self._periodic_hello, daemon=True)
        hello_thread.start()
        
        self.log.write(f"[Nodo {self.node_id}] Nodo iniciado correctamente")
        return True

    def stop(self):
        """Detener el nodo"""
        self.running = False
        if self.redis_manager:
            self.redis_manager.stop()
        self.log.write(f"[Nodo {self.node_id}] Nodo detenido")

    def interactive_mode(self):
        """Modo interactivo simple"""
        print(f"\n=== NODO {self.node_id} - FLOODING ===")
        print(f"Dirección: {self.my_address}")
        print("Comandos:")
        print("  send <destino> <mensaje>  - Enviar mensaje (destino puede ser node_id o dirección)")
        print("  echo <destino>            - Enviar echo/ping")
        print("  neighbors                 - Ver vecinos activos")
        print("  stats                     - Estadísticas")
        print("  hello                     - Enviar HELLO manual")
        print("  addresses                 - Ver tabla de direcciones")
        print("  quit                      - Salir")
        print("=" * 50)
        
        while self.running:
            try:
                cmd = input(f"[{self.node_id}]> ").strip().split()
                if not cmd:
                    continue
                    
                if cmd[0] == "send" and len(cmd) >= 3:
                    destination = cmd[1]
                    message = " ".join(cmd[2:])
                    self.send_data_message(destination, message)
                    
                elif cmd[0] == "echo" and len(cmd) >= 2:
                    destination = cmd[1]
                    self.send_echo_message(destination)
                    
                elif cmd[0] == "neighbors":
                    with self.lock:
                        active = set(self.active_neighbors)
                    print(f"Vecinos activos ({len(active)}): {list(active)}")
                    print(f"Vecinos configurados: {self.neighbor_ids}")
                    
                elif cmd[0] == "stats":
                    stats = self.flooding.get_stats()
                    print(f"Estadísticas: {stats}")
                    with self.lock:
                        print(f"Vecinos activos: {len(self.active_neighbors)}")
                    
                elif cmd[0] == "addresses":
                    print("Tabla de direcciones:")
                    for node_id, addr in self.names.items():
                        status = "ACTIVO" if node_id in self.active_neighbors else "INACTIVO"
                        marker = " <-- YO" if node_id == self.node_id else ""
                        print(f"  {node_id}: {addr} [{status}]{marker}")
                    
                elif cmd[0] == "hello":
                    self.send_hello_messages()
                    print("HELLO enviado a todos los vecinos")
                    
                elif cmd[0] == "quit":
                    self.stop()
                    break
                    
                else:
                    print("Comando no reconocido")
                    
            except KeyboardInterrupt:
                self.stop()
                break
            except Exception as e:
                print(f"Error: {e}")

    def run(self):
        """Ejecutar el nodo"""
        try:
            if not self.start():
                print(f"[Nodo {self.node_id}] Error iniciando nodo")
                return
                
            print(f"[Nodo {self.node_id}] Nodo iniciado - Dirección: {self.my_address}")
            print(f"[Nodo {self.node_id}] Vecinos: {list(self.neighbors.keys())}")
            
            # Modo interactivo
            self.interactive_mode()
            
        except KeyboardInterrupt:
            print(f"\n[Nodo {self.node_id}] Deteniendo...")
            self.stop()
        except Exception as e:
            print(f"[Nodo {self.node_id}] Error: {e}")
            self.stop()

