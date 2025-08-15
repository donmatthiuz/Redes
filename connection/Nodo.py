from multiprocessing import Process, Manager
import time
from connection.TablaRuteo import TablaRuteo

class Nodo:
    def __init__(self, id, tabla):
        self.id = id
        self.tabla = tabla

    def ruteo(self):
        while True:
            self.tabla.actualizar("192.168.0.1", "Interfaz 1")
            print(f"[Nodo {self.id}] Actualizando ruteo")
            time.sleep(1)

    def forwarding(self):
        while True:
            print(f"[Nodo {self.id}] Leyendo tabla: {self.tabla.mostrar()}")
            time.sleep(1)

if __name__ == "__main__":
  manager = Manager()
  tabla_compartida = TablaRuteo(manager)

  nodo = Nodo(1, tabla_compartida)

  p1 = Process(target=nodo.ruteo)
  p2 = Process(target=nodo.forwarding)

  p1.start()
  p2.start()

  p1.join()
  p2.join()