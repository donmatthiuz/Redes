import os
import time
import logging
from kafka.admin import KafkaAdminClient

# Configuración
KAFKA_SERVERS = 'iot.redesuvg.cloud:9092'
TOPIC_NAME = '22982'

# Configuración de logging
LOG_FILE = os.getenv('LOG_FILE', '/app/logs/app.log')
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

def setup_logger(name):
    """Configurar logger para cada módulo"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Evitar duplicar handlers si ya existen
    if not logger.handlers:
        # Handler para archivo
        file_handler = logging.FileHandler(LOG_FILE)
        file_handler.setLevel(logging.INFO)
        
        # Handler para consola
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formato
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger

def wait_for_kafka(max_retries=30, retry_interval=2):
    """Esperar a que Kafka esté disponible"""
    logger = setup_logger('kafka_utils')
    logger.info(f'Esperando a que Kafka esté listo en {KAFKA_SERVERS}...')
    
    for attempt in range(max_retries):
        try:
            admin_client = KafkaAdminClient(
                bootstrap_servers=KAFKA_SERVERS,
                request_timeout_ms=5000
            )
            # Intentar listar topics para verificar conexión
            admin_client.list_topics()
            admin_client.close()
            logger.info(f'✓ Kafka está listo después de {attempt + 1} intentos')
            return True
        except Exception as e:
            logger.warning(f'Intento {attempt + 1}/{max_retries}: Kafka no está listo aún... ({type(e).__name__})')
            time.sleep(retry_interval)
    
    logger.error('✗ No se pudo conectar a Kafka después de todos los intentos')
    return False