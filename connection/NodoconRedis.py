import time
import threading
import json
from typing import Dict, List, Set, Optional
from connection.redis_manager import RedisManager
from algoritmos.Flodding import Flooding  # Importar la clase que creaste
from logs.Logs import Log
from connection.Mensajes import Messages
from algoritmos.TIPOS import ECHO, INFO, MENSAJE, HOLA
from algoritmos.LSR import LSR
from connection.Red import RedConfig

class NeighborMetrics:
    def __init__(self):
        self.last_seen = 0
        self.last_hello = 0
        self.last_echo_sent = 0 
        self.rtt_samples = []

class Nodo_Redis:
    def __init__(self, node_id, algoritmo, topology_file="data/topo.txt", names_file="data/id_nodos.txt"):
        self.node_id = node_id
        self.running = False
        self.current_algorithm = algoritmo  # Preparado para otros algoritmos
        
        # Configuración de red - se cargará desde Redis
        self.topology = RedConfig.load_topology(topology_file)
        self.names = RedConfig.load_names(names_file)
        self.neighbor_ids = []
        self.my_address = None
        self.log = Log(f"./logs/{node_id}.txt")
        
        # Algoritmos de ruteo (preparado para extensión)
        self.algorithms = {
            "flooding": None,  # Se inicializará después
            "lsr": None,       # Placeholder para LSR
            "dijkstra": None   # Placeholder para Dijkstra
        }
        
        # Tabla de ruteo (compartida entre algoritmos)
        self.routing_table = {}
        
        # Estado de vecinos
        self.neighbor_metrics = {}
        
        # Redis Manager
        self.redis_manager = RedisManager()
        
        # Control de procesos
        self.routing_thread = None
        self.forwarding_thread = None
        self.hello_thread = None
        
        # Locks para thread safety
        self.routing_lock = threading.Lock()
        self.forwarding_lock = threading.Lock()
        
        # Estadísticas
        self.stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "messages_forwarded": 0,
            "hello_sent": 0,
            "hello_received": 0
        }
        
        # Log simplificado
        self.log_file = f"./logs/{node_id}.txt"
        self._init_log()
        
        self.log_message(f"[INIT] Nodo {node_id} inicializado")
    
    def load_config_from_redis(self):
        """Cargar configuración (topología y nombres) desde Redis"""
        try:
            # Intentar obtener configuración de nombres
            names_key = "config:names"
            names_data = self.redis_manager.redis_client.get(names_key)
            if names_data:
                config_data = json.loads(names_data)
                if config_data.get("type") == "names":
                    self.names = config_data.get("config", {})
                    self.log_message(f"[CONFIG] Nombres cargados: {self.names}")
            
            # Intentar obtener configuración de topología
            topo_key = "config:topo"
            topo_data = self.redis_manager.redis_client.get(topo_key)
            if topo_data:
                config_data = json.loads(topo_data)
                if config_data.get("type") == "topo":
                    self.topology = config_data.get("config", {})
                    self.log_message(f"[CONFIG] Topología cargada: {self.topology}")
            
            # Si no se encontró en Redis, usar configuración por defecto
            if not self.names:
                self.names = {
                    "A": "sec10.grupo4.cor22982",
                    "B": "sec10.grupo4.cor22986"
                }
                self.log_message("[CONFIG] Usando nombres por defecto")
            
            if not self.topology:
                self.topology = {
                    "A": ["B"],
                    "B": ["A"]
                }
                self.log_message("[CONFIG] Usando topología por defecto")
            
            # Configurar datos del nodo
            self.neighbor_ids = self.topology.get(self.node_id, [])
            self.my_address = self.names.get(self.node_id)
            
            if not self.my_address:
                raise ValueError(f"No se encontró dirección para nodo {self.node_id}")
            
            # Inicializar métricas de vecinos
            self.neighbor_metrics = {}
            for neighbor_id in self.neighbor_ids:
                self.neighbor_metrics[neighbor_id] = NeighborMetrics()
            
            self.log_message(f"[CONFIG] Dirección: {self.my_address}")
            self.log_message(f"[CONFIG] Vecinos: {self.neighbor_ids}")
            
            return True
            
        except Exception as e:
            self.log_message(f"[CONFIG] Error cargando configuración: {e}")
            return False
    
    def _init_log(self):
        """Inicializar archivo de log"""
        try:
            import os
            os.makedirs("logs", exist_ok=True)
            with open(self.log_file, 'w') as f:
                f.write(f"=== LOG NODO {self.node_id} ===\n")
        except Exception as e:
            print(f"Error inicializando log: {e}")
    
    def log_message(self, message):
        """Escribir mensaje al log"""
        timestamp = time.strftime("%H:%M:%S")
        log_line = f"[{timestamp}] {message}"
        self.log.write(log_line)

    
    def setup_redis(self):
        """Configurar conexión Redis"""
        self.log_message("[REDIS] Configurando conexión...")
        
        if not self.redis_manager.connect():
            return False
        
        if not self.load_config_from_redis():
            return False
        
        # Suscribirse al canal del nodo
        if not self.redis_manager.subscribe_to_channel(self.my_address):
            return False
        
        # Configurar callback para mensajes recibidos
        self.redis_manager.set_message_callback(self.on_redis_message)
        
        # Iniciar escucha de mensajes
        if not self.redis_manager.start_listening():
            return False
        
        self.log_message("[REDIS] Configuración completada")
        return True
    
    def on_redis_message(self, message, channel):
        """Callback para mensajes recibidos desde Redis"""
        try:
            self.stats["messages_received"] += 1
            self.log_message(f"[REDIS] Mensaje recibido en {channel}: {message}")
            self.handle_received_message(message)
        except Exception as e:
            self.log_message(f"[REDIS] Error procesando mensaje: {e}")
    
    def is_neighbor_active(self, neighbor_id, current_time, timeout=15.0):
        """Verificar si un vecino está activo"""
        metrics = self.neighbor_metrics.get(neighbor_id)
        if not metrics:
            return False
        
        if metrics.last_seen == 0:
            return True  # Aún no se ha visto, asumir activo
        
        return (current_time - metrics.last_seen) <= timeout
    
    def send_to_neighbor(self, neighbor_id, message):
        """Enviar mensaje a un vecino específico"""
        try:
            neighbor_addr = self.names.get(neighbor_id)
            if not neighbor_addr:
                self.log_message(f"[SEND] No se encontró dirección para {neighbor_id}")
                return False
            
            # Enviar a través de Redis
            success = self.redis_manager.send_to_neighbor(neighbor_addr, message)
            
            if success:
                self.stats["messages_sent"] += 1
                self.log_message(f"[SEND] Mensaje enviado a {neighbor_id}: {message.get('type', 'unknown')}")
            else:
                self.log_message(f"[SEND] Error enviando a {neighbor_id}")
            
            return success
            
        except Exception as e:
            self.log_message(f"[SEND] Error enviando a {neighbor_id}: {e}")
            return False
    
    def handle_hello_received(self, msg):
        from_addr = msg.get("from")    

        current_alg = self.algorithms.get(self.current_algorithm)
        if current_alg and hasattr(current_alg, 'process_message'):
            current_alg.process_message(self, msg)
        neighbor_id = self.addr_to_id(from_addr)
        if neighbor_id:
            metrics = self.neighbor_metrics[neighbor_id]
            metrics.last_seen = time.time()
            metrics.last_hello = time.time()
        
            echo_msg = Messages.create_echo_message(
                from_addr=self.my_address,
                to_addr=from_addr,
                algorithm=self.current_algorithm,hops=0)

            self.send_to_neighbor(neighbor_id, echo_msg)
    

    def hello_process(self):
        """Proceso de envío de mensajes HELLO optimizado"""
        self.log_message("[HELLO] Proceso iniciado")
        seq_counter = 0
        
        # Configuración de intervalos
        HELLO_INTERVAL = 5.0        # Intervalo base de HELLO
        HELLO_TIMEOUT = 15.0        # Tiempo sin respuesta para considerar vecino inactivo
        MAX_HELLO_INTERVAL = 30.0   # Intervalo máximo para vecinos inactivos
        
        while self.running:
            try:
                seq_counter += 1
                current_time = time.time()
                
                # Enviar HELLO solo cuando sea necesario
                for neighbor_id in self.neighbor_ids:
                    neighbor_addr = self.names.get(neighbor_id)
                    if not neighbor_addr:
                        continue
                    
                    metrics = self.neighbor_metrics.get(neighbor_id)
                    if not metrics:
                        continue
                    
                    # Decidir si enviar HELLO basado en actividad del vecino
                    should_send_hello = self._should_send_hello(neighbor_id, current_time)
                    
                    if should_send_hello:
                        hello_msg = Messages.create_hello_message(
                            from_addr=self.my_address,
                            to_addr=neighbor_addr,
                            hops=4,
                            algorithm=self.current_algorithm
                        )
                        
                        if self.send_to_neighbor(neighbor_id, hello_msg):
                            self.stats["hello_sent"] += 1
                            metrics.last_hello = current_time
                            self.log_message(f"[HELLO] Enviado a {neighbor_id} (último contacto hace {current_time - metrics.last_seen:.1f}s)")
                        else:
                            self.log_message(f"[HELLO] Error enviando a {neighbor_id}")
                    else:
                        # Log de por qué no se envió
                        time_since_last = current_time - metrics.last_seen if metrics.last_seen > 0 else float('inf')
                        time_since_hello = current_time - metrics.last_hello if metrics.last_hello > 0 else float('inf')
                        self.log_message(f"[HELLO] Omitiendo {neighbor_id} - último contacto: {time_since_last:.1f}s, último hello: {time_since_hello:.1f}s")
                
                time.sleep(HELLO_INTERVAL)
                    
            except Exception as e:
                self.log_message(f"[HELLO] ERROR: {e}")
                time.sleep(2.0)

    def _should_send_hello(self, neighbor_id, current_time):
        """Determinar si se debe enviar HELLO a un vecino específico"""
        
        # Configuración de intervalos
        HELLO_INTERVAL = 5.0        # Intervalo normal
        HELLO_TIMEOUT = 15.0        # Timeout para considerar inactivo
        HELLO_RETRY_INTERVAL = 3.0  # Intervalo para vecinos inactivos
        MAX_HELLO_INTERVAL = 30.0   # Intervalo máximo
        
        metrics = self.neighbor_metrics.get(neighbor_id)
        if not metrics:
            return True  # Sin métricas, enviar
        
        # Caso 1: Primer HELLO (nunca se ha enviado)
        if metrics.last_hello == 0:
            self.log_message(f"[HELLO_LOGIC] {neighbor_id}: Primer HELLO")
            return True
        
        # Tiempo transcurrido desde último HELLO enviado
        time_since_hello = current_time - metrics.last_hello
        
        # Caso 2: Vecino activo (responde normalmente)
        if metrics.last_seen > 0:
            time_since_contact = current_time - metrics.last_seen
            
            if time_since_contact <= HELLO_TIMEOUT:
                # Vecino activo - usar intervalo normal
                if time_since_hello >= HELLO_INTERVAL:
                    self.log_message(f"[HELLO_LOGIC] {neighbor_id}: Vecino activo, intervalo normal ({time_since_hello:.1f}s >= {HELLO_INTERVAL}s)")
                    return True
                else:
                    self.log_message(f"[HELLO_LOGIC] {neighbor_id}: Vecino activo, esperando intervalo ({time_since_hello:.1f}s < {HELLO_INTERVAL}s)")
                    return False
            else:
                # Vecino inactivo - usar intervalo de reintentos más frecuente
                if time_since_hello >= HELLO_RETRY_INTERVAL:
                    self.log_message(f"[HELLO_LOGIC] {neighbor_id}: Vecino inactivo, reintentando ({time_since_hello:.1f}s >= {HELLO_RETRY_INTERVAL}s)")
                    return True
                else:
                    self.log_message(f"[HELLO_LOGIC] {neighbor_id}: Vecino inactivo, esperando reintento ({time_since_hello:.1f}s < {HELLO_RETRY_INTERVAL}s)")
                    return False
        
        # Caso 3: Nunca se ha visto respuesta del vecino
        else:
            # Limitar la frecuencia para vecinos que nunca responden
            if time_since_hello >= MAX_HELLO_INTERVAL:
                self.log_message(f"[HELLO_LOGIC] {neighbor_id}: Sin respuesta, reintento máximo ({time_since_hello:.1f}s >= {MAX_HELLO_INTERVAL}s)")
                return True
            elif time_since_hello >= HELLO_RETRY_INTERVAL:
                self.log_message(f"[HELLO_LOGIC] {neighbor_id}: Sin respuesta, reintento normal ({time_since_hello:.1f}s >= {HELLO_RETRY_INTERVAL}s)")
                return True
            else:
                self.log_message(f"[HELLO_LOGIC] {neighbor_id}: Sin respuesta, esperando ({time_since_hello:.1f}s < {HELLO_RETRY_INTERVAL}s)")
                return False

    def get_neighbor_status(self):
        """Obtener estado detallado de todos los vecinos"""
        current_time = time.time()
        status = {}
        
        for neighbor_id in self.neighbor_ids:
            metrics = self.neighbor_metrics.get(neighbor_id)
            if metrics:
                time_since_contact = current_time - metrics.last_seen if metrics.last_seen > 0 else float('inf')
                time_since_hello = current_time - metrics.last_hello if metrics.last_hello > 0 else float('inf')
                
                status[neighbor_id] = {
                    "address": self.names.get(neighbor_id, "N/A"),
                    "active": self.is_neighbor_active(neighbor_id, current_time),
                    "last_seen": metrics.last_seen,
                    "last_hello": metrics.last_hello,
                    "time_since_contact": time_since_contact,
                    "time_since_hello": time_since_hello,
                    "should_send_hello": self._should_send_hello(neighbor_id, current_time)
                }
        
        return status
    
    
    def update_neighbor_activity(self, from_addr):
        neighbor_id = self.addr_to_id(from_addr)
        if neighbor_id and neighbor_id in self.neighbor_metrics:
            current_time = time.time()
            metrics = self.neighbor_metrics[neighbor_id]
            metrics.last_seen = current_time
            self.log_message(f"[NEIGHBOR] Actividad actualizada para {neighbor_id} ({from_addr})")
            return True
        else:
            self.log_message(f"[NEIGHBOR] Dirección desconocida: {from_addr}")
            return False
    
    def handle_echo_received(self, msg):
        from_addr = msg.get("from")
        neighbor_id = self.addr_to_id(from_addr)
        if neighbor_id:
            # Solo actualizar métricas de estado activo
            metrics = self.neighbor_metrics[neighbor_id]
            metrics.last_seen = time.time()
            self.log_message(f"[ECHO] Vecino {neighbor_id} activo")

    def addr_to_id(self, addr):
        for nid, naddr in self.names.items():
            if naddr == addr:
                return nid
        return None

    # =================== PROCESO DE FORWARDING ===================
    
    def forwarding_process(self):
        """Proceso principal de forwarding - maneja mensajes recibidos"""
        self.log_message("[FORWARDING] Proceso iniciado")
        
        # El forwarding ahora es manejado por callbacks de Redis
        # Este proceso solo mantiene el hilo activo
        while self.running:
            try:
                time.sleep(1.0)
            except Exception as e:
                self.log_message(f"[FORWARDING] ERROR: {e}")
                time.sleep(1.0)
    
    def handle_received_message(self, message):
        """Manejar mensaje recibido"""
        with self.forwarding_lock:
            try:
                msg_type = message.get("type", "")
                from_addr = message.get("from", "")
                
                self.log_message(f"[FORWARDING] Procesando {msg_type} de {from_addr}")
                
                # Manejar diferentes tipos de mensajes
                if msg_type in HOLA:
                    self.handle_hello_received(message)
                elif msg_type in ECHO:
                    self.handle_echo_received(message)
                elif msg_type in MENSAJE:
                    # Usar algoritmo actual para procesar
                    current_alg = self.algorithms.get(self.current_algorithm)
                    if current_alg and hasattr(current_alg, 'process_message'):
                        current_alg.process_message(self, message)
                    else:
                        self.log_message(f"[FORWARDING] No hay algoritmo para {self.current_algorithm}")

                elif msg_type in INFO:  # ← AGREGAR ESTA LÍNEA
                    # Mensajes de información (incluye LSP)
                    current_alg = self.algorithms.get(self.current_algorithm)
                    if current_alg and hasattr(current_alg, 'process_message'):
                        current_alg.process_message(self, message)
                    else:
                        self.log_message(f"[FORWARDING] No hay algoritmo para {self.current_algorithm}")
                else:
                    self.log_message(f"[FORWARDING] Tipo de mensaje desconocido: {msg_type}")
                
            except Exception as e:
                self.log_message(f"[FORWARDING] ERROR procesando mensaje: {e}")
    
    # =================== PROCESO DE ROUTING ===================
    
    def routing_process(self):
        """Proceso principal de routing - gestiona información de ruteo"""
        self.log_message("[ROUTING] Proceso iniciado")
        
        while self.running:
            try:
                with self.routing_lock:
                    if self.current_algorithm == "flooding":
                        self._routing_cycle_flooding()
                    elif self.current_algorithm == "lsr":
                        self._routing_cycle_lsr()
                    elif self.current_algorithm == "dijkstra":
                        self._routing_cycle_dijkstra()
                
                time.sleep(10.0)  # Ciclo cada 10 segundos
                
            except Exception as e:
                self.log_message(f"[ROUTING] ERROR: {e}")
                time.sleep(5.0)
    
    def _routing_cycle_flooding(self):
        """Ciclo de routing para Flooding - principalmente envío de HELLO"""
        # Para flooding, el routing principalmente mantiene vecinos activos
        current_time = time.time()
        
        # Verificar vecinos activos
        active_count = 0
        for neighbor_id in self.neighbor_ids:
            if self.is_neighbor_active(neighbor_id, current_time):
                active_count += 1
        
        self.log_message(f"[ROUTING-FLOOD] Vecinos activos: {active_count}/{len(self.neighbor_ids)}")
        
        # Actualizar tabla de ruteo (para flooding es básica)
        self.routing_table = {
            "algorithm": "flooding",
            "active_neighbors": active_count,
            "total_neighbors": len(self.neighbor_ids)
        }
    
    def _routing_cycle_lsr(self):
        lsr_alg = self.algorithms.get("lsr")
        if not lsr_alg:
            self.log_message("[ROUTING-LSR] Algoritmo LSR no disponible")
            return
        
        try:
            # Verificar si debe enviar LSP
            if lsr_alg.should_send_lsp():
                # Crear y enviar LSP a cada vecino
                sent_count = 0
                for neighbor_id in self.neighbor_ids:
                    neighbor_addr = self.names.get(neighbor_id)
                    if neighbor_addr:
                        # Crear LSP específico para cada vecino
                        lsp_msg = lsr_alg.create_lsp_message(neighbor_addr)
                        lsp_msg["from"] = self.my_address  # Establecer dirección de origen
                        
                        if self.send_to_neighbor(neighbor_id, lsp_msg):
                            sent_count += 1
                
                if sent_count > 0:
                    self.log_message(f"[ROUTING-LSR] LSP enviado a {sent_count} vecinos")
            
            # Obtener información de ruteo actualizada
            routing_info = lsr_alg.get_routing_table()
            topology_info = lsr_alg.get_topology_info()
            
            # Actualizar tabla de ruteo compartida
            self.routing_table = {
                "algorithm": "lsr",
                "routes": routing_info,
                "topology": topology_info,
                "known_nodes": topology_info.get("known_nodes", []),
                "total_routes": len(routing_info)
            }
            
            self.log_message(f"[ROUTING-LSR] Tabla actualizada: {len(routing_info)} rutas, {topology_info.get('total_nodes', 0)} nodos conocidos")
            
        except Exception as e:
            self.log_message(f"[ROUTING-LSR] Error en ciclo: {e}")
            
    def get_lsr_stats(self):
        """Obtener estadísticas específicas de LSR"""
        lsr_alg = self.algorithms.get("lsr")
        if lsr_alg:
            return {
                **lsr_alg.get_stats(),
                "topology_info": lsr_alg.get_topology_info(),
                "routing_table": lsr_alg.get_routing_table()
            }
        return {}
    
    def _routing_cycle_dijkstra(self):
        """Ciclo de routing para Dijkstra - placeholder"""
        self.log_message("[ROUTING-DIJKSTRA] Ciclo Dijkstra (no implementado)")
        pass
    
    # =================== PROCESO DE HELLO ===================
    
    def hello_process(self):
        """Proceso de envío de mensajes HELLO"""
        self.log_message("[HELLO] Proceso iniciado")
        seq_counter = 0
        
        while self.running:
            try:
                seq_counter += 1
                
                # Enviar HELLO a cada vecino
                for neighbor_id in self.neighbor_ids:
                    neighbor_addr = self.names.get(neighbor_id)
                    if neighbor_addr:

                        hello_msg = Messages.create_hello_message(
                            from_addr=self.my_address,
                            to_addr=neighbor_addr,
                            hops=4,
                            algorithm=self.current_algorithm
                            
                        )
                        
                        
                        if self.send_to_neighbor(neighbor_id, hello_msg):
                            self.stats["hello_sent"] += 1
                
                time.sleep(5.0)  # HELLO cada 5 segundos
                
            except Exception as e:
                self.log_message(f"[HELLO] ERROR: {e}")
                time.sleep(2.0)
    
    # =================== MÉTODOS PÚBLICOS ===================
    
    def start(self):
        """Iniciar el nodo"""
        if not self.setup_redis():
            self.log_message("[ERROR] No se pudo configurar Redis")
            return False
        
        # Inicializar algoritmo de flooding
        try:
            
            self.algorithms["flooding"] = Flooding()
        except ImportError:
            self.log_message("[WARNING] No se pudo importar clase Flooding")
            # Crear una implementación básica temporal
            class BasicFlooding:
                def process_message(self, node, message):
                    node.log_message("[FLOODING] Procesando mensaje (implementación básica)")
            self.algorithms["flooding"] = BasicFlooding()
        try:
            self.algorithms["lsr"] = LSR(self.node_id, self.topology)
            self.log_message("[INIT] LSR inicializado")
        except ImportError:
            self.log_message("[WARNING] No se pudo importar clase LSR")
        except Exception as e:
            self.log_message(f"[WARNING] Error inicializando LSR: {e}")
        

        
        self.running = True
        
        # Iniciar procesos
        self.routing_thread = threading.Thread(target=self.routing_process, daemon=True)
        self.forwarding_thread = threading.Thread(target=self.forwarding_process, daemon=True)
        self.hello_thread = threading.Thread(target=self.hello_process, daemon=True)
        
        self.routing_thread.start()
        self.forwarding_thread.start()
        self.hello_thread.start()
        
        self.log_message(f"[INIT] Nodo iniciado con algoritmo {self.current_algorithm}")
        return True
    
    def stop(self):
        """Detener el nodo"""
        self.running = False
        
        # Detener Redis Manager
        if self.redis_manager:
            self.redis_manager.stop()
        
        self.log_message("[STOP] Nodo detenido")
    
    def send_data_message(self, destination, payload):
        """Enviar mensaje de datos"""
        try:
            # Determinar dirección de destino
            dest_addr = None
            if destination in self.names:
                dest_addr = self.names[destination]
            else:
                dest_addr = destination
            
            # Crear mensaje

            message = Messages.create_data_message(
                from_addr=self.my_address,
                to_addr=dest_addr,
                hops=10,
                algorithm=self.current_algorithm,
                payload=payload
            )


            self.log_message(f"[Mensaje envado] {message}")
            
            
            
            # Procesar con algoritmo actual
            current_alg = self.algorithms.get(self.current_algorithm)
            if current_alg and hasattr(current_alg, 'process_message'):
                current_alg.process_message(self, message)
                self.log_message(f"[SEND] Mensaje enviado a {destination}: '{payload}'")
            else:
                # Envío directo como fallback
                if destination in self.neighbor_ids:
                    self.send_to_neighbor(destination, message)
                else:
                    self.log_message(f"[ERROR] No se puede enviar a {destination} - no es vecino directo")
                
        except Exception as e:
            self.log_message(f"[ERROR] Error enviando mensaje: {e}")
    
    def switch_algorithm(self, algorithm):
        """Cambiar algoritmo de ruteo"""
        if algorithm not in self.algorithms:
            self.log_message(f"[ERROR] Algoritmo {algorithm} no soportado")
            return False
        
        old_alg = self.current_algorithm
        self.current_algorithm = algorithm
        
        with self.routing_lock:
            self.routing_table.clear()
        
        self.log_message(f"[SWITCH] Algoritmo cambiado: {old_alg} → {algorithm}")
        return True
    
    def get_stats(self):
        current_time = time.time()
        active_neighbors = sum(1 for nid in self.neighbor_ids 
                            if self.is_neighbor_active(nid, current_time))
        
        stats = dict(self.stats)
        stats.update({
            "algorithm": self.current_algorithm,
            "active_neighbors": active_neighbors,
            "total_neighbors": len(self.neighbor_ids),
            "routing_table_size": len(self.routing_table),
            "redis_connected": self.redis_manager.is_connected() if self.redis_manager else False
        })
        
        # Agregar stats del algoritmo actual
        current_alg = self.algorithms.get(self.current_algorithm)
        if current_alg and hasattr(current_alg, 'get_stats'):
            alg_stats = current_alg.get_stats()
            # Prefijo para evitar conflictos de nombres
            for key, value in alg_stats.items():
                stats[f"{self.current_algorithm}_{key}"] = value
        
        return stats


    def interactive_mode(self):
        """Modo interactivo para testing"""
        print(f"\n=== NODO {self.node_id} - {self.current_algorithm.upper()} ===")
        print("Comandos disponibles:")
        print("  send <destino> <mensaje>  - Enviar mensaje")
        print("  stats                     - Ver estadísticas")
        print("  neighbors                 - Ver estado de vecinos")
        print("  algorithm <alg>           - Cambiar algoritmo")
        print("  config                    - Ver configuración")
        print("  lsr_info                  - Ver información LSR (solo si LSR activo)")
        print("  lsr_topology              - Ver topología conocida por LSR")
        print("  lsr_routes                - Ver tabla de ruteo LSR") 
        print("  force_lsp                 - Forzar envío de LSP (solo LSR)")
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
                
                elif cmd[0] == "stats":
                    stats = self.get_stats()
                    print("Estadísticas:")
                    for key, value in stats.items():
                        print(f"  {key}: {value}")
                
                elif cmd[0] == "neighbors":
                    current_time = time.time()
                    print("Estado de vecinos:")
                    for nid in self.neighbor_ids:
                        active = self.is_neighbor_active(nid, current_time)
                        metrics = self.neighbor_metrics[nid]
                        last_seen = metrics.last_seen
                        status = "ACTIVO" if active else "INACTIVO"
                        addr = self.names.get(nid, "N/A")
                        print(f"  {nid} ({addr}): {status} (last_seen: {last_seen})")
                
                elif cmd[0] == "config":
                    print("Configuración actual:")
                    print(f"  Node ID: {self.node_id}")
                    print(f"  Address: {self.my_address}")
                    print(f"  Neighbors: {self.neighbor_ids}")
                    print(f"  Names: {self.names}")
                    print(f"  Topology: {self.topology}")
                
                elif cmd[0] == "algorithm" and len(cmd) >= 2:
                    new_alg = cmd[1]
                    if self.switch_algorithm(new_alg):
                        print(f"Algoritmo cambiado a: {new_alg}")
                    else:
                        print(f"Error cambiando a algoritmo: {new_alg}")
                

                elif cmd[0] == "lsr_info":
                    if self.current_algorithm == "lsr":
                        lsr_stats = self.get_lsr_stats()
                        print("Información LSR:")
                        for key, value in lsr_stats.items():
                            if isinstance(value, dict):
                                print(f"  {key}:")
                                for sub_key, sub_value in value.items():
                                    print(f"    {sub_key}: {sub_value}")
                            else:
                                print(f"  {key}: {value}")
                    else:
                        print("LSR no está activo")
                
                elif cmd[0] == "lsr_topology":
                    lsr_alg = self.algorithms.get("lsr")
                    if lsr_alg:
                        topology_info = lsr_alg.get_topology_info()
                        print("Topología conocida por LSR:")
                        for node, data in topology_info.get("link_state_db", {}).items():
                            print(f"  {node}: {data}")
                    else:
                        print("LSR no disponible")
                
                elif cmd[0] == "lsr_routes":
                    lsr_alg = self.algorithms.get("lsr")
                    if lsr_alg:
                        routes = lsr_alg.get_routing_table()
                        print("Tabla de ruteo LSR:")
                        for dest, route_info in routes.items():
                            print(f"  {dest} -> next_hop: {route_info['next_hop']}, cost: {route_info['cost']}")
                        if not routes:
                            print("  (No hay rutas calculadas)")
                    else:
                        print("LSR no disponible")
                
                elif cmd[0] == "force_lsp":
                    if self.current_algorithm == "lsr":
                        lsr_alg = self.algorithms.get("lsr")
                        if lsr_alg:
                            lsr_alg.last_lsp_time = 0  # Forzar envío
                            print("LSP forzado en próximo ciclo de routing")
                        else:
                            print("LSR no disponible")
                    else:
                        print("Comando solo disponible en modo LSR")
                
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
        """Ejecutar el nodo en modo interactivo"""
        try:
            if not self.start():
                print(f"Error iniciando nodo {self.node_id}")
                return
            
            print(f"Nodo {self.node_id} iniciado correctamente")
            self.interactive_mode()
            
        except KeyboardInterrupt:
            print(f"\nDeteniendo nodo {self.node_id}...")
            self.stop()
        except Exception as e:
            print(f"Error en nodo {self.node_id}: {e}")
            self.stop()


