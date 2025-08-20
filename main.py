# va a crear 2 nodos  
# el .env de la raiz es el usuario/puerto

from multiprocessing import Process, Manager
import time
from connection.TablaRuteo import TablaRuteo
from connection.Nodo import Nodo

if __name__ == "__main__":
    nodo1 = Nodo(1)
    nodo2 = Nodo(2)

    # Creamos procesos para cada nodo
    p_nodo1 = Process(target=nodo1.main_executor)
    p_nodo2 = Process(target=nodo2.main_executor)

    p_nodo1.start()
    p_nodo2.start()

    p_nodo1.join()
    p_nodo2.join()
