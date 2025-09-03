# Laboratorio 3
---

[Repositorio](https://github.com/donmatthiuz/Redes/tree/lab3)

## 🔧 Preparación del entorno

1. **Clonar el repositorio**

   ```bash
   git clone https://github.com/donmatthiuz/Redes.git
   cd Redes
   git checkout lab3
   ```

2. **Crear un entorno virtual (recomendado)**

   ```bash
   python3 -m venv venv
   source venv/bin/activate   # En Linux/Mac
   venv\Scripts\activate      # En Windows
   ```

3. **Instalar dependencias**

   ```bash
   pip install -r requirements.txt
   ```

---

## ▶️ Ejecución de los scripts

### Parte 1 (`main.py`)

```bash
python3 main.py <node_id> <algoritmo>
```

* `<node_id>`: Identificador del nodo (ej: `A`, `B`, `C`, …).
* `<algoritmo>`:

  * `flooding` (por defecto)
  * `lsr`
  * `dijkstra`

📌 Ejemplos:

```bash
python3 main.py A flooding
python3 main.py B lsr
python3 main.py C dijkstra
```

---

### Parte 2 (`parte2.py`)

Funciona igual que `main.py`, solo que usas:

```bash
python3 parte2.py <node_id> <algoritmo>
```

Ejemplo:

```bash
python3 parte2.py G dijkstra
```

---

## 📂 Archivos importantes

* **`data/topo.txt`** → describe la topología de la red.
* **`data/id_nodos.txt`** → contiene direcciones de los nodos.

  > Si no existen, se generan automáticamente al ejecutar.

---

## 📑 Logs

Cada nodo escribe su log en:

```
./logs/<node_id>.txt
```

---

## 🔄 Múltiples nodos

Para levantar varios nodos:

* Abres varias terminales.
* Ejecutas el mismo script (`main.py` o `parte2.py`) con distintos `<node_id>` y algoritmos.

Ejemplo:

```bash
# Terminal 1
python3 main.py A flooding

# Terminal 2
python3 main.py B lsr

# Terminal 3
python3 parte2.py G dijkstra
```

