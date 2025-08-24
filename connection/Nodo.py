from multiprocessing import Process, Manager, Lock, Queue
import time
import json
from connection.TablaRuteo import TablaRuteo
from connection.socket_manager import SocketManager
from connection.Mensajes import Mensajes_Protocolo
from connection.Red import RedConfig
from algoritmos.Flodding import Flooding
from algoritmos.LSR import LSR

class Nodo:
    def __init__(self, node_id, host="127.0.0.1", port=5000, topology_file="data/topo.txt", names_file="data/id_nodos.txt"):
        self.node_id = node_id
        self.host = host
        self.port = port
        
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
        
        # Cargar configuración
        self.topology = RedConfig.load_topology(topology_file)
        self.names = RedConfig.load_names(names_file)
        
        # Obtener mis vecinos y dirección
        self.neighbors = self.topology.get(node_id, [])
        self.my_address = self.names.get(node_id, f"{node_id}@localhost")
        
        # Inicializar datos del nodo
        self.shared_node_info.update({
            'node_id': node_id,
            'address': self.my_address,
            'neighbors': self.neighbors
        })
        
        print(f"[Nodo {self.node_id}] Inicializado en {host}:{port}")
        print(f"[Nodo {self.node_id}] Dirección: {self.my_address}")
        print(f"[Nodo {self.node_id}] Vecinos: {self.neighbors}")

    def _socket_process(self):
        """Proceso dedicado para manejo de sockets"""
        # Crear socket manager en este proceso
        socket_manager = SocketManager(host=self.host, port=self.port)
        socket_manager.on_message = self._on_message_multiprocess
        
        print(f"[Nodo {self.node_id}] Socket iniciado en proceso separado")
        socket_manager.start_server()
        
        # Manejo de mensajes salientes
        while self.running.value:
            try:
                if not self.outgoing_packets_queue.empty():
                    host, port, message = self.outgoing_packets_queue.get(timeout=0.1)
                    socket_manager.send_message(host, port, message)
                    print(f"[Nodo {self.node_id}] [SOCKET] 📤 Enviado a {host}:{port}")
                time.sleep(0.1)
            except:
                continue
        
        socket_manager.stop()

    def _on_message_multiprocess(self, raw_message, addr):
        """Callback para mensajes que distribuye según el tipo"""
        try:
            if isinstance(raw_message, str):
                message = json.loads(raw_message)
            else:
                message = raw_message
            
            msg_type = message.get("type")
            
            print(f"[Nodo {self.node_id}] [SOCKET] 📨 Recibido {msg_type} de {addr}")
            
            # Todos los mensajes van primero a incoming_packets para forwarding
            self.incoming_packets_queue.put((message, addr))
            
            # Los mensajes de info de ruteo también van a la cola de ruteo
            if msg_type in ["hello", "routing_info", "node_discovery"]:
                self.routing_info_queue.put((message, addr))
                
        except Exception as e:
            print(f"[Nodo {self.node_id}] [SOCKET] Error procesando mensaje: {e}")

    def ruteo(self):
        """
        Proceso de RUTEO - Maneja:
        - Inicializar la Tabla de Ruteo
        - Armar paquetes de Info
        - Consultar paquetes de Info y nuevos nodos entrantes
        - Utilizar paquetes de info para resolver y actualizar las tablas según cada algoritmo
        """
        print(f"[Nodo {self.node_id}] [RUTEO] Proceso iniciado")
        
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
                print(f"[Nodo {self.node_id}] [RUTEO] Error: {e}")
                time.sleep(1)

    def forwarding(self):
        """
        Proceso de FORWARDING - Maneja:
        - Paquetes entrantes y salientes
        - Decisiones de reenvío usando algoritmos (flooding, etc.)
        - Entrega de mensajes al destino final
        """
        print(f"[Nodo {self.node_id}] [FORWARDING] Proceso iniciado")
        
        # Inicializar algoritmo de flooding
        neighbor_addresses = [self.names.get(n, f"{n}@localhost") for n in self.neighbors]
        flooding = Flooding(self.my_address, neighbor_addresses)
        
        while self.running.value:
            try:
                # Procesar paquetes entrantes
                while not self.incoming_packets_queue.empty():
                    message, addr = self.incoming_packets_queue.get()
                    self._process_incoming_packet(message, addr, flooding)
                
                time.sleep(0.1)
                
            except Exception as e:
                print(f"[Nodo {self.node_id}] [FORWARDING] Error: {e}")
                time.sleep(1)

    def _initialize_routing_table(self):
        """Inicializa la tabla de ruteo con vecinos directos"""
        print(f"[Nodo {self.node_id}] [RUTEO] Inicializando tabla de ruteo")
        
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
                
            print(f"[Nodo {self.node_id}] [RUTEO] Tabla inicializada con {len(self.shared_routing_table)} entradas")

    def _send_initial_routing_info(self):
        """Envía paquetes de info inicial (HELLO messages)"""
        hello_msg = Mensajes_Protocolo.create_hello_message(self.my_address, "flooding")
        
        for neighbor_id in self.neighbors:
            neighbor_port = 5000 + ord(neighbor_id) - ord('A')
            print(f"[Nodo {self.node_id}] [RUTEO] Enviando HELLO inicial a {neighbor_id}")
            self.outgoing_packets_queue.put(("127.0.0.1", neighbor_port, hello_msg))

    def _send_routing_info_packets(self):
        """Arma y envía paquetes de información de ruteo - solo a vecinos activos"""
        print(f"[Nodo {self.node_id}] [RUTEO] Enviando paquetes de info de ruteo")
        
        # Crear paquete con información de la tabla de ruteo
        with self.lock:
            routing_info = dict(self.shared_routing_table)
            discovered_nodes = dict(self.shared_discovered_nodes)
        
        routing_packet = {
            "type": "routing_info",
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
            print(f"[Nodo {self.node_id}] [RUTEO] Enviado info a vecinos activos: {neighbor_list}")
        else:
            print(f"[Nodo {self.node_id}] [RUTEO] No hay vecinos activos para enviar info")

    def _process_routing_info(self, message, addr):
        """Procesa paquetes de información de ruteo recibidos"""
        msg_type = message.get("type")
        from_addr = message.get("from")
        
        print(f"[Nodo {self.node_id}] [RUTEO] Procesando {msg_type} de {from_addr}")
        
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
        """Procesa información de nuevos nodos entrantes"""
        node_addr = new_node_info['node_address']
        node_port = new_node_info['port']
        
        print(f"[Nodo {self.node_id}] [RUTEO] Procesando nuevo nodo: {node_addr}")
        
        # Actualizar tabla de ruteo con el nuevo nodo
        with self.lock:
            if node_addr not in self.shared_routing_table:
                self.shared_routing_table[node_addr] = {
                    'next_hop': node_addr,
                    'distance': 1,
                    'interface': f"127.0.0.1:{node_port}",
                    'timestamp': time.time()
                }
                print(f"[Nodo {self.node_id}] [RUTEO] Nuevo nodo agregado a tabla: {node_addr}")

    def _merge_routing_info(self, from_addr, remote_table):
        """Utiliza paquetes de info para resolver y actualizar las tablas"""
        print(f"[Nodo {self.node_id}] [RUTEO] Fusionando info de ruteo de {from_addr}")
        
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
                print(f"[Nodo {self.node_id}] [RUTEO] Actualizadas {updated_entries} entradas en la tabla")

    def _update_routing_tables(self):
        """Actualiza las tablas según el algoritmo implementado"""
        with self.lock:
            current_table = dict(self.shared_routing_table)
        
        print(f"[Nodo {self.node_id}] [RUTEO] 📋 Tabla actual: {len(current_table)} entradas")
        
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
                print(f"[Nodo {self.node_id}] [RUTEO] Eliminadas {len(expired_entries)} entradas expiradas")

    def _process_incoming_packet(self, message, addr, flooding):
        """Procesa paquetes entrantes en el proceso de forwarding"""
        msg_type = message.get("type")
        from_addr = message.get("from")
        to_addr = message.get("to")
        
        print(f"[Nodo {self.node_id}] [FORWARDING] Paquete entrante: {msg_type} de {from_addr} hacia {to_addr}")
        
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
                    self._forward_packet(neighbor_addr, new_msg)

    def _address_to_node_id(self, address):
        """Convierte dirección completa a node_id simple"""
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

    def _forward_packet(self, neighbor_addr, message):
        """Reenvía un paquete a un vecino específico"""
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
            print(f"[Nodo {self.node_id}] [FORWARDING] 🔄 Reenviando a {neighbor_addr} ({neighbor_port})")
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
            print(f"[Nodo {self.node_id}] [FORWARDING] ❌ No se pudo determinar puerto para {neighbor_addr}")

    def send_data_message(self, destination, data, ttl=5):
        """Envía un mensaje de datos usando flooding"""
        dest_addr = self.names.get(destination, f"{destination}@localhost")
        
        # Crear mensaje usando el protocolo
        message = Mensajes_Protocolo.create_data_message(
            self.my_address, 
            "flooding",
            dest_addr, 
            data, 
            ttl
        )
        
        print(f"[Nodo {self.node_id}] 📤 Enviando mensaje a {destination}: '{data}'")
        
        # Enviar directamente al proceso de forwarding
        self.incoming_packets_queue.put((message, ("127.0.0.1", self.port)))

    def interactive_mode(self):
        """Modo interactivo que corre en el proceso principal"""
        print(f"\n=== NODO {self.node_id} - MODO INTERACTIVO ===")
        print("Comandos disponibles:")
        print("  send <destino> <mensaje>  - Enviar mensaje")
        print("  neighbors                 - Ver vecinos descubiertos")
        print("  table                     - Ver tabla de ruteo")
        print("  quit                      - Salir")
        print("=" * 50)
        
        while self.running.value:
            try:
                cmd = input(f"[{self.node_id}]> ").strip().split()
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
                    
                elif cmd[0] == "table":
                    with self.lock:
                        table = dict(self.shared_routing_table)
                    print("Tabla de ruteo:")
                    for dest, info in table.items():
                        print(f"  {dest} -> {info['next_hop']} (dist: {info['distance']})")
                    
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
        """Ejecutor principal que maneja los procesos paralelos"""
        # Marcar como ejecutándose
        self.running.value = True
        
        # Crear procesos
        p1 = Process(target=self.ruteo, name=f"Ruteo-{self.node_id}")
        p2 = Process(target=self.forwarding, name=f"Forwarding-{self.node_id}")
        p3 = Process(target=self._socket_process, name=f"Socket-{self.node_id}")
        
        procesos = [p1, p2, p3]
        
        print(f"[Nodo {self.node_id}] 🚀 Iniciando {len(procesos)} procesos...")
        
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
        """Detiene el nodo"""
        self.running.value = False
        print(f"[Nodo {self.node_id}] Señal de parada enviada")