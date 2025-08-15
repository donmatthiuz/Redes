import socket
import threading
import json

class SocketManager:
    def __init__(self, host="127.0.0.1", port=5000):
        self.host = host
        self.port = port
        self.running = False

    def start_server(self):
        """Inicia el servidor para escuchar mensajes"""
        self.running = True
        server_thread = threading.Thread(target=self._listen)
        server_thread.daemon = True
        server_thread.start()
        print(f"Servidor escuchando en {self.host}:{self.port}")

    def _listen(self):
        """Hilo de escucha que recibe mensajes entrantes"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind((self.host, self.port))
            server_socket.listen()

            while self.running:
                conn, addr = server_socket.accept()
                client_thread = threading.Thread(target=self._handle_client, args=(conn, addr))
                client_thread.daemon = True
                client_thread.start()

    def _handle_client(self, conn, addr):
        """Maneja un cliente que se ha conectado"""
        with conn:
            try:
                data = conn.recv(4096).decode()
                if data:
                    message = json.loads(data)
                    self.on_message(message, addr)
            except Exception as e:
                print(f"Error recibiendo mensaje: {e}")

    def send_message(self, host, port, message):
        """Envía un mensaje JSON a otro nodo"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((host, port))
                s.sendall(json.dumps(message).encode())
        except Exception as e:
            print(f"Error enviando mensaje a {host}:{port} → {e}")

    def on_message(self, message, addr):
        """
        Método para manejar mensajes recibidos.
        """
        print(f"Mensaje recibido de {addr}: {message}")

    def stop(self):
        """Detiene el servidor"""
        self.running = False
