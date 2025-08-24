from multiprocessing import Process, Manager, Lock
import time
import json
from connection.TablaRuteo import TablaRuteo
from connection.socket_manager import SocketManager
from connection.Mensajes import Mensajes_Protocolo
from connection.Red import RedConfig
from algoritmos.Flodding import Flooding
import threading

class Nodo:
    def __init__(self, node_id, host="127.0.0.1", port=5000, topology_file="data/topo.txt", names_file="data/id_nodos.txt"):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.running = False
        
        # Cargar configuración
        self.topology = RedConfig.load_topology(topology_file)
        self.names = RedConfig.load_names(names_file)
        
        # Obtener mis vecinos y dirección
        self.neighbors = self.topology.get(node_id, [])
        self.my_address = self.names.get(node_id, f"{node_id}@localhost")
        
        # Inicializar algoritmo de flooding
        neighbor_addresses = [self.names.get(n, f"{n}@localhost") for n in self.neighbors]
        self.flooding = Flooding(self.my_address, neighbor_addresses)
        
        # Socket manager
        self.socket = SocketManager(host=host, port=port)
        self.socket.on_message = self._on_message
        
        # Tabla de ruteo y discovered nodes
        self.routing_table = {}
        self.discovered_nodes = set()
        self.neighbor_ports = {}  # Mapeo de vecinos a puertos
        
        print(f"[Nodo {self.node_id}] Inicializado en {host}:{port}")
        print(f"[Nodo {self.node_id}] Dirección: {self.my_address}")
        print(f"[Nodo {self.node_id}] Vecinos: {self.neighbors}")

    def _on_message(self, raw_message, addr):
        try:
            if isinstance(raw_message, str):
                message = json.loads(raw_message)
            else:
                message = raw_message
            
            msg_type = message.get("type")
            proto = message.get("proto")
            from_addr = message.get("from")
            to_addr = message.get("to")
            
            print(f"[Nodo {self.node_id}] Recibido {msg_type} de {from_addr} hacia {to_addr}")
            
            if msg_type == "hello":
                self._handle_hello(message, addr)
            elif msg_type == "message" and proto == "flooding":
                self._handle_flooding_message(message)
            else:
                print(f"[Nodo {self.node_id}] Tipo de mensaje no reconocido: {msg_type}")
                
        except json.JSONDecodeError as e:
            print(f"[Nodo {self.node_id}] Error parseando mensaje: {e}")
        except Exception as e:
            print(f"[Nodo {self.node_id}] Error procesando mensaje: {e}")

    def _handle_hello(self, message, addr):
        from_addr = message.get("from")
        
        # Extraer información del nodo
        if from_addr and from_addr != self.my_address:
            self.discovered_nodes.add(from_addr)
            self.neighbor_ports[from_addr] = addr[1]  # Guardar puerto del vecino
            print(f"[Nodo {self.node_id}] Vecino descubierto: {from_addr} en {addr}")

    def _handle_flooding_message(self, message):
        # Usar el algoritmo de flooding para procesar el mensaje
        forwards = self.flooding.receive_message(message)
        
        # Si el mensaje es para nosotros, no hay forwards
        if message.get("to") == self.my_address:
            payload = message.get("payload", {})
            data = payload.get("data", "")
            print(f"[Nodo {self.node_id}] 📩 MENSAJE RECIBIDO: {data}")
            return
        
        # Reenviar el mensaje según flooding
        for neighbor_addr, new_msg in forwards:
            self._forward_message(neighbor_addr, new_msg)

    def _forward_message(self, neighbor_addr, message):
        # Buscar el puerto del vecino
        neighbor_port = None
        
        # Primero buscar en neighbor_ports descubiertos
        if neighbor_addr in self.neighbor_ports:
            neighbor_port = self.neighbor_ports[neighbor_addr]
        else:
            # Mapeo por defecto basado en node_id
            for node_id, addr in self.names.items():
                if addr == neighbor_addr:
                    # Asumimos puertos consecutivos: A=5000, B=5001, etc.
                    neighbor_port = 5000 + ord(node_id) - ord('A')
                    break
        
        if neighbor_port:
            print(f"[Nodo {self.node_id}] 🔄 Reenviando a {neighbor_addr} ({neighbor_port})")
            self.socket.send_message("127.0.0.1", neighbor_port, message)
        else:
            print(f"[Nodo {self.node_id}] ❌ No se pudo determinar puerto para {neighbor_addr}")

    def start_server(self):
        """Inicia el servidor para escuchar mensajes"""
        self.socket.start_server()
        self.running = True

    def send_hello_messages(self):
        hello_msg = Mensajes_Protocolo.create_hello_message(self.my_address, "flooding")
        
        for neighbor_id in self.neighbors:
            neighbor_port = 5000 + ord(neighbor_id) - ord('A')
            print(f"[Nodo {self.node_id}] Enviando HELLO a {neighbor_id} (puerto {neighbor_port})")
            self.socket.send_message("127.0.0.1", neighbor_port, hello_msg)

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
        
        # Procesar con flooding (esto genera los forwards)
        forwards = self.flooding.receive_message(message)
        
        # Enviar a todos los vecinos según flooding
        for neighbor_addr, new_msg in forwards:
            self._forward_message(neighbor_addr, new_msg)

    def discovery_process(self):
        """Proceso de descubrimiento de vecinos"""
        while self.running:
            self.send_hello_messages()
            time.sleep(5)  # Enviar HELLO cada 5 segundos

    def interactive_mode(self):
        print(f"\n=== NODO {self.node_id} - MODO INTERACTIVO ===")
        print("Comandos disponibles:")
        print("  send <destino> <mensaje>  - Enviar mensaje")
        print("  neighbors                 - Ver vecinos descubiertos")
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
                    
                elif cmd[0] == "neighbors":
                    print(f"Vecinos descubiertos: {list(self.discovered_nodes)}")
                    
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

    def start_all_processes(self):
        # Iniciar servidor
        self.start_server()
        
        # Esperar un poco para que el servidor se inicie
        time.sleep(1)
        
        # Iniciar proceso de descubrimiento en hilo separado
        discovery_thread = threading.Thread(target=self.discovery_process)
        discovery_thread.daemon = True
        discovery_thread.start()
        
        # Esperar un poco más para descubrir vecinos
        time.sleep(2)
        
        # Modo interactivo
        self.interactive_mode()

    def stop(self):
        """Detiene el nodo"""
        self.running = False
        self.socket.stop()
        print(f"[Nodo {self.node_id}] Detenido")
