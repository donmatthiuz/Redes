from multiprocessing import Process, Manager
import time

class TablaRuteo:
    def __init__(self, manager):
        self.tabla = manager.dict()  # Diccionario compartido

    def actualizar(self, destino, ruta):
        self.tabla[destino] = ruta

    def mostrar(self):
        return dict(self.tabla)