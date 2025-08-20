from multiprocessing import Process, Manager, Lock
import time
from connection.TablaRuteo import TablaRuteo

class Nodo:
    def __init__(self, id, tabla=None, lock=None):
        self.id = id
        # Si no se pasa una tabla, se crea una propia
        self.tabla = tabla or TablaRuteo(Manager())
        self.lock = lock or Lock()

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


