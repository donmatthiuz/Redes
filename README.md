# Laboratorio 8


## 🚀 Levantar servicios

```bash
# Levantar todos los servicios en background
docker-compose up -d

# Levantar y ver logs en tiempo real
docker-compose up

# Levantar solo servicios específicos
docker-compose up -d kafka zookeeper
docker-compose up -d producer
docker-compose up -d consumer

# Reconstruir imágenes y levantar
docker-compose up -d --build

# Forzar recreación de contenedores
docker-compose up -d --force-recreate
```

## 📋 Ver logs

```bash
# Ver logs de todos los servicios
docker-compose logs

# Ver logs en tiempo real (follow)
docker-compose logs -f

# Ver logs de servicios específicos
docker-compose logs producer
docker-compose logs consumer
docker-compose logs kafka

# Ver logs en tiempo real de servicios específicos
docker-compose logs -f producer consumer

# Ver últimas 100 líneas de logs
docker-compose logs --tail=100 producer

# Ver logs con timestamps
docker-compose logs -f -t producer
```

## 🔍 Entrar a los contenedores

```bash
# Entrar al contenedor del producer
docker-compose exec producer bash

# Entrar al contenedor del consumer
docker-compose exec consumer bash

# Entrar al contenedor de Kafka
docker-compose exec kafka bash

# Entrar al contenedor de Zookeeper
docker-compose exec zookeeper bash

# Si bash no funciona, intenta con sh
docker-compose exec producer sh
```

## 📊 Ver estado de servicios

```bash
# Ver estado de todos los contenedores
docker-compose ps

# Ver procesos corriendo en un contenedor
docker-compose top producer

# Ver uso de recursos
docker stats
```

## 🔄 Reiniciar servicios

```bash
# Reiniciar todos los servicios
docker-compose restart

# Reiniciar servicios específicos
docker-compose restart producer
docker-compose restart consumer
docker-compose restart kafka

# Detener servicios
docker-compose stop

# Detener servicios específicos
docker-compose stop producer consumer

# Iniciar servicios detenidos
docker-compose start
```

## 🗑️ Limpiar y detener

```bash
# Detener y eliminar contenedores
docker-compose down

# Detener, eliminar contenedores y volúmenes
docker-compose down -v

# Detener, eliminar contenedores, volúmenes e imágenes
docker-compose down -v --rmi all

# Eliminar volúmenes huérfanos
docker volume prune
```

