import whisper

class WhisperTranscriber:
    def __init__(self, model_name="tiny"):
        """
        Inicializa el transcriptor de Whisper.
        :param model_name: Modelo de Whisper a usar ("tiny", "base", "small", "medium", "large")
        """
        print(f"Cargando modelo Whisper '{model_name}'...")
        self.model = whisper.load_model(model_name)
        print("Modelo cargado correctamente.")

    def transcribe(self, audio_path):
        """
        Transcribe un archivo de audio.
        :param audio_path: Ruta del archivo de audio (mp3, wav, mp4, etc.)
        :return: Texto transcrito
        """
        print(f"Transcribiendo audio: {audio_path}")
        result = self.model.transcribe(audio_path)
        return result["text"]
    
# if __name__ == "__main__":
#     transcriber = WhisperTranscriber(model_name="base")
#     texto = transcriber.transcribe("Grabación-_2_.wav")  # Puede ser mp3, wav, mp4
#     print("Texto transcrito:")
#     print(texto)
