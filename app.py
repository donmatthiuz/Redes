import os
import time
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError, NoBrokersAvailable
from kafka.admin import KafkaAdminClient, NewTopic
import json

# Configuración
KAFKA_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
TOPIC_NAME = 'test-topic'

def create_producer():
    """Crear un productor de Kafka"""
    return KafkaProducer(
        bootstrap_servers=KAFKA_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

def create_consumer():
    """Crear un consumidor de Kafka"""
    return KafkaConsumer(
        TOPIC_NAME,
        bootstrap_servers=KAFKA_SERVERS,
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        group_id='my-group',
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )

def produce_messages():
    """Enviar mensajes a Kafka"""
    producer = create_producer()
    
    for i in range(10):
        message = {'number': i, 'message': f'Hola desde Python {i}'}
        print(f'Enviando: {message}')
        
        try:
            future = producer.send(TOPIC_NAME, value=message)
            record_metadata = future.get(timeout=10)
            print(f'Mensaje enviado a {record_metadata.topic} partition {record_metadata.partition}')
        except KafkaError as e:
            print(f'Error enviando mensaje: {e}')
        
        time.sleep(1)
    
    producer.close()

def consume_messages():
    """Consumir mensajes de Kafka"""
    consumer = create_consumer()
    
    print(f'Esperando mensajes en el topic {TOPIC_NAME}...')
    
    try:
        for message in consumer:
            print(f'Recibido: {message.value}')
            print(f'  Topic: {message.topic}')
            print(f'  Partition: {message.partition}')
            print(f'  Offset: {message.offset}')
            print('-' * 50)
    except KeyboardInterrupt:
        print('Deteniendo consumidor...')
    finally:
        consumer.close()

def main():
    print('Esperando a que Kafka esté listo...')
    time.sleep(10)  # Esperar a que Kafka se inicie
    
    print('¡Kafka está listo! Iniciando aplicación...')
    
    # Puedes elegir producir o consumir
    # Descomenta la función que quieras usar
    
    produce_messages()
    # consume_messages()

if __name__ == '__main__':
    main()