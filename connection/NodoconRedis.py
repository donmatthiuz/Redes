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

class NodoRedis:
    def __init__(self, node_id, algorithm="flooding",
                 topology_file="data/topo.txt", names_file="data/id_nodos.txt"):
        
        self.node_id = node_id
        self.algorithm = algorithm.lower()

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
        self.my_address = self.names.get(node_id, f"{node_id}")
        
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

    def ruteo(self):     
        self.log.write(f"[Nodo {self.node_id}] [RUTEO-{self.algorithm.upper()}] Proceso iniciado")
        if self.algorithm == "flooding":
            pass
        elif self.algorithm == "lsr":
            pass
        elif self.algorithm == "dijkstra":  # AGREGAR esta línea
            pass

    def forwarding(self):
        self.log.write(f"[Nodo {self.node_id}] [FORWARDING-{self.algorithm.upper()}] Proceso iniciado")
        if self.algorithm == "flooding":
            pass
        elif self.algorithm == "lsr":
            pass
        
        elif self.algorithm == "dijkstra":
            pass

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
                    print("Mensaje")
                    
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
        procesos = [p1, p2]
        
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

