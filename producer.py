import os
import time
from kafka import KafkaProducer
from kafka.errors import KafkaError, NoBrokersAvailable
import json
from kafka_utils import KAFKA_SERVERS, TOPIC_NAME, wait_for_kafka, setup_logger

# Configurar logger
logger = setup_logger('producer')


def create_producer():
    """Crear un productor de Kafka con reintentos"""
    max_retries = 5
    for attempt in range(max_retries):
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
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
    """Enviar mensajes a Kafka"""
    producer = create_producer()
    
    logger.info('Iniciando envío de mensajes...')
    for i in range(10):
        message = {'number': i, 'message': f'Hola desde Python {i}'}
        logger.info(f'Enviando: {message}')
        
        try:
            future = producer.send(TOPIC_NAME, value=message)
            record_metadata = future.get(timeout=10)
            logger.info(f'✓ Mensaje enviado a {record_metadata.topic} partition {record_metadata.partition}')
        except KafkaError as e:
            logger.error(f'✗ Error enviando mensaje: {e}')
        
        time.sleep(1)
    
    producer.close()
    logger.info('Productor cerrado. Todos los mensajes enviados.')

    
def main():
    logger.info('=' * 60)
    logger.info('[PRODUCER] Iniciando producer')
    logger.info('=' * 60)
    
    # Esperar a que Kafka esté disponible
    if not wait_for_kafka():
        logger.error('Error: No se pudo conectar a Kafka. Saliendo...')
        return
    
    logger.info('¡Kafka está listo! Iniciando envío de mensajes...')
    produce_messages()
    logger.info('Producer finalizado')


if __name__ == '__main__':
    main()