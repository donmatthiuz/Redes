import os
from dotenv import load_dotenv
from cliente.LLM import LLMClient

# Cargar variables de entorno desde .env
load_dotenv()

if __name__ == "__main__":
    # Tomar la API Key desde la variable de entorno
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("No se encontró la API Key en las variables de entorno.")

    cliente = LLMClient(api_key=api_key)

    print(cliente.preguntar("¿Quién fue Alan Turing?"))
    print(cliente.preguntar("¿En qué fecha nació?"))
    print(cliente.preguntar("¿Cuál fue su contribución a la informática?"))

    cliente.mostrar_log()
