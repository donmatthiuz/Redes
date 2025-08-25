from multiprocessing import Process, Manager, Lock, Queue
import time
import json
from connection.socket_manager import SocketManager
from connection.Mensajes import Mensajes_Protocolo
from connection.Red import RedConfig
from algoritmos.Flodding import Flooding
from algoritmos.LSR import LSR
from logs.Logs import Log

class Nodo:
    def __init__(self, node_id, algorithm="flooding", host="127.0.0.1", port=5000, 
                 topology_file="data/topo.txt", names_file="data/id_nodos.txt"):
        
        self.node_id = node_id
        self.algorithm = algorithm.lower()
        self.host = host
        self.port = port
        self.log = Log(f"./logs/{node_id}.txt")
        
        # Validar algoritmo
        if self.algorithm not in ["flooding", "lsr"]:
            raise ValueError(f"Algoritmo no soportado: {algorithm}. Use 'flooding' o 'lsr'")
        
        # Manager para compartir datos entre procesos
        manager = Manager()
        self.running = manager.Value('b', False)
        
        # Datos compartidos entre procesos
        self.shared_routing_table = manager.dict()
        self.shared_discovered_nodes = manager.dict()
        self.shared_neighbor_ports = manager.dict()
        self.shared_node_info = manager.dict()
        
        # Lock para sincronización
        self.lock = Lock()
        
        # Colas para comunicación entre procesos
        self.routing_info_queue = Queue()      # Para paquetes de info de ruteo
        self.incoming_packets_queue = Queue()  # Para paquetes entrantes
        self.outgoing_packets_queue = Queue()  # Para paquetes salientes
        self.new_nodes_queue = Queue()         # Para notificación de nuevos nodos
        self.lsp_queue = Queue()              # Para LSPs (solo LSR)
        
        # Cargar configuración
        self.topology = RedConfig.load_topology(topology_file)
        self.names = RedConfig.load_names(names_file)
        
        # Obtener mis vecinos y dirección
        self.neighbors = self.topology.get(node_id, [])
        self.my_address = self.names.get(node_id, f"{node_id}@localhost")
        
        # Crear diccionario de vecinos con costos para LSR
        self.neighbor_costs = {}
        for neighbor in self.neighbors:
            # Por defecto, costo 1 para todos los vecinos
            # Esto se puede modificar según la topología
            self.neighbor_costs[neighbor] = 1
        
        # Inicializar datos del nodo
        self.shared_node_info.update({
            'node_id': node_id,
            'address': self.my_address,
            'neighbors': self.neighbors,
            'algorithm': self.algorithm
        })
        


        self.log.write(f"[Nodo {self.node_id}] Inicializado con algoritmo {self.algorithm.upper()}")
        self.log.write(f"[Nodo {self.node_id}] Dirección: {self.my_address}")
        self.log.write(f"[Nodo {self.node_id}] Vecinos: {self.neighbors}")

    
        if self.algorithm == "lsr":
            self.log.write(f"[Nodo {self.node_id}] Costos vecinos: {self.neighbor_costs}")

    def _socket_process(self):
        
        # Crear socket manager en este proceso
        socket_manager = SocketManager(host=self.host, port=self.port)
        socket_manager.on_message = self._on_message_multiprocess
        


        self.log.write(f"[Nodo {self.node_id}] Socket iniciado en proceso separado")
        socket_manager.start_server()
        
        # Manejo de mensajes salientes
        while self.running.value:
            try:
                if not self.outgoing_packets_queue.empty():
                    host, port, message = self.outgoing_packets_queue.get(timeout=0.1)
                    socket_manager.send_message(host, port, message)
                    self.log.write(f"[Nodo {self.node_id}] [SOCKET] 📤 Enviado a {host}:{port}")
                    
                time.sleep(0.1)
            except:
                continue
        
        socket_manager.stop()

    def _on_message_multiprocess(self, raw_message, addr):
        
        try:
            if isinstance(raw_message, str):
                message = json.loads(raw_message)
            else:
                message = raw_message
            
            msg_type = message.get("type")
            msg_proto = message.get("proto", "")
            
            
            
            self.log.write(f"[Nodo {self.node_id}] [SOCKET] 📨 Recibido {msg_type}({msg_proto}) de {addr}")
            # Todos los mensajes van primero a incoming_packets para forwarding
            self.incoming_packets_queue.put((message, addr))
            
            # Distribuir según el algoritmo y tipo de mensaje
            if self.algorithm == "flooding":
                # Para flooding: mensajes de ruteo van a routing_info_queue
                if msg_type in ["hello", "routing_info", "node_discovery"]:
                    self.routing_info_queue.put((message, addr))
            
            elif self.algorithm == "lsr":
                # Para LSR: LSPs van a lsp_queue, otros mensajes de ruteo a routing_info_queue
                if msg_type == "lsp" and msg_proto == "lsr":
                    self.lsp_queue.put((message, addr))
                elif msg_type in ["hello", "routing_info", "node_discovery"]:
                    self.routing_info_queue.put((message, addr))
                    
        except Exception as e:
            print(f"[Nodo {self.node_id}] [SOCKET] Error procesando mensaje: {e}")

    def ruteo(self):
        
        
        self.log.write(f"[Nodo {self.node_id}] [RUTEO-{self.algorithm.upper()}] Proceso iniciado")
        if self.algorithm == "flooding":
            self._ruteo_flooding()
        elif self.algorithm == "lsr":
            self._ruteo_lsr()

    def _ruteo_flooding(self):
        
        # Inicializar la Tabla de Ruteo
        self._initialize_routing_table()
        
        # Enviar paquetes de info inicial
        self._send_initial_routing_info()
        
        routing_info_timer = 0
        table_update_timer = 0
        
        while self.running.value:
            try:
                # 1. Consultar paquetes de Info entrantes
                while not self.routing_info_queue.empty():
                    message, addr = self.routing_info_queue.get()
                    self._process_routing_info(message, addr)
                
                # 2. Consultar nuevos nodos entrantes
                while not self.new_nodes_queue.empty():
                    new_node_info = self.new_nodes_queue.get()
                    self._process_new_node(new_node_info)
                
                # 3. Armar y enviar paquetes de Info periódicamente (cada 5 segundos)
                if routing_info_timer >= 50:  # 50 * 0.1 = 5 segundos
                    self._send_routing_info_packets()
                    routing_info_timer = 0
                
                # 4. Actualizar tablas según algoritmo (cada 3 segundos)
                if table_update_timer >= 30:  # 30 * 0.1 = 3 segundos
                    self._update_routing_tables()
                    table_update_timer = 0
                
                routing_info_timer += 1
                table_update_timer += 1
                time.sleep(0.1)
                
            except Exception as e:
                print(f"[Nodo {self.node_id}] [RUTEO-FLOODING] Error: {e}")
                time.sleep(1)

    def _ruteo_lsr(self):
        
        # Inicializar LSR
        lsr = LSR(self.node_id, self.neighbor_costs)
        
        # Enviar LSP inicial
        initial_lsp = lsr.create_lsp()
        self._broadcast_lsp(initial_lsp)
        
        lsp_timer = 0
        hello_timer = 0
        
        while self.running.value:
            try:
                # 1. Procesar LSPs entrantes
                while not self.lsp_queue.empty():
                    lsp_message, addr = self.lsp_queue.get()
                    forwards = lsr.process_lsp(lsp_message)
                    
                    # Reenviar LSPs según el algoritmo
                    for neighbor_id, lsp_to_forward in forwards:
                        self._forward_lsp(neighbor_id, lsp_to_forward)
                
                # 2. Procesar mensajes de hello para descubrir vecinos
                while not self.routing_info_queue.empty():
                    message, addr = self.routing_info_queue.get()
                    if message.get("type") == "hello":
                        self._process_hello_lsr(message, addr)
                
                # 3. Enviar LSPs periódicamente (cada 30 segundos)
                if lsp_timer >= 300:  # 300 * 0.1 = 30 segundos
                    if lsr.should_send_lsp():
                        new_lsp = lsr.create_lsp()
                        self._broadcast_lsp(new_lsp)
                        lsr.last_lsp_time = time.time()
                    lsp_timer = 0
                
                # 4. Enviar hello messages (cada 10 segundos)
                if hello_timer >= 100:  # 100 * 0.1 = 10 segundos
                    self._send_hello_lsr()
                    hello_timer = 0
                
                # 5. Actualizar tabla de ruteo compartida
                self._update_shared_routing_table_lsr(lsr)
                
                lsp_timer += 1
                hello_timer += 1
                time.sleep(0.1)
                
            except Exception as e:
                print(f"[Nodo {self.node_id}] [RUTEO-LSR] Error: {e}")
                time.sleep(1)

    def forwarding(self):
        
        
        self.log.write(f"[Nodo {self.node_id}] [FORWARDING-{self.algorithm.upper()}] Proceso iniciado")
        if self.algorithm == "flooding":
            self._forwarding_flooding()
        elif self.algorithm == "lsr":
            self._forwarding_lsr()

    def _forwarding_flooding(self):
        
        # Inicializar algoritmo de flooding
        neighbor_addresses = [self.names.get(n, f"{n}@localhost") for n in self.neighbors]
        flooding = Flooding(self.my_address, neighbor_addresses)
        
        while self.running.value:
            try:
                # Procesar paquetes entrantes
                while not self.incoming_packets_queue.empty():
                    message, addr = self.incoming_packets_queue.get()
                    self._process_incoming_packet_flooding(message, addr, flooding)
                
                time.sleep(0.1)
                
            except Exception as e:
                print(f"[Nodo {self.node_id}] [FORWARDING-FLOODING] Error: {e}")
                time.sleep(1)

    def _forwarding_lsr(self):
        
        while self.running.value:
            try:
                # Procesar paquetes entrantes
                while not self.incoming_packets_queue.empty():
                    message, addr = self.incoming_packets_queue.get()
                    self._process_incoming_packet_lsr(message, addr)
                
                time.sleep(0.1)
                
            except Exception as e:
                print(f"[Nodo {self.node_id}] [FORWARDING-LSR] Error: {e}")
                time.sleep(1)

    def _broadcast_lsp(self, lsp):
        
        for neighbor_id in self.neighbors:
            neighbor_port = 5000 + ord(neighbor_id) - ord('A')
            self.outgoing_packets_queue.put(("127.0.0.1", neighbor_port, lsp))
        self.log.write(f"[Nodo {self.node_id}] [LSR] LSP difundido a {len(self.neighbors)} vecinos")

    def _forward_lsp(self, neighbor_id, lsp):
        
        neighbor_port = 5000 + ord(neighbor_id) - ord('A')
        self.outgoing_packets_queue.put(("127.0.0.1", neighbor_port, lsp))

        self.log.write(f"[Nodo {self.node_id}] [LSR] LSP reenviado a {neighbor_id}")

    def _send_hello_lsr(self):
        
        hello_msg = Mensajes_Protocolo.create_hello_message(self.my_address, "lsr")
        
        for neighbor_id in self.neighbors:
            neighbor_port = 5000 + ord(neighbor_id) - ord('A')
            self.outgoing_packets_queue.put(("127.0.0.1", neighbor_port, hello_msg))
        
        self.log.write(f"[Nodo {self.node_id}] [LSR] HELLO enviado a vecinos")

    def _process_hello_lsr(self, message, addr):
        
        from_addr = message.get("from")
        
        if from_addr and from_addr != self.my_address:
            with self.lock:
                self.shared_discovered_nodes[from_addr] = {
                    'port': addr[1],
                    'last_seen': time.time()
                }
                self.shared_neighbor_ports[from_addr] = addr[1]
            
            self.log.write(f"[Nodo {self.node_id}] [LSR] Vecino descubierto: {from_addr}")

    def _update_shared_routing_table_lsr(self, lsr):
        
        lsr_table = lsr.get_routing_table()
        
        with self.lock:
            self.shared_routing_table.clear()
            for dest, info in lsr_table.items():
                dest_addr = self.names.get(dest, f"{dest}@localhost")
                next_hop_addr = self.names.get(info["next_hop"], f"{info['next_hop']}@localhost")
                
                # Obtener puerto del next hop
                next_hop_port = None
                if info["next_hop"] in self.shared_neighbor_ports:
                    next_hop_port = self.shared_neighbor_ports[info["next_hop"]]
                else:
                    next_hop_port = 5000 + ord(info["next_hop"]) - ord('A')
                
                self.shared_routing_table[dest_addr] = {
                    'next_hop': next_hop_addr,
                    'distance': info["cost"],
                    'interface': f"127.0.0.1:{next_hop_port}",
                    'timestamp': time.time()
                }

    def _process_incoming_packet_lsr(self, message, addr):
        
        msg_type = message.get("type")
        from_addr = message.get("from")
        to_addr = message.get("to")
        

        
        self.log.write(f"[Nodo {self.node_id}] [FORWARDING-LSR] Paquete: {msg_type} de {from_addr} hacia {to_addr}")
        # Si el mensaje es para nosotros
        if to_addr == self.my_address or self._address_to_node_id(to_addr) == self.node_id:
            if msg_type == "message":
                payload = message.get("payload", {})
                data = payload.get("data", "")
                print(f"[Nodo {self.node_id}] [LSR] 📨 MENSAJE RECIBIDO de {from_addr}: '{data}'")

            return
        
        # Si es un mensaje de datos, usar tabla de ruteo para reenviar
        if msg_type == "message":
            self._forward_packet_lsr(message)

    def _forward_packet_lsr(self, message):
        
        to_addr = message.get("to")
        
        # Buscar en la tabla de ruteo
        with self.lock:
            routing_table = dict(self.shared_routing_table)
        
        if to_addr in routing_table:
            next_hop_info = routing_table[to_addr]
            next_hop = next_hop_info['next_hop']
            interface = next_hop_info['interface']
            
            # Extraer puerto de la interfaz
            port = int(interface.split(':')[1])
            


            self.log.write(f"[Nodo {self.node_id}] [LSR] 🔄 Reenviando a {to_addr} vía {next_hop} ({port})")
            self.outgoing_packets_queue.put(("127.0.0.1", port, message))
        else:
            self.log.write(f"[Nodo {self.node_id}] [LSR] ❌ No hay ruta hacia {to_addr}")

    # Métodos existentes para flooding (conservados)
    def _initialize_routing_table(self):
        

        
        self.log.write(f"[Nodo {self.node_id}] [RUTEO] Inicializando tabla de ruteo")
        with self.lock:
            # Agregar vecinos directos a la tabla
            for neighbor in self.neighbors:
                neighbor_addr = self.names.get(neighbor, f"{neighbor}@localhost")
                neighbor_port = 5000 + ord(neighbor) - ord('A')
                
                self.shared_routing_table[neighbor_addr] = {
                    'next_hop': neighbor_addr,
                    'distance': 1,
                    'interface': f"127.0.0.1:{neighbor_port}",
                    'timestamp': time.time()
                }

            self.log.write(f"[Nodo {self.node_id}] [RUTEO] Tabla inicializada con {len(self.shared_routing_table)} entradas")
                
       

    def _send_initial_routing_info(self):
        
        hello_msg = Mensajes_Protocolo.create_hello_message(self.my_address, self.algorithm)
        
        for neighbor_id in self.neighbors:
            neighbor_port = 5000 + ord(neighbor_id) - ord('A')

            self.log.write(f"[Nodo {self.node_id}] [RUTEO] Enviando HELLO inicial a {neighbor_id}")
            self.outgoing_packets_queue.put(("127.0.0.1", neighbor_port, hello_msg))

    def _send_routing_info_packets(self):
        

        
        self.log.write(f"[Nodo {self.node_id}] [RUTEO] Enviando paquetes de info de ruteo")
        # Crear paquete con información de la tabla de ruteo
        with self.lock:
            routing_info = dict(self.shared_routing_table)
            discovered_nodes = dict(self.shared_discovered_nodes)
        
        routing_packet = {
            "type": "routing_info",
            "proto": self.algorithm,
            "from": self.my_address,
            "timestamp": time.time(),
            "routing_table": routing_info,
            "neighbors": self.neighbors
        }
        
        # Solo enviar a vecinos que han respondido (están en discovered_nodes)
        active_neighbors = []
        for neighbor_id in self.neighbors:
            neighbor_addr = self.names.get(neighbor_id, f"{neighbor_id}@localhost")
            if neighbor_addr in discovered_nodes:
                neighbor_port = 5000 + ord(neighbor_id) - ord('A')
                active_neighbors.append((neighbor_id, neighbor_port))
                self.outgoing_packets_queue.put(("127.0.0.1", neighbor_port, routing_packet))
        
        if active_neighbors:
            neighbor_list = [f"{n_id}({n_port})" for n_id, n_port in active_neighbors]
            self.log.write(f"[Nodo {self.node_id}] [RUTEO] Enviado info a vecinos activos: {neighbor_list}")

        else:
            self.log.write(f"[Nodo {self.node_id}] [RUTEO] No hay vecinos activos para enviar info")

    def _process_routing_info(self, message, addr):
        
        msg_type = message.get("type")
        from_addr = message.get("from")
        

        
        self.log.write(f"[Nodo {self.node_id}] [RUTEO] Procesando {msg_type} de {from_addr}")

        if msg_type == "hello":
            # Nuevo vecino descubierto
            if from_addr and from_addr != self.my_address:
                with self.lock:
                    self.shared_discovered_nodes[from_addr] = {
                        'port': addr[1],
                        'last_seen': time.time()
                    }
                    self.shared_neighbor_ports[from_addr] = addr[1]
                
                # Notificar al proceso de nuevos nodos
                self.new_nodes_queue.put({
                    'node_address': from_addr,
                    'port': addr[1],
                    'type': 'neighbor'
                })
                
        elif msg_type == "routing_info":
            # Información de tabla de ruteo de otro nodo
            remote_table = message.get("routing_table", {})
            self._merge_routing_info(from_addr, remote_table)

    def _process_new_node(self, new_node_info):
        
        node_addr = new_node_info['node_address']
        node_port = new_node_info['port']
        
        
        self.log.write(f"[Nodo {self.node_id}] [RUTEO] Procesando nuevo nodo: {node_addr}")
        # Actualizar tabla de ruteo con el nuevo nodo
        with self.lock:
            if node_addr not in self.shared_routing_table:
                self.shared_routing_table[node_addr] = {
                    'next_hop': node_addr,
                    'distance': 1,
                    'interface': f"127.0.0.1:{node_port}",
                    'timestamp': time.time()
                }
                self.log.write(f"[Nodo {self.node_id}] [RUTEO] Nuevo nodo agregado a tabla: {node_addr}")


    def _merge_routing_info(self, from_addr, remote_table):
        

        
        self.log.write(f"[Nodo {self.node_id}] [RUTEO] Fusionando info de ruteo de {from_addr}")
        with self.lock:
            updated_entries = 0
            
            for dest_addr, remote_info in remote_table.items():
                if dest_addr == self.my_address:
                    continue  # Ignorar rutas hacia nosotros mismos
                
                remote_distance = remote_info.get('distance', float('inf')) + 1
                
                # Si no tenemos ruta o encontramos una mejor
                if (dest_addr not in self.shared_routing_table or 
                    self.shared_routing_table[dest_addr]['distance'] > remote_distance):
                    
                    # Encontrar interfaz hacia el nodo que nos dio la info
                    next_hop_interface = None
                    if from_addr in self.shared_neighbor_ports:
                        port = self.shared_neighbor_ports[from_addr]
                        next_hop_interface = f"127.0.0.1:{port}"
                    
                    if next_hop_interface:
                        self.shared_routing_table[dest_addr] = {
                            'next_hop': from_addr,
                            'distance': remote_distance,
                            'interface': next_hop_interface,
                            'timestamp': time.time()
                        }
                        updated_entries += 1
            
            if updated_entries > 0:
                self.log.write(f"[Nodo {self.node_id}] [RUTEO] Actualizadas {updated_entries} entradas en la tabla")

    def _update_routing_tables(self):
        
        with self.lock:
            current_table = dict(self.shared_routing_table)
        

        
        self.log.write(f"[Nodo {self.node_id}] [RUTEO] 📋 Tabla actual: {len(current_table)} entradas")

        # Limpiar entradas antiguas (más de 120 segundos - más tolerante)
        current_time = time.time()
        with self.lock:
            expired_entries = []
            for dest, info in list(self.shared_routing_table.items()):
                if current_time - info['timestamp'] > 120:
                    expired_entries.append(dest)
            
            for dest in expired_entries:
                del self.shared_routing_table[dest]
                
            if expired_entries:
                self.log.write(f"[Nodo {self.node_id}] [RUTEO] Eliminadas {len(expired_entries)} entradas expiradas")


    def _process_incoming_packet_flooding(self, message, addr, flooding):
        
        msg_type = message.get("type")
        from_addr = message.get("from")
        to_addr = message.get("to")
        

        
        self.log.write(f"[Nodo {self.node_id}] [FORWARDING] Paquete entrante: {msg_type} de {from_addr} hacia {to_addr}")

        # Si es un mensaje de datos, usar flooding para forwarding
        if msg_type == "message":
            proto = message.get("proto")
            
            if proto == "flooding":
                # Convertir direcciones a node_id simple para flooding
                from_node_id = self._address_to_node_id(from_addr)
                to_node_id = self._address_to_node_id(to_addr)
                
                # Convertir mensaje al formato esperado por flooding
                flooding_msg = {
                    "msg_id": message.get("msg_id", f"{from_node_id}-{time.time()}"),
                    "from_node": from_node_id,
                    "to": to_node_id,
                    "ttl": message.get("ttl", 5),
                    "payload": message.get("payload", {}).get("data", "")
                }
                
                # Procesar con flooding
                forwards = flooding.receive_message(flooding_msg)
                
                # Si es para nosotros, ya flooding lo procesó
                if to_node_id == self.node_id:
                    return
                
                # Reenviar según flooding
                for neighbor_node_id, new_msg in forwards:
                    neighbor_addr = self.names.get(neighbor_node_id, f"{neighbor_node_id}@localhost")
                    self._forward_packet_flooding(neighbor_addr, new_msg)

    def _address_to_node_id(self, address):
        
        if not address:
            return None
        
        # Buscar en names dict
        for node_id, addr in self.names.items():
            if addr == address:
                return node_id
        
        # Si no se encuentra, extraer de la dirección
        if "@" in address:
            return address.split("@")[0].replace("node", "").upper()
        
        return address

    def _forward_packet_flooding(self, neighbor_addr, message):
        
        neighbor_port = None
        
        # Buscar puerto del vecino
        with self.lock:
            neighbor_ports = dict(self.shared_neighbor_ports)
        
        if neighbor_addr in neighbor_ports:
            neighbor_port = neighbor_ports[neighbor_addr]
        else:
            # Mapeo por defecto basado en node_id
            for node_id, addr in self.names.items():
                if addr == neighbor_addr:
                    neighbor_port = 5000 + ord(node_id) - ord('A')
                    break
        
        if neighbor_port:

            self.log.write(f"[Nodo {self.node_id}] [FORWARDING] 🔄 Reenviando a {neighbor_addr} ({neighbor_port})")
            # Convertir de vuelta al formato de mensaje original
            original_msg = {
                "type": "message",
                "proto": "flooding",
                "from": message["from_node"],
                "to": message["to"],
                "msg_id": message["msg_id"],
                "ttl": message["ttl"],
                "payload": {"data": message["payload"]}
            }
            self.outgoing_packets_queue.put(("127.0.0.1", neighbor_port, original_msg))
        else:
            self.log.write(f"[Nodo {self.node_id}] [FORWARDING] ❌ No se pudo determinar puerto para {neighbor_addr}")

    def send_data_message(self, destination, data, ttl=5):
        
        dest_addr = self.names.get(destination, f"{destination}@localhost")
        
        # Crear mensaje usando el protocolo
        message = Mensajes_Protocolo.create_data_message(
            self.my_address, 
            self.algorithm,  # Usar el algoritmo configurado
            dest_addr, 
            data, 
            ttl
        )
        
        
        self.log.write(f"[Nodo {self.node_id}] 📤 Enviando mensaje ({self.algorithm.upper()}) a {destination}: '{data}'")
        # Enviar directamente al proceso de forwarding
        self.incoming_packets_queue.put((message, ("127.0.0.1", self.port)))

    def set_neighbor_cost(self, neighbor, cost):
        
        if self.algorithm != "lsr":
            self.log.write(f"[Nodo {self.node_id}] Comando solo disponible para LSR")
            return
        
        if neighbor in self.neighbor_costs:
            old_cost = self.neighbor_costs[neighbor]
            self.neighbor_costs[neighbor] = cost
            self.log.write(f"[Nodo {self.node_id}] Costo a {neighbor} cambiado: {old_cost} → {cost}")
        else:
            self.log.write(f"[Nodo {self.node_id}] Vecino {neighbor} no encontrado")

    def interactive_mode(self):
        
        print(f"\n=== NODO {self.node_id} - MODO INTERACTIVO ({self.algorithm.upper()}) ===")
        print("Comandos disponibles:")
        print("  send <destino> <mensaje>  - Enviar mensaje")
        print("  neighbors                 - Ver vecinos descubiertos")
        print("  table                     - Ver tabla de ruteo")
        if self.algorithm == "lsr":
            print("  cost <vecino> <costo>     - Cambiar costo de vecino")
            print("  topology                  - Ver información de topología")
        print("  quit                      - Salir")
        print("=" * 60)
        
        while self.running.value:
            try:
                cmd = input(f"[{self.node_id}-{self.algorithm.upper()}]> ").strip().split()
                if not cmd:
                    continue
                    
                if cmd[0] == "send" and len(cmd) >= 3:
                    destination = cmd[1]
                    message = " ".join(cmd[2:])
                    self.send_data_message(destination, message)
                    
                elif cmd[0] == "neighbors":
                    with self.lock:
                        discovered = dict(self.shared_discovered_nodes)
                    print(f"Vecinos descubiertos: {list(discovered.keys())}")
                    if self.algorithm == "lsr":
                        print(f"Costos de vecinos: {self.neighbor_costs}")
                    
                elif cmd[0] == "table":
                    with self.lock:
                        table = dict(self.shared_routing_table)
                    print(f"Tabla de ruteo ({self.algorithm.upper()}):")
                    if not table:
                        print("  (vacía)")
                    else:
                        for dest, info in table.items():
                            distance = info.get('distance', info.get('cost', '?'))
                            print(f"  {dest} -> {info['next_hop']} (dist/cost: {distance})")
                
                elif cmd[0] == "cost" and len(cmd) == 3 and self.algorithm == "lsr":
                    neighbor = cmd[1]
                    try:
                        cost = int(cmd[2])
                        self.set_neighbor_cost(neighbor, cost)
                    except ValueError:
                        print("Error: El costo debe ser un número entero")
                
                elif cmd[0] == "topology" and self.algorithm == "lsr":
                    # Mostrar información de topología conocida
                    print("Información de topología conocida:")
                    # Esta información estaría disponible en el proceso LSR
                    # Por simplicidad, mostramos la configuración local
                    print(f"  Vecinos directos: {self.neighbors}")
                    print(f"  Costos: {self.neighbor_costs}")
                    
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

    def main_executor(self):
        
        # Marcar como ejecutándose
        self.running.value = True
        
        # Crear procesos
        p1 = Process(target=self.ruteo, name=f"Ruteo-{self.node_id}-{self.algorithm}")
        p2 = Process(target=self.forwarding, name=f"Forwarding-{self.node_id}-{self.algorithm}")
        p3 = Process(target=self._socket_process, name=f"Socket-{self.node_id}")
        
        procesos = [p1, p2, p3]
        
        print(f"[Nodo {self.node_id}] 🚀 Iniciando {len(procesos)} procesos con algoritmo {self.algorithm.upper()}...")
        
        try:
            # Iniciar todos los procesos
            for p in procesos:
                p.start()
            
            # Esperar un momento para que se inicialicen
            time.sleep(2)
            
            # Ejecutar modo interactivo en proceso principal
            self.interactive_mode()
            
        except KeyboardInterrupt:
            print(f"[Nodo {self.node_id}] 🛑 Deteniendo nodo...")
            self.stop()
            
        finally:
            # Terminar procesos
            for p in procesos:
                if p.is_alive():
                    p.terminate()
                    p.join(timeout=5)
                    if p.is_alive():
                        p.kill()
        
        print(f"[Nodo {self.node_id}] ✅ Nodo detenido completamente")

    def stop(self):
        
        self.running.value = False
        print(f"[Nodo {self.node_id}] Señal de parada enviada")

