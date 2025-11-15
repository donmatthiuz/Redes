import os
import time
import json
import random
import threading
import numpy as np
from kafka import KafkaProducer
from kafka.errors import KafkaError, NoBrokersAvailable

from kafka_utils import KAFKA_SERVERS, TOPIC_NAME, wait_for_kafka, setup_logger

# Configurar logger
logger = setup_logger('producer')

# Parámetros
DIRECCIONES_VIENTO = ['N', 'NO', 'O', 'SO', 'S', 'SE', 'E', 'NE']

TEMP_MEDIA = 25.0
TEMP_STD = 15.0
TEMP_MIN = 0.0
TEMP_MAX = 110.0

HUMEDAD_MEDIA = 60.0
HUMEDAD_STD = 20.0
HUMEDAD_MIN = 0
HUMEDAD_MAX = 100

# Estado compartido donde cada sensor escribe su última lectura
shared_state = {
    "temperatura": None,
    "humedad": None,
    "direccion_viento": None
}
state_lock = threading.Lock()


# ------------------ GENERADORES (cada sensor solo su medida) ------------------

def generar_temperatura():
    # Distribución normal centrada en TEMP_MEDIA, recortada al rango
    t = np.random.normal(TEMP_MEDIA, TEMP_STD)
    t = np.clip(t, TEMP_MIN, TEMP_MAX)
    # convertir a float nativo con 2 decimales
    return float(round(float(t), 2))


def generar_humedad():
    h = np.random.normal(HUMEDAD_MEDIA, HUMEDAD_STD)
    h = np.clip(h, HUMEDAD_MIN, HUMEDAD_MAX)
    return int(round(float(h)))  # entero nativo


def generar_direccion_viento():
    return str(np.random.choice(DIRECCIONES_VIENTO))


# ------------------ WORKERS DE SENSORES ------------------

def sensor_temperatura_worker():
    while True:
        t = generar_temperatura()
        with state_lock:
            shared_state['temperatura'] = t
        logger.debug(f"[SENSOR-Temp] actualizado: {t}")
        time.sleep(5)  # frecuencia interna de muestreo (ajustable)


def sensor_humedad_worker():
    
    while True:
        h = generar_humedad()
        with state_lock:
            shared_state['humedad'] = h
        logger.debug(f"[SENSOR-Hum] actualizado: {h}")
        time.sleep(5)


def sensor_viento_worker():
   
    while True:
        d = generar_direccion_viento()
        with state_lock:
            shared_state['direccion_viento'] = d
        logger.debug(f"[SENSOR-Viento] actualizado: {d}")
        time.sleep(5)


# ------------------ PRODUCER ------------------

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


def producer_loop(producer, node_key="Nodo1"):
    """
    Cada intervalo (aleatorio entre 15 y 30s) toma las lecturas más recientes
    y envía un único mensaje JSON combinado.
    """
    contador = 0
    while True:
        # esperar intervalo entre 15 y 30 segundos
        intervalo = random.uniform(15, 30)
        time.sleep(intervalo)

        # construir mensaje con snapshot de estado
        with state_lock:
            temp = shared_state['temperatura']
            hum = shared_state['humedad']
            dir_v = shared_state['direccion_viento']

        # Si alguna lectura aún no se ha generado (p. ej. al inicio), la rellenamos o la omitimos
        if temp is None:
            temp = generar_temperatura()
        if hum is None:
            hum = generar_humedad()
        if dir_v is None:
            dir_v = generar_direccion_viento()

        mensaje = {
            "temperatura": float(round(float(temp), 2)),  # float nativo, 2 decimales
            "humedad": int(hum),                           # entero nativo
            "direccion_viento": str(dir_v),                # string nativo
            "timestamp": int(time.time())
        }

        contador += 1
        logger.info(f"[#{contador}] Enviando mensaje combinado: {mensaje}")

        try:
            future = producer.send(
                TOPIC_NAME,
                key=node_key,   # key del nodo/dispositivo
                value=mensaje
            )
            metadata = future.get(timeout=10)
            logger.info(f"✓ Mensaje enviado a {metadata.topic} partition {metadata.partition}")
        except KafkaError as e:
            logger.error(f"✗ Error enviando mensaje combinado: {e}")


# ------------------ INICIALIZACIÓN Y MAIN ------------------

def start_sensor_threads():
    t_temp = threading.Thread(target=sensor_temperatura_worker, daemon=True)
    t_hum = threading.Thread(target=sensor_humedad_worker, daemon=True)
    t_viento = threading.Thread(target=sensor_viento_worker, daemon=True)

    t_temp.start()
    t_hum.start()
    t_viento.start()
    logger.info("Hilos de sensores iniciados (temperatura, humedad, viento).")


def produce_messages():
    producer = create_producer()
    start_sensor_threads()

    # Ejecutar el loop del producer en el hilo principal (o en otro hilo si prefieres)
    try:
        producer_loop(producer, node_key="Nodo1")
    except KeyboardInterrupt:
        logger.info('⚠ Interrupción detectada. Cerrando productor...')
    finally:
        producer.close()
        logger.info('Productor cerrado. Finalizado.')


def main():
    logger.info('=' * 60)
    logger.info('[PRODUCER] Iniciando simulación: sensores separados + envío combinado')
    logger.info('=' * 60)

    if not wait_for_kafka():
        logger.error('Error: No se pudo conectar a Kafka. Abortando...')
        return

    produce_messages()


if __name__ == '__main__':
    main()
