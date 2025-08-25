import os
from datetime import datetime

class Log:
    def __init__(self, file_path: str):
        self.file_path = file_path
        if not os.path.exists(file_path):
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("=== LOG INICIADO ===\n")

    def write(self, message: str, with_time: bool = True):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if with_time else ""
        log_message = f"{timestamp} - {message}\n" if with_time else f"{message}\n"

        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(log_message)