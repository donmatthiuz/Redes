# Iniciar todo
docker-compose up -d

# Ver logs en tiempo real
docker-compose logs -f python-app

# Ver logs de Kafka
docker-compose logs -f kafka

# Reiniciar solo la app de Python (útil si cambias requirements.txt)
docker-compose restart python-app

# Detener todo
docker-compose down

# Detener y eliminar volúmenes (limpieza completa)
docker-compose down -v