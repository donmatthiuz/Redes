from multiprocessing import Process, Manager, Lock
import time
from connection.TablaRuteo import TablaRuteo
from connection.socket_manager import SocketManager

class Nodo:
    def __init__(self, id, host="127.0.0.1", port=5000, tabla=None, lock=None):
        self.id = id
        self.tabla = tabla or TablaRuteo(Manager())
        self.lock = lock or Lock()

        # Crear socket para comunicación
        self.socket = SocketManager(host=host, port=port)

        # Reemplazar el on_message para que actualice la tabla
        self.socket.on_message = self._on_message

    def _on_message(self, message, addr):
        """
        Maneja mensajes recibidos y actualiza la tabla de ruteo si es necesario.
        """
        tipo = message.get("type")
        if tipo == "hello":
            vecino = message.get("from")
            with self.lock:
                self.tabla.actualizar(vecino, f"interfaz-{addr}")
            print(f"[Nodo {self.id}] Recibido HELLO de {vecino}, actualizado en tabla.")
        elif tipo == "message":
            destino = message.get("to")
            if destino == self.id:
                print(f"[Nodo {self.id}]  Mensaje entregado: {message['payload']}")
            else:
                print(f"[Nodo {self.id}] Forwarding mensaje hacia {destino}...")
        else:
            print(f"[Nodo {self.id}] Mensaje recibido: {message}")

    def ruteo(self):
        while True:
            with self.lock: 
                self.tabla.actualizar("192.168.0.1", "Interfaz 1")
            print(f"[Nodo {self.id}] Actualizando ruteo")
            time.sleep(1)

    def forwarding(self):
        while True:
            with self.lock:
                tabla_actual = self.tabla.mostrar()
            print(f"[Nodo {self.id}] Leyendo tabla: {tabla_actual}")
            time.sleep(1)

    def main_executor(self):
        # Creamos procesos para ruteo y forwarding
        p1 = Process(target=self.ruteo)
        p2 = Process(target=self.forwarding)

        p1.start()
        p2.start()

        # Esperamos a que terminen (en este caso nunca)
        p1.join()
        p2.join()