import redis

r = redis.Redis(
    host="lab3.redesuvg.cloud",
    port=6379,
    password="UVGRedis2025",
    decode_responses=True
)

# Probar conexión
try:
    pong = r.ping()
    print("Conectado a Redis:", pong)
    
    # Ejemplo guardar y leer
    r.set("prueba", "hola mundo")
    print("Valor:", r.get("prueba"))

except Exception as e:
    print("Error:", e)
