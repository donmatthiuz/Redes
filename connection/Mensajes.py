
import json
import time

class Mensajes_Protocolo ():
  def crear_mensaje(
      proto, msg_type, from_addr, to_addr, payload, ttl=5, headers=None
  ):
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
  def create_hello_message(from_addr, protocol, to_addr="broadcast"):
        return Mensajes_Protocolo.crear_mensaje(
            proto=protocol,
            msg_type="ping",
            from_addr=from_addr,
            to_addr=to_addr,
            payload={"action": "ping", "node_id": from_addr}
        )
  
  def create_data_message(proto, from_addr, to_addr, data, ttl=5):
        return Mensajes_Protocolo.crear_mensaje(
            proto=proto,
            msg_type="message",
            from_addr=from_addr,
            to_addr=to_addr,
            payload={"data": data},
            ttl=ttl
        )
  def create_info_message(proto, from_addr, routing_info):
        return Mensajes_Protocolo.crear_mensaje(
            proto=proto,
            msg_type="info",
            from_addr=from_addr,
            to_addr="broadcast",
            payload={"routing_info": routing_info}
        )
    
  
  def parse_message(json_str): 
      try:
          msg = json.loads(json_str)
          required_fields = ["proto", "type", "from", "to", "ttl", "payload"]
          
          for field in required_fields:
              if field not in msg:
                  raise ValueError(f"Campo requerido '{field}' faltante")
          
          return msg
      except json.JSONDecodeError as e:
          raise ValueError(f"JSON inválido: {e}")
    

  def serialize_message(message):
    return json.dumps(message, indent=2)
    

  def is_for_me(message, my_addr):
      return message.get("to") == my_addr or message.get("to") == "broadcast"
    
  def should_forward(message, my_addr):
      return (message.get("to") != my_addr and 
                message.get("to") != "broadcast" and 
                message.get("ttl", 0) > 0)
  

  
