import time
import threading
import json
from typing import Dict, List, Set, Tuple, Optional
from connection.Red import RedConfig
from connection.redis_manager import RedisManager
from logs.Logs import Log
from algoritmos.Flodding import Flooding
from algoritmos.DJstra import SolveDjstra
from connection.Red import Red
from algoritmos.LSR import LSR


class NodoRedisSimple:
    def __init__(self, node_id, topology_file="data/topo.txt", names_file="data/id_nodos.txt", routing_algorithm="flooding"):
        self.node_id = node_id
        self.running = False
        self.routing_algorithm = routing_algorithm  # "flooding" o "lsr"
        
        # Log
        self.log = Log(f"./logs/{node_id}.txt")
        
        # Cargar configuración
        self.topology = RedConfig.load_topology(topology_file)
        self.names = RedConfig.load_names(names_file)
        
        # Obtener mis vecinos y dirección
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
        
        # Tabla de ruteo compartida
        self.routing_table = {}
        
        # Inicializar algoritmos de ruteo
        self._init_routing_algorithms()
        
        # Redis Manager
        self.redis_manager = RedisManager()
        
        # Estado de vecinos
        self.active_neighbors = set()
        
        # Locks para thread safety
        self.lock = threading.Lock()
        self.routing_lock = threading.Lock()
        
        # Hilos de procesos
        self.routing_thread = None
        self.forwarding_thread = None
        
        self.log.write(f"[Nodo {self.node_id}] Inicializado - Algoritmo: {routing_algorithm}")
        self.log.write(f"[Nodo {self.node_id}] Dirección: {self.my_address}")
        self.log.write(f"[Nodo {self.node_id}] Vecinos: {self.neighbors}")

    def _init_routing_algorithms(self):
        """Inicializar algoritmos de ruteo"""
        # Flooding (siempre disponible)
        self.flooding = Flooding(self.node_id, self.my_address, self.neighbors)
        
        # LSR (si está seleccionado)
        if self.routing_algorithm == "lsr":
            # Para LSR necesitamos costos, usaremos 1 por defecto
            neighbor_costs = {neighbor_id: 1 for neighbor_id in self.neighbor_ids}
            self.lsr = LSR(self.node_id, neighbor_costs)
        else:
            self.lsr = None

    def _setup_redis(self):
        """Configurar Redis"""
        try:
            if not self.redis_manager.connect():
                self.log.write(f"[Nodo {self.node_id}] ERROR: No se pudo conectar a Redis")
                return False
            
            # Configurar callback para forwarding
            self.redis_manager.set_message_callback(self._forwarding_process)
            
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
        """Validar formato de mensaje"""
        required_fields = ["proto", "type", "from", "to", "ttl", "headers", "payload"]
        
        for field in required_fields:
            if field not in message:
                self.log.write(f"[Nodo {self.node_id}] Mensaje inválido: falta campo '{field}'")
                return False
        
        if not isinstance(message.get("headers"), list):
            self.log.write(f"[Nodo {self.node_id}] Mensaje inválido: 'headers' debe ser una lista")
            return False
            
        return True

    # ================== PROCESO DE FORWARDING ==================
    
    def _forwarding_process(self, message, channel):
        """Proceso de Forwarding - Manejo de paquetes entrantes"""
        try:
            if not self._validate_message_format(message):
                return
            
            proto = message.get("proto", "")
            msg_type = message.get("type", "")
            from_addr = message.get("from", "")
            to_addr = message.get("to", "")
            
            self.log.write(f"[FORWARDING] Mensaje {proto}/{msg_type} de {from_addr} para {to_addr}")
            
            # Determinar el tipo de paquete y procesarlo
            if proto == "flooding":
                self._handle_flooding_packet(message)
            elif proto == "lsr":
                self._handle_lsr_packet(message)
            elif proto == "data":
                self._handle_data_packet(message)
            elif proto == "hello" or msg_type == "ping":
                self._handle_hello_ping_packet(message)
            else:
                self.log.write(f"[FORWARDING] Protocolo {proto} no soportado")
                
        except Exception as e:
            self.log.write(f"[FORWARDING] ERROR procesando mensaje: {e}")

    def _handle_flooding_packet(self, message):
        """Manejar paquetes de flooding"""
        msg_type = message.get("type", "")
        from_addr = message.get("from", "")
        
        if msg_type == "hello":
            # Procesar HELLO
            if self.flooding.process_hello(message):
                neighbor_id = self._get_node_id_by_address(from_addr)
                if neighbor_id:
                    with self.lock:
                        self.active_neighbors.add(neighbor_id)
                    self.log.write(f"[FORWARDING] Vecino activo: {neighbor_id}")
        
        elif msg_type in ["message", "echo"]:
            # Procesar mensaje de datos
            forwards = self.flooding.receive_message(message)
            
            # Reenviar si es necesario
            for neighbor_addr, forward_msg in forwards:
                neighbor_id = self._get_node_id_by_address(neighbor_addr)
                if neighbor_id:
                    self._send_to_neighbor(neighbor_id, forward_msg)

    def _handle_lsr_packet(self, message):
        """Manejar paquetes LSR - Pasarlos al proceso de ruteo"""
        if self.lsr is None:
            return
            
        msg_type = message.get("type", "")
        
        if msg_type == "lsp":
            # Paquete LSP - pasar al proceso de ruteo
            threading.Thread(target=self._process_lsp_in_routing, args=(message,), daemon=True).start()

    def _handle_data_packet(self, message):
        """Manejar paquetes de datos"""
        to_addr = message.get("to", "")
        payload = message.get("payload", "")
        
        # ¿Es para nosotros?
        if to_addr == self.my_address or to_addr == self.node_id:
            self.log.write(f"[FORWARDING] MENSAJE RECIBIDO: {payload}")
            print(f"[{self.node_id}] >>> MENSAJE: {payload}")
        else:
            # Forward usando la tabla de ruteo actual
            self._forward_data_packet(message)

    def _handle_hello_ping_packet(self, message):
        """Manejar paquetes Hello/Ping"""
        from_addr = message.get("from", "")
        msg_type = message.get("type", "")
        
        if msg_type == "ping":
            # Responder ping
            pong_msg = {
                "proto": "hello",
                "type": "pong", 
                "from": self.my_address,
                "to": from_addr,
                "ttl": 5,
                "headers": [],
                "payload": f"Pong from {self.node_id}"
            }
            
            neighbor_id = self._get_node_id_by_address(from_addr)
            if neighbor_id:
                self._send_to_neighbor(neighbor_id, pong_msg)

    def _forward_data_packet(self, message):
        """Forward de paquetes de datos usando tabla de ruteo"""
        to_addr = message.get("to", "")
        dest_node_id = self._get_node_id_by_address(to_addr) or to_addr
        
        with self.routing_lock:
            # Usar tabla de ruteo del algoritmo activo
            next_hop = None
            
            if self.routing_algorithm == "lsr" and self.lsr:
                next_hop = self.lsr.get_next_hop(dest_node_id)
            elif self.routing_algorithm == "flooding":
                # Flooding no tiene tabla de ruteo específica, reenvía a todos
                forwards = self.flooding.receive_message(message)
                for neighbor_addr, forward_msg in forwards:
                    neighbor_id = self._get_node_id_by_address(neighbor_addr)
                    if neighbor_id:
                        self._send_to_neighbor(neighbor_id, forward_msg)
                return
        
        if next_hop:
            # Decrementar TTL
            message["ttl"] -= 1
            if message["ttl"] > 0:
                self._send_to_neighbor(next_hop, message)
                self.log.write(f"[FORWARDING] Datos reenviados a {next_hop} hacia {dest_node_id}")
            else:
                self.log.write(f"[FORWARDING] TTL agotado, descartando paquete")
        else:
            self.log.write(f"[FORWARDING] No hay ruta a {dest_node_id}")

    # ================== PROCESO DE RUTEO ==================
    
    def _routing_process(self):
        """Proceso de Ruteo - Gestión de información de ruteo"""
        while self.running:
            try:
                if self.routing_algorithm == "lsr" and self.lsr:
                    self._lsr_routing_cycle()
                elif self.routing_algorithm == "flooding":
                    self._flooding_routing_cycle()
                    
                time.sleep(10)  # Ciclo cada 10 segundos
                
            except Exception as e:
                self.log.write(f"[RUTEO] ERROR en ciclo de ruteo: {e}")
                time.sleep(5)

    def _lsr_routing_cycle(self):
        """Ciclo de ruteo para LSR"""
        if self.lsr.should_send_lsp():
            # Crear y enviar LSP
            lsp = self.lsr.create_lsp()
            
            # Enviar a todos los vecinos activos
            sent_count = 0
            for neighbor_id in self.neighbor_ids:
                if self._send_to_neighbor(neighbor_id, lsp):
                    sent_count += 1
            
            self.log.write(f"[RUTEO-LSR] LSP enviado a {sent_count}/{len(self.neighbor_ids)} vecinos")
            
            # Actualizar tabla de ruteo compartida
            with self.routing_lock:
                self.routing_table = self.lsr.get_routing_table()

    def _flooding_routing_cycle(self):
        """Ciclo de ruteo para Flooding (HELLOs periódicos)"""
        hello_msg = self.flooding.create_hello_message()
        
        sent_count = 0
        for neighbor_id in self.neighbor_ids:
            if self._send_to_neighbor(neighbor_id, hello_msg):
                sent_count += 1
        
        self.log.write(f"[RUTEO-FLOODING] HELLO enviado a {sent_count}/{len(self.neighbor_ids)} vecinos")

    def _process_lsp_in_routing(self, lsp_message):
        """Procesar LSP en el proceso de ruteo"""
        if self.lsr is None:
            return
            
        try:
            forwards = self.lsr.process_lsp(lsp_message)
            
            # Reenviar LSPs
            for neighbor_id, forward_lsp in forwards:
                self._send_to_neighbor(neighbor_id, forward_lsp)
            
            # Actualizar tabla de ruteo compartida
            with self.routing_lock:
                self.routing_table = self.lsr.get_routing_table()
                
        except Exception as e:
            self.log.write(f"[RUTEO] ERROR procesando LSP: {e}")

    # ================== MÉTODOS DE UTILIDAD ==================
    
    def _get_node_id_by_address(self, address):
        """Obtener node_id a partir de una dirección"""
        for node_id, addr in self.names.items():
            if addr == address:
                return node_id
        return None

    def _send_to_neighbor(self, neighbor_id, message):
        """Enviar mensaje a un vecino específico"""
        try:
            if not self._validate_message_format(message):
                self.log.write(f"[Nodo {self.node_id}] No se puede enviar mensaje con formato inválido")
                return False
                
            if self.redis_manager.send_to_neighbor(neighbor_id, message):
                return True
            else:
                return False
        except Exception as e:
            self.log.write(f"[Nodo {self.node_id}] ERROR enviando a {neighbor_id}: {e}")
            return False

    # ================== MÉTODOS PÚBLICOS ==================

    def send_data_message(self, destination_input, payload):
        """Enviar mensaje de datos"""
        try:
            # Determinar dirección de destino
            destination_addr = None
            
            if destination_input in self.names:
                destination_addr = self.names[destination_input]
            elif "@" in destination_input:
                destination_addr = destination_input
            else:
                self.log.write(f"[Nodo {self.node_id}] Destino no válido: {destination_input}")
                return
            
            # Crear mensaje de datos
            message = {
                "proto": "data",
                "type": "message",
                "from": self.my_address,
                "to": destination_addr,
                "ttl": 10,
                "headers": [],
                "payload": payload
            }
            
            # Procesar según algoritmo
            if self.routing_algorithm == "flooding":
                # Usar flooding
                flood_msg = self.flooding.create_message(destination_addr, payload)
                forwards = self.flooding.receive_message(flood_msg)
                
                sent_count = 0
                for neighbor_addr, forward_msg in forwards:
                    neighbor_id = self._get_node_id_by_address(neighbor_addr)
                    if neighbor_id and self._send_to_neighbor(neighbor_id, forward_msg):
                        sent_count += 1
                        
                self.log.write(f"[Nodo {self.node_id}] Mensaje (flooding) hacia {destination_addr}: '{payload}' ({sent_count} reenvíos)")
                
            elif self.routing_algorithm == "lsr" and self.lsr:
                # Usar tabla de ruteo LSR
                dest_node_id = self._get_node_id_by_address(destination_addr) or destination_input
                next_hop = self.lsr.get_next_hop(dest_node_id)
                
                if next_hop:
                    if self._send_to_neighbor(next_hop, message):
                        self.log.write(f"[Nodo {self.node_id}] Mensaje (LSR) hacia {destination_addr} vía {next_hop}: '{payload}'")
                    else:
                        self.log.write(f"[Nodo {self.node_id}] Error enviando hacia {next_hop}")
                else:
                    self.log.write(f"[Nodo {self.node_id}] No hay ruta LSR hacia {dest_node_id}")
            
        except Exception as e:
            self.log.write(f"[Nodo {self.node_id}] ERROR enviando mensaje: {e}")

    def send_ping(self, destination_input):
        """Enviar ping a un destino"""
        try:
            destination_addr = None
            if destination_input in self.names:
                destination_addr = self.names[destination_input]
            elif "@" in destination_input:
                destination_addr = destination_input
            else:
                self.log.write(f"[Nodo {self.node_id}] Destino no válido para ping: {destination_input}")
                return
            
            ping_msg = {
                "proto": "hello",
                "type": "ping",
                "from": self.my_address,
                "to": destination_addr,
                "ttl": 5,
                "headers": [],
                "payload": f"Ping from {self.node_id}"
            }
            
            # Enviar ping usando forwarding normal
            self._handle_data_packet(ping_msg)
            
        except Exception as e:
            self.log.write(f"[Nodo {self.node_id}] ERROR enviando ping: {e}")

    def switch_routing_algorithm(self, algorithm):
        """Cambiar algoritmo de ruteo en runtime"""
        if algorithm not in ["flooding", "lsr"]:
            print(f"Algoritmo no válido: {algorithm}")
            return False
            
        if algorithm == self.routing_algorithm:
            print(f"Ya usando algoritmo {algorithm}")
            return True
            
        old_alg = self.routing_algorithm
        self.routing_algorithm = algorithm
        
        # Reinicializar algoritmos si es necesario
        if algorithm == "lsr" and self.lsr is None:
            neighbor_costs = {neighbor_id: 1 for neighbor_id in self.neighbor_ids}
            self.lsr = LSR(self.node_id, neighbor_costs)
            
        with self.routing_lock:
            self.routing_table.clear()
            
        self.log.write(f"[Nodo {self.node_id}] Algoritmo cambiado: {old_alg} → {algorithm}")
        print(f"Algoritmo de ruteo cambiado a: {algorithm}")
        return True

    def start(self):
        """Iniciar el nodo"""
        if not self._setup_redis():
            return False
            
        self.running = True
        
        # Iniciar proceso de ruteo
        self.routing_thread = threading.Thread(target=self._routing_process, daemon=True)
        self.routing_thread.start()
        
        # Envío inicial
        if self.routing_algorithm == "flooding":
            hello_msg = self.flooding.create_hello_message()
            for neighbor_id in self.neighbor_ids:
                self._send_to_neighbor(neighbor_id, hello_msg)
        elif self.routing_algorithm == "lsr" and self.lsr:
            lsp = self.lsr.create_lsp()
            for neighbor_id in self.neighbor_ids:
                self._send_to_neighbor(neighbor_id, lsp)
        
        self.log.write(f"[Nodo {self.node_id}] Nodo iniciado correctamente con {self.routing_algorithm}")
        return True

    def stop(self):
        """Detener el nodo"""
        self.running = False
        if self.redis_manager:
            self.redis_manager.stop()
        self.log.write(f"[Nodo {self.node_id}] Nodo detenido")

    def interactive_mode(self):
        """Modo interactivo mejorado"""
        print(f"\n=== NODO {self.node_id} - ALGORITMO: {self.routing_algorithm.upper()} ===")
        print(f"Dirección: {self.my_address}")
        print("Comandos:")
        print("  send <destino> <mensaje>     - Enviar mensaje")
        print("  ping <destino>               - Enviar ping")

        if self.routing_algorithm == "flooding":
            print("  neighbors                    - Ver vecinos activos")

        if self.routing_algorithm == "lsr":
            print("  routing                      - Ver tabla de ruteo")
            print("  topology                     - Ver topología conocida (LSR)")

        print("  algorithm <flooding|lsr>     - Cambiar algoritmo")
        print("  stats                        - Estadísticas")
        print("  addresses                    - Ver direcciones")
        print("  quit                         - Salir")
        print("=" * 60)

        
        while self.running:
            try:
                cmd = input(f"[{self.node_id}-{self.routing_algorithm}]> ").strip().split()
                if not cmd:
                    continue
                    
                if cmd[0] == "send" and len(cmd) >= 3:
                    destination = cmd[1]
                    message = " ".join(cmd[2:])
                    self.send_data_message(destination, message)
                    
                elif cmd[0] == "ping" and len(cmd) >= 2:
                    destination = cmd[1]
                    self.send_ping(destination)
                    
                elif cmd[0] == "neighbors":
                    with self.lock:
                        active = set(self.active_neighbors)
                    print(f"Vecinos activos ({len(active)}): {list(active)}")
                    print(f"Vecinos configurados: {self.neighbor_ids}")
                    
                elif cmd[0] == "routing":
                    with self.routing_lock:
                        if self.routing_table:
                            print("Tabla de Ruteo:")
                            for dest, info in self.routing_table.items():
                                print(f"  {dest} -> next_hop: {info['next_hop']}, cost: {info['cost']}")
                        else:
                            print("Tabla de ruteo vacía")
                    
                elif cmd[0] == "topology":
                    if self.routing_algorithm == "lsr" and self.lsr:
                        print("Base de Datos de Estado de Enlaces:")
                        for node, data in self.lsr.link_state_db.items():
                            print(f"  {node}: vecinos={data['neighbors']}, seq={data['sequence']}")
                    else:
                        print("Información de topología solo disponible con LSR")
                    
                elif cmd[0] == "algorithm" and len(cmd) >= 2:
                    new_alg = cmd[1]
                    self.switch_routing_algorithm(new_alg)
                    
                elif cmd[0] == "stats":
                    print(f"Algoritmo actual: {self.routing_algorithm}")
                    if self.routing_algorithm == "flooding":
                        stats = self.flooding.get_stats()
                        print(f"Estadísticas flooding: {stats}")
                    elif self.routing_algorithm == "lsr" and self.lsr:
                        print(f"LSPs conocidos: {len(self.lsr.link_state_db)}")
                        print(f"Rutas calculadas: {len(self.lsr.routing_table)}")
                        print(f"Último LSP enviado: {time.time() - self.lsr.last_lsp_time:.1f}s atrás")
                    
                    with self.lock:
                        print(f"Vecinos activos: {len(self.active_neighbors)}")
                    
                elif cmd[0] == "addresses":
                    print("Tabla de direcciones:")
                    for node_id, addr in self.names.items():
                        status = "ACTIVO" if node_id in self.active_neighbors else "INACTIVO"
                        marker = " <-- YO" if node_id == self.node_id else ""
                        print(f"  {node_id}: {addr} [{status}]{marker}")
                    
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
                
            print(f"[Nodo {self.node_id}] Nodo iniciado - Algoritmo: {self.routing_algorithm}")
            print(f"[Nodo {self.node_id}] Dirección: {self.my_address}")
            print(f"[Nodo {self.node_id}] Vecinos: {list(self.neighbors.keys())}")
            
            # Modo interactivo
            self.interactive_mode()
            
        except KeyboardInterrupt:
            print(f"\n[Nodo {self.node_id}] Deteniendo...")
            self.stop()
        except Exception as e:
            print(f"[Nodo {self.node_id}] Error: {e}")
            self.stop()

