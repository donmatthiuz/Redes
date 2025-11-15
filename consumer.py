import os
import json
from kafka import KafkaConsumer
from kafka.errors import KafkaError
from kafka_utils import KAFKA_SERVERS, TOPIC_NAME, wait_for_kafka, setup_logger

logger = setup_logger("consumer")

DATA_FILE = "./logs/data/telemetria.jsonl"


def ensure_data_dir():
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)


def save_payload(payload):
    """Guardar cada mensaje como una línea JSON"""
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
            logger.info(f"Datos recibidos: {payload}")

            save_payload(payload)

    except KeyboardInterrupt:
        logger.info("Consumidor detenido.")
    finally:
        consumer.close()


def main():
    logger.info("Iniciando consumer...")
    if not wait_for_kafka():
        logger.error("Error conectando a Kafka.")
        return
    consume_messages()


if __name__ == "__main__":
    main()
