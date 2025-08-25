from multiprocessing import Process, Manager, Lock, Queue
import time
import json
from connection.socket_manager import SocketManager
from connection.Mensajes import Mensajes_Protocolo
from connection.Red import RedConfig
from connection.Red import Red
from algoritmos.Flodding import Flooding
from algoritmos.LSR import LSR
from algoritmos.DJstra import SolveDjstra
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
        if self.algorithm not in ["flooding", "lsr", "dijkstra"]:
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

        if self.algorithm == "dijkstra":
        
            self._initialize_dijkstra_network()

    def _initialize_dijkstra_network(self):

        # Crear mapeo de node_id a índices numéricos
        self.node_to_index = {}
        self.index_to_node = {}
        all_nodes = set([self.node_id])
        all_nodes.update(self.neighbors)
        
        # Agregar más nodos de la topología si están disponibles
        for node_id, neighbors in self.topology.items():
            all_nodes.add(node_id)
            all_nodes.update(neighbors)
        
        # Crear mapeo bidireccional
        for i, node_id in enumerate(sorted(all_nodes)):
            self.node_to_index[node_id] = i
            self.index_to_node[i] = node_id
        
        # Crear objeto Red
        self.dijkstra_network = Red(len(all_nodes))
        
        # Inicializar con infinito
        for i in range(len(all_nodes)):
            for j in range(len(all_nodes)):
                if i == j:
                    self.dijkstra_network.graph[i][j] = 0
                else:
                    self.dijkstra_network.graph[i][j] = float('inf')
        
        # Agregar conexiones conocidas de la topología
        for node_id, neighbors in self.topology.items():
            if node_id in self.node_to_index:
                src_idx = self.node_to_index[node_id]
                for neighbor in neighbors:
                    if neighbor in self.node_to_index:
                        dest_idx = self.node_to_index[neighbor]
                        # Costo por defecto 1, puede ser modificado
                        cost = self.neighbor_costs.get(neighbor, 1) if node_id == self.node_id else 1
                        self.dijkstra_network.graph[src_idx][dest_idx] = cost
        
        # Crear solver
        self.dijkstra_solver = SolveDjstra(self.dijkstra_network)
        
        self.log.write(f"[Nodo {self.node_id}] Red Dijkstra inicializada con {len(all_nodes)} nodos")

    def _ruteo_dijkstra(self):

        # Inicializar tabla de ruteo
        self._initialize_routing_table()
        
        # Enviar información inicial
        self._send_initial_routing_info()
        
        # Calcular rutas iniciales con Dijkstra
        self._update_dijkstra_routing_table()
        
        routing_info_timer = 0
        dijkstra_update_timer = 0
        topology_update_timer = 0
        
        while self.running.value:
            try:
                # 1. Procesar información de ruteo entrante
                while not self.routing_info_queue.empty():
                    message, addr = self.routing_info_queue.get()
                    self._process_routing_info_dijkstra(message, addr)
                
                # 2. Procesar nuevos nodos
                while not self.new_nodes_queue.empty():
                    new_node_info = self.new_nodes_queue.get()
                    self._process_new_node_dijkstra(new_node_info)
                
                # 3. Enviar información periódicamente (cada 10 segundos)
                if routing_info_timer >= 100:
                    self._send_dijkstra_info_packets()
                    routing_info_timer = 0
                
                # 4. Actualizar topología y recalcular rutas (cada 15 segundos)
                if dijkstra_update_timer >= 150:
                    self._update_dijkstra_routing_table()
                    dijkstra_update_timer = 0
                
                # 5. Actualizar información de topología (cada 5 segundos)
                if topology_update_timer >= 50:
                    self._broadcast_topology_info()
                    topology_update_timer = 0
                
                routing_info_timer += 1
                dijkstra_update_timer += 1
                topology_update_timer += 1
                time.sleep(0.1)
                
            except Exception as e:
                self.log.write(f"[Nodo {self.node_id}] [RUTEO-DIJKSTRA] Error: {e}")
                time.sleep(1)
    
    
    def _forwarding_dijkstra(self):
        while self.running.value:
            try:
                while not self.incoming_packets_queue.empty():
                    message, addr = self.incoming_packets_queue.get()
                    msg_type = message.get("type")
                    msg_proto = message.get("proto", "")
                    
                    # Solo procesar mensajes que NO sean de ruteo en forwarding
                    # Los mensajes de ruteo se procesan en el proceso de ruteo
                    if msg_type == "message":
                        self._process_incoming_packet_dijkstra(message, addr)
                    # Los mensajes de ruteo (hello, dijkstra_info, etc.) se ignoran aquí
                    # porque ya se procesan en el proceso de ruteo
                
                time.sleep(0.1)
                
            except Exception as e:
                self.log.write(f"[Nodo {self.node_id}] [FORWARDING-DIJKSTRA] Error: {e}")
                time.sleep(1)

    
    def _update_dijkstra_routing_table(self):
        """Actualiza la tabla de ruteo usando Dijkstra."""
        try:
            src_idx = self.node_to_index[self.node_id]
            routing_table = self.dijkstra_solver.get_routing_table(src_idx)
            
            with self.lock:
                # Limpiar tabla actual
                dijkstra_entries = {}
                
                for dest_idx, route_info in routing_table.items():
                    if route_info['reachable']:
                        dest_node_id = self.index_to_node[dest_idx]
                        next_hop_node_id = self.index_to_node[route_info['next_hop']]
                        
                        dest_addr = self.names.get(dest_node_id, f"{dest_node_id}@localhost")
                        next_hop_addr = self.names.get(next_hop_node_id, f"{next_hop_node_id}@localhost")
                        next_hop_port = 5000 + ord(next_hop_node_id) - ord('A')
                        
                        dijkstra_entries[dest_addr] = {
                            'next_hop': next_hop_addr,
                            'distance': route_info['distance'],
                            'interface': f"127.0.0.1:{next_hop_port}",
                            'timestamp': time.time(),
                            'algorithm': 'dijkstra'
                        }
                
                # Actualizar tabla compartida manteniendo entradas de vecinos directos
                for dest, info in dijkstra_entries.items():
                    self.shared_routing_table[dest] = info
            
            self.log.write(f"[Nodo {self.node_id}] [DIJKSTRA] Tabla actualizada: {len(dijkstra_entries)} rutas")
            
        except Exception as e:
            self.log.write(f"[Nodo {self.node_id}] [DIJKSTRA] Error actualizando tabla: {e}")

    def _process_routing_info_dijkstra(self, message, addr):
        msg_type = message.get("type")
        from_addr = message.get("from")
        
        self.log.write(f"[Nodo {self.node_id}] [RUTEO-DIJKSTRA] Procesando {msg_type} de {from_addr}")
        
        if msg_type == "hello":
            if from_addr and from_addr != self.my_address:
                from_node_id = self._address_to_node_id(from_addr)
                if from_node_id in self.neighbors:
                    real_port = 5000 + ord(from_node_id) - ord('A')
                    
                    with self.lock:
                        self.shared_discovered_nodes[from_addr] = {
                            'port': real_port,
                            'last_seen': time.time()
                        }
                        self.shared_neighbor_ports[from_addr] = real_port
                    
                    # ESTA LÍNEA FALTABA: Agregar a la cola de nuevos nodos
                    self.new_nodes_queue.put({
                        'node_address': from_addr,
                        'port': real_port,
                        'type': 'neighbor'
                    })
                    
                    self.log.write(f"[Nodo {self.node_id}] [DIJKSTRA] Vecino confirmado: {from_addr} ({from_node_id})")
        
        elif msg_type == "dijkstra_info":
            # Procesar información de topología de otros nodos
            self._process_dijkstra_topology_info(message, from_addr)
        
        elif msg_type == "topology_update":
            # Procesar actualizaciones completas de topología
            self._process_dijkstra_topology_info(message, from_addr)

    def _process_dijkstra_topology_info(self, message, from_addr):
        """Procesa información de topología para actualizar el grafo."""
        topology_info = message.get("topology", {})
        costs_info = message.get("costs", {})
        
        updated = False
        from_node_id = self._address_to_node_id(from_addr)
        
        if from_node_id in self.node_to_index:
            from_idx = self.node_to_index[from_node_id]
            
            # Actualizar conexiones conocidas por el nodo remoto
            for dest_node_id, cost in costs_info.items():
                if dest_node_id in self.node_to_index:
                    dest_idx = self.node_to_index[dest_node_id]
                    current_cost = self.dijkstra_network.graph[from_idx][dest_idx]
                    
                    if current_cost != cost:
                        self.dijkstra_network.graph[from_idx][dest_idx] = cost
                        updated = True
            
            if updated:
                self.log.write(f"[Nodo {self.node_id}] [DIJKSTRA] Topología actualizada con info de {from_node_id}")
                # Recalcular rutas después de actualizar topología
                self._update_dijkstra_routing_table()

    def _send_dijkstra_info_packets(self):
        """Envía información de topología a los vecinos."""
        # Crear paquete con información de topología local
        dijkstra_packet = {
            "type": "dijkstra_info",
            "proto": "dijkstra",
            "from": self.my_address,
            "timestamp": time.time(),
            "topology": self.neighbors,
            "costs": self.neighbor_costs
        }
        
        with self.lock:
            discovered_nodes = dict(self.shared_discovered_nodes)
        
        # Enviar solo a vecinos activos
        sent_count = 0
        for neighbor_id in self.neighbors:
            neighbor_addr = self.names.get(neighbor_id, f"{neighbor_id}@localhost")
            if neighbor_addr in discovered_nodes:
                neighbor_port = 5000 + ord(neighbor_id) - ord('A')
                self.outgoing_packets_queue.put(("127.0.0.1", neighbor_port, dijkstra_packet))
                sent_count += 1
        
        if sent_count > 0:
            self.log.write(f"[Nodo {self.node_id}] [DIJKSTRA] Info enviada a {sent_count} vecinos")

    def _broadcast_topology_info(self):
        """Difunde información de topología conocida."""
        # Similar a _send_dijkstra_info_packets pero con más información
        topology_packet = {
            "type": "topology_update",
            "proto": "dijkstra",
            "from": self.my_address,
            "timestamp": time.time(),
            "full_topology": dict(self.topology),
            "known_costs": self.neighbor_costs
        }
        
        with self.lock:
            discovered_nodes = dict(self.shared_discovered_nodes)
        
        for neighbor_id in self.neighbors:
            neighbor_addr = self.names.get(neighbor_id, f"{neighbor_id}@localhost")
            if neighbor_addr in discovered_nodes:
                neighbor_port = 5000 + ord(neighbor_id) - ord('A')
                self.outgoing_packets_queue.put(("127.0.0.1", neighbor_port, topology_packet))

    def _process_new_node_dijkstra(self, new_node_info):
        """Procesa un nuevo nodo descubierto para Dijkstra."""
        node_addr = new_node_info['node_address']
        node_port = new_node_info['port']
        
        self.log.write(f"[Nodo {self.node_id}] [DIJKSTRA] Procesando nuevo nodo: {node_addr}")
        
        # Actualizar tabla de ruteo con nodo directo
        with self.lock:
            if node_addr not in self.shared_routing_table:
                self.shared_routing_table[node_addr] = {
                    'next_hop': node_addr,
                    'distance': 1,
                    'interface': f"127.0.0.1:{node_port}",
                    'timestamp': time.time(),
                    'algorithm': 'dijkstra'
                }
        
        # Recalcular rutas después de agregar nuevo nodo
        self._update_dijkstra_routing_table()

    
    def _process_incoming_packet_dijkstra(self, message, addr):

        msg_type = message.get("type")
        from_addr = message.get("from")
        to_addr = message.get("to")
        msg_proto = message.get("proto", "")
        
        self.log.write(f"[Nodo {self.node_id}] [FORWARDING-DIJKSTRA] Paquete: {msg_type}({msg_proto}) de {from_addr} hacia {to_addr}")
        
        # Si el mensaje es para nosotros
        if to_addr == self.my_address or self._address_to_node_id(to_addr) == self.node_id:
            if msg_type == "message":
                payload = message.get("payload", {})
                data = payload.get("data", "")
                original_sender = message.get("original_sender", from_addr)
                print(f"[Nodo {self.node_id}] [DIJKSTRA] 📨 MENSAJE RECIBIDO de {original_sender}: '{data}'")
                self.log.write(f"[Nodo {self.node_id}] [DIJKSTRA] 📨 MENSAJE RECIBIDO de {original_sender}: '{data}'")
            return
        
        # Si es un mensaje de datos con protocolo dijkstra, usar tabla de ruteo para reenviar
        if msg_type == "message" and msg_proto == "dijkstra":
            self._forward_packet_dijkstra(message)


    def _forward_packet_dijkstra(self, message):
        """Reenvía un paquete usando la tabla de ruteo de Dijkstra."""
        to_addr = message.get("to")
        
        # Buscar en la tabla de ruteo
        with self.lock:
            routing_table = dict(self.shared_routing_table)
        
        if to_addr in routing_table:
            route_info = routing_table[to_addr]
            next_hop = route_info['next_hop']
            interface = route_info['interface']
            
            # Extraer puerto de la interfaz
            port = int(interface.split(':')[1])
            
            self.log.write(f"[Nodo {self.node_id}] [DIJKSTRA] 🔄 Reenviando a {to_addr} vía {next_hop} (dist: {route_info['distance']})")
            self.outgoing_packets_queue.put(("127.0.0.1", port, message))
        else:
            self.log.write(f"[Nodo {self.node_id}] [DIJKSTRA] ❌ No hay ruta hacia {to_addr}")


    def set_neighbor_cost_dijkstra(self, neighbor, cost):
        if self.algorithm != "dijkstra":
            self.log.write(f"[Nodo {self.node_id}] Comando solo disponible para Dijkstra")
            return
        
        if neighbor in self.neighbors:
            old_cost = self.neighbor_costs.get(neighbor, 1)
            self.neighbor_costs[neighbor] = cost
            
            # Actualizar en el grafo de Dijkstra
            if neighbor in self.node_to_index:
                src_idx = self.node_to_index[self.node_id]
                dest_idx = self.node_to_index[neighbor]
                self.dijkstra_network.graph[src_idx][dest_idx] = cost
            
            # Recalcular rutas
            self._update_dijkstra_routing_table()
            
            self.log.write(f"[Nodo {self.node_id}] [DIJKSTRA] Costo a {neighbor} cambiado: {old_cost} → {cost}")
        else:
            self.log.write(f"[Nodo {self.node_id}] [DIJKSTRA] Vecino {neighbor} no encontrado")


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
            
            elif self.algorithm == "dijkstra":
                if msg_type in ["hello", "dijkstra_info", "topology_update", "node_discovery"]:
                    self.routing_info_queue.put((message, addr))
                
                    
        except Exception as e:
            print(f"[Nodo {self.node_id}] [SOCKET] Error procesando mensaje: {e}")

    def ruteo(self):
        
        
        self.log.write(f"[Nodo {self.node_id}] [RUTEO-{self.algorithm.upper()}] Proceso iniciado")
        if self.algorithm == "flooding":
            self._ruteo_flooding()
        elif self.algorithm == "lsr":
            self._ruteo_lsr()
        elif self.algorithm == "dijkstra":  # AGREGAR esta línea
            self._ruteo_dijkstra()

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
        
        elif self.algorithm == "dijkstra":
            print("FORWRW")
            self._forwarding_dijkstra()

    def _forwarding_flooding(self):
        
        # Inicializar algoritmo de flooding con IDs de vecinos (no direcciones)
        flooding = Flooding(self.node_id, self.neighbors)
        
        self.log.write(f"[Nodo {self.node_id}] [FORWARDING-FLOODING] Flooding inicializado con vecinos: {self.neighbors}")
        
        while self.running.value:
            try:
                # Procesar paquetes entrantes
                while not self.incoming_packets_queue.empty():
                    message, addr = self.incoming_packets_queue.get()
                    self._process_incoming_packet_flooding(message, addr, flooding)
                
                time.sleep(0.1)
                
            except Exception as e:
                self.log.write(f"[Nodo {self.node_id}] [FORWARDING-FLOODING] Error: {e}")
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
        
        self.log.write(f"[Nodo {self.node_id}] [RUTEO-FLOODING] Procesando {msg_type} de {from_addr}")

        if msg_type == "hello":
            # Nuevo vecino descubierto
            if from_addr and from_addr != self.my_address:
                from_node_id = self._address_to_node_id(from_addr)
                
                # Verificar que sea realmente nuestro vecino
                if from_node_id in self.neighbors:
                    real_port = 5000 + ord(from_node_id) - ord('A')
                
                    with self.lock:
                        self.shared_discovered_nodes[from_addr] = {
                            'port': real_port,
                            'last_seen': time.time()
                        }
                        self.shared_neighbor_ports[from_addr] = real_port
                    
                    # Notificar al proceso de nuevos nodos
                    self.new_nodes_queue.put({
                        'node_address': from_addr,
                        'port': real_port,
                        'type': 'neighbor'
                    })
                    
                    self.log.write(f"[Nodo {self.node_id}] [RUTEO-FLOODING] Vecino confirmado: {from_addr} ({from_node_id})")
                else:
                    self.log.write(f"[Nodo {self.node_id}] [RUTEO-FLOODING] Nodo {from_node_id} no es vecino directo")
                    
        elif msg_type == "routing_info":
            # Para flooding, la información de ruteo es menos crítica
            # pero aún podemos usarla para descubrir nodos
            remote_table = message.get("routing_table", {})
            self._merge_routing_info_flooding(from_addr, remote_table)


    def _merge_routing_info_flooding(self, from_addr, remote_table):

        
        with self.lock:
            updated_entries = 0
            
            for dest_addr, remote_info in remote_table.items():
                if dest_addr == self.my_address:
                    continue
                
                # Para flooding, todas las rutas son de distancia 1 a través de vecinos
                # o se aprenden dinámicamente
                if dest_addr not in self.shared_routing_table:
                    # Solo agregar si el from_addr es un vecino conocido
                    from_node_id = self._address_to_node_id(from_addr)
                    if from_node_id in self.neighbors:
                        port = self.shared_neighbor_ports.get(from_addr)
                        if port:
                            self.shared_routing_table[dest_addr] = {
                                'next_hop': from_addr,
                                'distance': 2,  # A través de un vecino
                                'interface': f"127.0.0.1:{port}",
                                'timestamp': time.time()
                            }
                            updated_entries += 1
            
            if updated_entries > 0:
                self.log.write(f"[Nodo {self.node_id}] [RUTEO-FLOODING] Descubiertos {updated_entries} nodos adicionales")
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
        proto = message.get("proto", "")
        
        self.log.write(f"[Nodo {self.node_id}] [FORWARDING-FLOODING] Paquete: {msg_type}({proto}) de {from_addr} hacia {to_addr}")
        
        # Solo procesar mensajes de datos con protocolo flooding
        if msg_type == "message" and proto == "flooding":
            # Convertir direcciones a node_id para flooding
            from_node_id = self._address_to_node_id(from_addr) or from_addr
            to_node_id = self._address_to_node_id(to_addr) or to_addr
            
            # Crear mensaje en formato esperado por flooding
            flooding_msg = {
                "msg_id": message.get("msg_id", f"{from_node_id}-{int(time.time() * 1000)}"),
                "from_node": from_node_id,
                "original_sender": message.get("original_sender", from_node_id),
                "to": to_node_id,
                "ttl": message.get("ttl", 5),
                "payload": message.get("payload", {}).get("data", ""),
                "timestamp": message.get("timestamp", time.time())
            }
            
            self.log.write(f"[Nodo {self.node_id}] [FORWARDING-FLOODING] Procesando con flooding: {flooding_msg['msg_id']}")
            
            # Procesar con flooding
            forwards = flooding.receive_message(flooding_msg)
            
            # Si flooding devuelve reenvíos, procesarlos
            for neighbor_id, flood_msg in forwards:
                self._forward_packet_flooding(neighbor_id, flood_msg)

    def _address_to_node_id(self, address):
        """Convierte una dirección a node_id."""
        if not address:
            return None
        
        # Buscar en names dict (dirección -> node_id)
        for node_id, addr in self.names.items():
            if addr == address:
                return node_id
        
        # Si no se encuentra, intentar extraer de la dirección
        if "@" in address:
            node_part = address.split("@")[0]
            # Remover 'node' si está presente y obtener la letra
            node_id = node_part.replace("node", "").upper()
            if len(node_id) == 1 and node_id.isalpha():
                return node_id
        
        # Si es solo una letra, devolverla
        if len(address) == 1 and address.isalpha():
            return address.upper()
        
        return address

    def _forward_packet_flooding(self, neighbor_id, flood_msg):
        """Reenvía un paquete usando flooding a un vecino específico."""
        
        # Obtener dirección del vecino
        neighbor_addr = self.names.get(neighbor_id, f"{neighbor_id}@localhost")
        neighbor_port = 5000 + ord(neighbor_id) - ord('A')
        
        # Convertir mensaje de flooding de vuelta al formato de protocolo
        protocol_msg = {
            "type": "message",
            "proto": "flooding",
            "from": self.names.get(flood_msg["from_node"], f"{flood_msg['from_node']}@localhost"),
            "to": self.names.get(flood_msg["to"], f"{flood_msg['to']}@localhost"),
            "msg_id": flood_msg["msg_id"],
            "original_sender": flood_msg.get("original_sender", flood_msg["from_node"]),
            "ttl": flood_msg["ttl"],
            "timestamp": flood_msg.get("timestamp", time.time()),
            "payload": {"data": flood_msg["payload"]}
        }
        
        self.log.write(f"[Nodo {self.node_id}] [FORWARDING-FLOODING] 🔄 Reenviando {flood_msg['msg_id']} a {neighbor_id} ({neighbor_port})")
        
        # Enviar mensaje
        self.outgoing_packets_queue.put(("127.0.0.1", neighbor_port, protocol_msg))


    def send_data_message(self, destination, data, ttl=5):
        
        
        # Obtener dirección del destino
        dest_addr = self.names.get(destination, f"{destination}@localhost")
        
        # Crear mensaje usando el protocolo
        if self.algorithm == "flooding":
            # Para flooding, crear mensaje con información adicional
            message = {
                "type": "message",
                "proto": "flooding",
                "from": self.my_address,
                "to": dest_addr,
                "msg_id": f"{self.node_id}-{int(time.time() * 1000)}",
                "original_sender": self.node_id,
                "ttl": ttl,
                "timestamp": time.time(),
                "payload": {"data": data}
            }
        elif self.algorithm == "dijkstra":  # AGREGAR esta opción
            message = {
                "type": "message",
                "proto": "dijkstra",
                "from": self.my_address,
                "to": dest_addr,
                "msg_id": f"{self.node_id}-{int(time.time() * 1000)}",
                "original_sender": self.my_address,
                "timestamp": time.time(),
                "payload": {"data": data}
            }
        else:
            # Para otros algoritmos (LSR)
            message = Mensajes_Protocolo.create_data_message(
                self.my_address, 
                self.algorithm,
                dest_addr, 
                data, 
                ttl
            )
        
        self.log.write(f"[Nodo {self.node_id}] 📤 Enviando mensaje ({self.algorithm.upper()}) a {destination}: '{data}'")
        
        # Enviar al proceso de forwarding
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
        if self.algorithm in ["lsr", "dijkstra"]:  # MODIFICAR esta línea
            print("  cost <vecino> <costo>     - Cambiar costo de vecino")
            print("  topology                  - Ver información de topología")
        if self.algorithm == "dijkstra":  # AGREGAR estas líneas
            print("  graph                     - Ver matriz de adyacencia")
            print("  calculate <destino>       - Calcular ruta específica")
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
                    if self.algorithm in ["lsr", "dijkstra"]:
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
                
                elif cmd[0] == "cost" and len(cmd) == 3 and self.algorithm in ["lsr", "dijkstra"]:
                    neighbor = cmd[1]
                    try:
                        cost = int(cmd[2])
                        if self.algorithm == "dijkstra":
                            self.set_neighbor_cost_dijkstra(neighbor, cost)
                        else:
                            self.set_neighbor_cost(neighbor, cost)
                    except ValueError:
                        print("Error: El costo debe ser un número entero")
                
                elif cmd[0] == "graph" and self.algorithm == "dijkstra":  # AGREGAR
                    print("Matriz de adyacencia:")
                    print("Nodos:", [self.index_to_node[i] for i in range(len(self.index_to_node))])
                    for i in range(self.dijkstra_network.V):
                        row = []
                        for j in range(self.dijkstra_network.V):
                            cost = self.dijkstra_network.graph[i][j]
                            if cost == float('inf'):
                                row.append('∞')
                            else:
                                row.append(str(int(cost)))
                        print(f"{self.index_to_node[i]}: {row}")
                
                elif cmd[0] == "calculate" and len(cmd) == 2 and self.algorithm == "dijkstra":  # AGREGAR
                    destination = cmd[1]
                    if destination in self.node_to_index:
                        src_idx = self.node_to_index[self.node_id]
                        dest_idx = self.node_to_index[destination]
                        distance, path_indices = self.dijkstra_solver.get_shortest_path(src_idx, dest_idx)
                        path_nodes = [self.index_to_node[i] for i in path_indices]
                        print(f"Ruta más corta a {destination}: {' -> '.join(path_nodes)} (distancia: {distance})")
                    else:
                        print(f"Nodo {destination} no encontrado")
                
                elif cmd[0] == "topology" and self.algorithm in ["lsr", "dijkstra"]:
                    print("Información de topología conocida:")
                    print(f"  Vecinos directos: {self.neighbors}")
                    print(f"  Costos: {self.neighbor_costs}")
                    if self.algorithm == "dijkstra":
                        print(f"  Nodos conocidos: {list(self.node_to_index.keys())}")
                    
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

