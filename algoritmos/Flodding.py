import time

class Flooding:
    def __init__(self, node_id, neighbors):
        """
        node_id: ID único del nodo (ejemplo: "A")
        neighbors: lista de IDs de nodos vecinos
        """
        self.node_id = node_id
        self.neighbors = neighbors
        self.seen_messages = set()

    def create_message(self, destination, payload, ttl=5):
        """Crea un mensaje inicial con identificador único."""
        return {
            "msg_id": f"{self.node_id}-{time.time()}",
            "from_node": self.node_id,
            "to": destination,
            "ttl": ttl,
            "payload": payload
        }

    def receive_message(self, message):
        """
        Procesa un mensaje recibido y devuelve una lista de reenvíos.
        Cada reenvío es una tupla (vecino, mensaje).
        """
        msg_id = message["msg_id"]

        # Si ya procesamos este mensaje, ignoramos
        if msg_id in self.seen_messages:
            return []
        self.seen_messages.add(msg_id)

        # Si somos el destino, procesar y no reenviar
        if message["to"] == self.node_id:
            print(f"[{self.node_id}] 📩 Recibido: {message['payload']}")
            return []

        # Reducir TTL y verificar
        message["ttl"] -= 1
        if message["ttl"] <= 0:
            print(f"[{self.node_id}] ⚠ TTL expirado para {msg_id}")
            return []

        # Reenviar a todos los vecinos excepto de donde vino
        forward_list = []
        for neighbor in self.neighbors:
            if neighbor != message["from_node"]:
                new_msg = message.copy()
                new_msg["from_node"] = self.node_id
                forward_list.append((neighbor, new_msg))

        return forward_list
