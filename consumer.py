import os
import json
from kafka import KafkaConsumer
from kafka.errors import KafkaError
from kafka_utils import KAFKA_SERVERS, TOPIC_NAME, wait_for_kafka, setup_logger
from decoder_encoder import decode  # Importar función de decodificación

logger = setup_logger("consumer")

DATA_FILE = "./logs/data/telemetria.jsonl"


def ensure_data_dir():
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)


def save_payload(payload):
    with open(DATA_FILE, "a") as f:
        f.write(json.dumps(payload) + "\n")


def create_consumer():
    try:
        consumer = KafkaConsumer(
            TOPIC_NAME,
            bootstrap_servers=KAFKA_SERVERS,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            group_id="telemetria-group",
            value_deserializer=lambda x: json.loads(x.decode("utf-8"))
        )
        logger.info("✓ Consumer creado")
        return consumer
    except Exception as e:
        logger.error(f"✗ Error creando consumer: {e}")
        raise


def consume_messages():
    consumer = create_consumer()
    ensure_data_dir()

    logger.info(f"Esperando mensajes en {TOPIC_NAME}...")

    try:
        for msg in consumer:
            payload = msg.value
            
            # El payload viene como: {"data": "3_bytes_codificados", "timestamp": 123456}
            try:
                # Extraer los datos codificados
                datos_codificados = payload.get("data")
                timestamp = payload.get("timestamp")
                
                if not datos_codificados:
                    logger.warning("Mensaje sin campo 'data', ignorando...")
                    continue
                
                logger.info(f"Datos codificados recibidos: {repr(datos_codificados)} ({len(datos_codificados)} bytes)")
                logger.info(f"Hex: {datos_codificados.encode('latin-1').hex()}")
                
                # DECODIFICAR los 3 bytes
                datos_decodificados = decode(datos_codificados)
                
                # Agregar el timestamp al mensaje decodificado
                datos_decodificados["timestamp"] = timestamp
                
                logger.info(f"✓ Datos decodificados: {datos_decodificados}")
                
                # Guardar el mensaje decodificado
                save_payload(datos_decodificados)
                
            except Exception as e:
                logger.error(f"✗ Error decodificando mensaje: {e}")
                logger.error(f"Payload original: {payload}")
                continue

    except KeyboardInterrupt:
        logger.info("Consumidor detenido.")
    finally:
        consumer.close()


def main():
    logger.info("=" * 60)
    logger.info("[CONSUMER] Iniciando: MODO DECODIFICACIÓN")
    logger.info("=" * 60)
    
    if not wait_for_kafka():
        logger.error("Error conectando a Kafka.")
        return
    consume_messages()


if __name__ == "__main__":
    main()