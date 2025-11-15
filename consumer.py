import os
import time
from kafka import KafkaConsumer
from kafka.errors import KafkaError
import json
from kafka_utils import KAFKA_SERVERS, TOPIC_NAME, wait_for_kafka, setup_logger

# Configurar logger
logger = setup_logger('consumer')


def create_consumer():
    """Crear un consumidor de Kafka"""
    try:
        consumer = KafkaConsumer(
            TOPIC_NAME,
            bootstrap_servers=KAFKA_SERVERS,
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            group_id='my-group',
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        logger.info('✓ Consumidor creado exitosamente')
        return consumer
    except Exception as e:
        logger.error(f'✗ Error creando consumidor: {e}')
        raise

    
def consume_messages():
    """Consumir mensajes de Kafka"""
    consumer = create_consumer()
    
    logger.info(f'Esperando mensajes en el topic {TOPIC_NAME}...')
    logger.info('Presiona Ctrl+C para detener')
    
    try:
        message_count = 0
        for message in consumer:
            message_count += 1
            logger.info('=' * 50)
            logger.info(f'Mensaje #{message_count} recibido')
            logger.info(f'  Contenido: {message.value}')
            logger.info(f'  Topic: {message.topic}')
            logger.info(f'  Partition: {message.partition}')
            logger.info(f'  Offset: {message.offset}')
            logger.info('=' * 50)
    except KeyboardInterrupt:
        logger.info('Señal de interrupción recibida. Deteniendo consumidor...')
    except Exception as e:
        logger.error(f'Error consumiendo mensajes: {e}')
    finally:
        consumer.close()
        logger.info(f'Consumidor cerrado. Total de mensajes procesados: {message_count}')


def main():
    logger.info('=' * 60)
    logger.info('[CONSUMER] Iniciando consumer')
    logger.info('=' * 60)
    
    # Esperar a que Kafka esté disponible
    if not wait_for_kafka():
        logger.error('Error: No se pudo conectar a Kafka. Saliendo...')
        return
    
    logger.info('¡Kafka está listo! Iniciando consumidor...')
    consume_messages()
    logger.info('Consumer finalizado')


if __name__ == '__main__':
    main()