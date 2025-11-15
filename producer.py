import os 
import time 
from kafka import KafkaProducer 
from kafka.errors import KafkaError, NoBrokersAvailable 
import json 
import numpy as np
from kafka_utils import KAFKA_SERVERS, TOPIC_NAME, wait_for_kafka, setup_logger 
 
# Configurar logger 
logger = setup_logger('producer')

# Parámetros
NUM_SENSORES = 5
DIRECCIONES_VIENTO = ['N', 'NO', 'O', 'SO', 'S', 'SE', 'E', 'NE']

TEMP_MEDIA = 25.0
TEMP_STD = 15.0
TEMP_MIN = 0.0
TEMP_MAX = 110.0

HUMEDAD_MEDIA = 60.0
HUMEDAD_STD = 20.0
HUMEDAD_MIN = 0
HUMEDAD_MAX = 100


def generar_temperatura():
    temp = np.random.normal(TEMP_MEDIA, TEMP_STD)
    temp = np.clip(temp, TEMP_MIN, TEMP_MAX)
    return round(temp, 2)


def generar_humedad():
    humedad = np.random.normal(HUMEDAD_MEDIA, HUMEDAD_STD)
    humedad = np.clip(humedad, HUMEDAD_MIN, HUMEDAD_MAX)
    return int(round(humedad))


def generar_direccion_viento():
    return np.random.choice(DIRECCIONES_VIENTO)


def generar_lectura_sensores(sensor_id):
    return {
        "sensor_id": sensor_id,
        "temperatura": generar_temperatura(),
        "humedad": generar_humedad(),
        "direccion_viento": generar_direccion_viento()
    }


def create_producer():
    max_retries = 5
    for attempt in range(max_retries):
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: str(k).encode("utf-8"),
                request_timeout_ms=10000,
                max_block_ms=10000
            )
            logger.info('✓ Productor creado exitosamente')
            return producer
        except NoBrokersAvailable:
            if attempt < max_retries - 1:
                logger.warning(f'Reintentando crear productor ({attempt + 1}/{max_retries})...')
                time.sleep(2)
            else:
                logger.error('No se pudo crear el productor después de todos los intentos')
                raise
    return None


def produce_messages():
    producer = create_producer()

    logger.info(f'Iniciando emisión de datos desde {NUM_SENSORES} sensores...\n')

    sensores = [f"Sensor{i+1}" for i in range(NUM_SENSORES)]
    logger.info(f"Sensores activos: {sensores}")

    contador = 0

    try:
        while True:
            contador += 1

            for sensor in sensores:
                lectura = generar_lectura_sensores(sensor)

                logger.info(f'[#{contador}] Enviando desde {sensor}: {lectura}')

                try:
                    future = producer.send(
                        TOPIC_NAME,
                        key=sensor,
                        value=lectura
                    )
                    record_metadata = future.get(timeout=10)
                    logger.info(f'✓ {sensor} → partición {record_metadata.partition}')
                except KafkaError as e:
                    logger.error(f'✗ Error enviando desde {sensor}: {e}')

            logger.info('Esperando 15 segundos...\n')
            time.sleep(15)

    except KeyboardInterrupt:
        logger.info('⚠ Interrupción detectada. Cerrando productor...')
    finally:
        producer.close()
        logger.info('Productor cerrado. Finalizado.')


def main():
    logger.info('=' * 60)
    logger.info('[PRODUCER] Iniciando simulación de sensores múltiples')
    logger.info('=' * 60)

    if not wait_for_kafka():
        logger.error('Error: No se pudo conectar a Kafka. Abortando...')
        return

    logger.info('Kafka listo. Iniciando simulación...')
    produce_messages()


if __name__ == '__main__':
    main()
