import json
import struct

# Mapeo de direcciones de viento
DIRECCIONES = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]

def encode(data):
    temperatura = data["temperatura"]
    humedad = data["humedad"]
    direccion = data["direccion_viento"]
    
    # Validaciones
    if not (0 <= humedad <= 100):
        raise ValueError("Humedad debe estar entre 0 y 100")
    if not (0 <= temperatura <= 110):
        raise ValueError("Temperatura debe estar entre 0 y 110")
    if direccion not in DIRECCIONES:
        raise ValueError(f"Dirección debe ser una de: {DIRECCIONES}")
    
    # Convertir temperatura a entero (multiplicar por 100 para mantener 2 decimales)
    temp_int = int(round(temperatura * 100))
    
    # Obtener índice de dirección (0-7)
    dir_int = DIRECCIONES.index(direccion)
    
    
    valor_24bits = (humedad & 0x7F) | ((dir_int & 0x07) << 7) | ((temp_int & 0x3FFF) << 10)
    
    # Convertir a 3 bytes
    byte1 = (valor_24bits >> 16) & 0xFF
    byte2 = (valor_24bits >> 8) & 0xFF
    byte3 = valor_24bits & 0xFF
    
    # Convertir bytes a caracteres ASCII
    resultado = chr(byte1) + chr(byte2) + chr(byte3)
    
    return resultado


def decode(encoded_str):
    if len(encoded_str) != 3:
        raise ValueError("El string debe tener exactamente 3 caracteres")
    
    # Convertir caracteres a bytes
    byte1 = ord(encoded_str[0])
    byte2 = ord(encoded_str[1])
    byte3 = ord(encoded_str[2])
    
    # Reconstruir el valor de 24 bits
    valor_24bits = (byte1 << 16) | (byte2 << 8) | byte3
    
    # Extraer cada campo
    humedad = valor_24bits & 0x7F  # Bits 0-6
    dir_int = (valor_24bits >> 7) & 0x07  # Bits 7-9
    temp_int = (valor_24bits >> 10) & 0x3FFF  # Bits 10-23
    
    # Convertir temperatura de vuelta a flotante
    temperatura = temp_int / 100.0
    
    # Obtener dirección del viento
    direccion = DIRECCIONES[dir_int]
    
    return {
        "temperatura": temperatura,
        "humedad": humedad,
        "direccion_viento": direccion
    }

