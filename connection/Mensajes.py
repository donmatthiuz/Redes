import time

class Messages:
    def __init__(self):
        pass
    
    @staticmethod
    def create_message(msg_type, from_addr, to_addr, payload, hops=10, headers=None):
        """Crear mensaje con el nuevo formato de protocolo"""
        if headers is None:
            headers = []
        
        return {
            "type": msg_type,
            "from": from_addr,
            "to": to_addr,
            "hops": hops,
            "headers": headers,
            "payload": payload
        }
    
    @staticmethod
    def create_hello_message(from_addr, to_addr, algorithm="flooding", seq=None):
        """Crear mensaje HELLO"""
        if seq is None:
            seq = int(time.time() * 1_000_000)
            
        return Messages.create_message(
            msg_type="hello",
            from_addr=from_addr,
            to_addr=to_addr,  # Dirección específica del vecino
            payload={
                "seq": seq,
                "ts": time.time()
            },
            hops=4,
            headers=[{"alg": algorithm}]
        )
    
    @staticmethod
    def create_echo_message(from_addr, to_addr, seq, original_ts, algorithm="flooding"):
        """Crear mensaje ECHO"""
        return Messages.create_message(
            msg_type="echo",
            from_addr=from_addr,
            to_addr=to_addr,
            payload={
                "seq": seq,
                "ts": original_ts
            },
            hops=4,
            headers=[{"alg": algorithm}]
        )
    
    @staticmethod
    def create_data_message(from_addr, to_addr, data, algorithm="flooding", hops=10):
        """Crear mensaje de datos"""
        return Messages.create_message(
            msg_type="data",
            from_addr=from_addr,
            to_addr=to_addr,
            payload=data,
            hops=hops,
            headers=[{"alg": algorithm}]
        )
    
    @staticmethod
    def create_info_message(from_addr, to_addr, info_data, algorithm="flooding", hops=10):
        """Crear mensaje de información"""
        return Messages.create_message(
            msg_type="info",
            from_addr=from_addr,
            to_addr=to_addr,
            payload=info_data,
            hops=hops,
            headers=[{"alg": algorithm}]
        )
    
    @staticmethod
    def create_lsp_message(from_addr, to_addr, neighbors_data, sequence, algorithm="lsr", hops=10):
        """Crear mensaje LSP para LSR"""
        return Messages.create_message(
            msg_type="info",  # LSP usa tipo "info"
            from_addr=from_addr,
            to_addr=to_addr,  # Dirección específica del vecino
            payload={
                "type": "lsp",
                "neighbors": neighbors_data,
                "sequence": sequence
            },
            hops=hops,
            headers=[{"alg": algorithm}, {"lsp": True}]
        )