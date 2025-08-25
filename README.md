# Laboratorio 3 Parte 1

[Repositorio](https://github.com/donmatthiuz/Redes/tree/lab3)


## Ejecución del Script `main.py`

### Requisitos

- Python 3.8+ instalado.
- Dependencias del proyecto instaladas (si aplica).
- Archivos de configuración:
  - `data/topo.txt` (topología de la red)
  - `data/id_nodos.txt` (direcciones de los nodos)  
  > Si no existen, se crean automáticamente al ejecutar el script.

---

### Sintaxis

```bash
python main.py <node_id> <algoritmo>
````

* `<node_id>`: Identificador del nodo (por ejemplo: `A`, `B`, `C`).
* `<algoritmo>`: Algoritmo de enrutamiento a usar. Opciones:

  * `flooding` (por defecto)
  * `lsr`
  * `dijkstra`

---

## Ejemplos

```bash
# Iniciar nodo A con Flooding (por defecto)
python main.py A flooding

# Iniciar nodo B con LSR
python main.py B lsr

# Iniciar nodo C con Dijkstra
python main.py C dijkstra
```

---

## Notas

1. El puerto del nodo se calcula automáticamente como:

   ```
   puerto = 5000 + (ord(node_id) - ord('A'))
   ```

   Ejemplo: Nodo A → 5000, Nodo B → 5001, Nodo C → 5002.

2. Los logs de cada nodo se guardan en la carpeta `./logs/` con el nombre `<node_id>.txt`.

3. Para ejecutar múltiples nodos, abrir varias terminales y ejecutar `main.py` con diferentes `<node_id>` y algoritmos.

