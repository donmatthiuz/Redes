

import time
 
class Mensajes_Protocolo ():
    def __init__(self):
        pass

    def crear_mensaje(proto, msg_type, from_addr, to_addr, payload, ttl=5, headers=None):
        if headers is None:
            headers = []
            
        return {
            "proto": proto,
            "type": msg_type,
            "from": from_addr,
            "to": to_addr,
            "ttl": ttl,
            "headers": headers,
            "payload": payload,
            "timestamp": time.time()
        }
    
    def create_hello_message(from_addr, protocolo):
        return Mensajes_Protocolo.crear_mensaje(
            proto=protocolo,
            msg_type="hello",
            from_addr=from_addr,
            to_addr="broadcast",
            payload={"action": "discover", "node_id": from_addr}
        )
    

    def create_data_message(from_addr,protocolo, to_addr, data, ttl=5):
        return Mensajes_Protocolo.crear_mensaje(
            proto=protocolo,
            msg_type="message",
            from_addr=from_addr,
            to_addr=to_addr,
            payload={"data": data},
            ttl=ttl
        )