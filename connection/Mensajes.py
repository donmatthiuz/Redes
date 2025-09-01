import time

class Messages:
    def __init__(self):
        pass

    @staticmethod
    def create_message(msg_type, from_addr, to_addr, payload=None, hops=10, headers=None, seq_num=None, neighbors=None):
        """Crear mensaje según el nuevo protocolo"""
        if headers is None:
            headers = {}

        msg = {
            "type": msg_type,
            "from": from_addr,
            "to": to_addr,
            "hops": hops,
            "headers": headers
        }

        if msg_type == "info":
            if seq_num is not None:
                msg["seq_num"] = seq_num
            if neighbors is not None:
                msg["neighbors"] = neighbors
        elif msg_type == "message":
            msg["payload"] = payload

        return msg

    @staticmethod
    def create_hello_message(from_addr, to_addr, algorithm="flooding", hops=4):
        seq = int(time.time() * 1_000_000)
        return Messages.create_message(
            msg_type="hello",
            from_addr=from_addr,
            to_addr=to_addr,
            hops=hops,
            headers={"alg": algorithm}
        )

    @staticmethod
    def create_echo_message(from_addr, to_addr, algorithm="flooding", hops=4):
        return Messages.create_message(
            msg_type="echo",
            from_addr=from_addr,
            to_addr=to_addr,
            hops=hops,
            headers={"alg": algorithm}
        )

    @staticmethod
    def create_data_message(from_addr, to_addr, payload, algorithm="flooding", hops=10):
        return Messages.create_message(
            msg_type="message",
            from_addr=from_addr,
            to_addr=to_addr,
            payload=payload,
            hops=hops,
            headers={"alg": algorithm}
        )

    @staticmethod
    def create_lsp_message(from_addr, to_addr, neighbors=None, seq_num=None, algorithm="lsr", hops=10):
        """Info tipo LSP"""
        return Messages.create_message(
            msg_type="info",
            from_addr=from_addr,
            to_addr=to_addr,
            hops=hops,
            headers={"alg": algorithm},
            seq_num=seq_num,
            neighbors=neighbors
        )
