import socket
import threading
import json

class SocketManager:
    def __init__(self, host="127.0.0.1", port=5000):
        self.host = host
        self.port = port
        self.running = False
        self.server_socket = None

    def start_server(self):
        self.running = True
        server_thread = threading.Thread(target=self._listen)
        server_thread.daemon = True
        server_thread.start()
        print(f"🌐 Servidor escuchando en {self.host}:{self.port}")

    def _listen(self):
        
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.server_socket.settimeout(1.0)  # Timeout para poder verificar self.running

            while self.running:
                try:
                    conn, addr = self.server_socket.accept()
                    client_thread = threading.Thread(target=self._handle_client, args=(conn, addr))
                    client_thread.daemon = True
                    client_thread.start()
                except socket.timeout:
                    continue  # Verificar si self.running sigue siendo True
                except Exception as e:
                    if self.running:  # Solo mostrar error si no es por shutdown
                        print(f"Error en servidor: {e}")
                    break
        except Exception as e:
            print(f"Error iniciando servidor: {e}")
        finally:
            if self.server_socket:
                self.server_socket.close()

    def _handle_client(self, conn, addr):
     
        try:
            with conn:
                data = conn.recv(4096).decode('utf-8')
                if data:
                    try:
                        message = json.loads(data)
                        self.on_message(message, addr)
                    except json.JSONDecodeError as e:
                        print(f"Error decodificando JSON de {addr}: {e}")
                        print(f"Datos recibidos: {data}")
        except Exception as e:
            print(f"Error manejando cliente {addr}: {e}")

    def send_message(self, host, port, message):
       
        max_retries = 3
        retry_delay = 0.5
        
        for attempt in range(max_retries):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(5.0)  # Timeout de 5 segundos
                    s.connect((host, port))
                    
                    # Convertir mensaje a JSON si es necesario
                    if isinstance(message, dict):
                        json_data = json.dumps(message)
                    else:
                        json_data = str(message)
                    
                    s.sendall(json_data.encode('utf-8'))
                    return True  # Éxito
                    
            except ConnectionRefusedError:
                if attempt < max_retries - 1:
                    print(f"⚠️ Conexión rechazada a {host}:{port}, reintentando en {retry_delay}s...")
                    import time
                    time.sleep(retry_delay)
                else:
                    print(f"❌ No se pudo conectar a {host}:{port} después de {max_retries} intentos")
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"⚠️ Error enviando mensaje a {host}:{port} → {e}, reintentando...")
                    import time
                    time.sleep(retry_delay)
                else:
                    print(f"❌ Error final enviando mensaje a {host}:{port} → {e}")
        
        return False 

    def on_message(self, message, addr):
      
        print(f"📨 Mensaje recibido de {addr}: {message}")

    def stop(self):
       
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        print(f"🛑 Servidor {self.host}:{self.port} detenido")