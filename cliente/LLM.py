import os
from datetime import datetime
from functions.Logs import Log
from openai import OpenAI

class LLMClient:
    def __init__(self, model="gpt-4", log_file="llm_log.txt", api_key=None):
        """
        Inicializa el cliente LLM.
        :param model: Modelo de OpenAI a usar (por ejemplo "gpt-4")
        :param log_file: Archivo para guardar log de interacción
        :param api_key: API Key de OpenAI (si no se proporciona, usa la variable de entorno)
        """
        self.model = model
        self.conversation = []  # Mantiene el contexto
        self.log = Log(log_file)
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))


        self.system_message = "Eres un asistente útil y educado."
        self.conversation.append({"role": "system", "content": self.system_message})

    def preguntar(self, prompt: str) -> str:

        self.conversation.append({"role": "user", "content": prompt})
        self.log.write(f"USER: {prompt}")

        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.conversation,
            temperature=0.7,
            max_tokens=100
        )

        # Obtener texto de la respuesta
        respuesta_texto = response.choices[0].message.content

        # Guardar respuesta en la conversación y log
        self.conversation.append({"role": "assistant", "content": respuesta_texto})
        self.log.write(f"ASSISTANT: {respuesta_texto}")

        return respuesta_texto

    def mostrar_log(self):
        """
        Muestra todo el log almacenado en el archivo.
        """
        with open(self.log.file_path, "r", encoding="utf-8") as f:
            print(f.read())

