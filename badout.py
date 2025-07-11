

import sys, math, wave, struct

# ─── PARÁMETROS AJUSTABLES ───────────────────────────────────────────────────
FREQ_0   = 440      # Hz (bit 0)
FREQ_1   = 660      # Hz (bit 1)
BIT_MS   = 200      # duración de un bit
LETTER_PAUSE = 1  # s entre letras
WORD_PAUSE   = 1.7  # s entre palabras
SAMPLE_HZ = 44100
AMP       = int(32767 * 0.6)

# ─── TABLA BAUDOT (LSB primero) ──────────────────────────────────────────────
BAUDOT = {
    ' ': '00100', 'A': '00011', 'B': '11001', 'C': '01110', 'D': '01001',
    'E': '00010', 'F': '01101', 'G': '11010', 'H': '10100', 'I': '00110',
    'J': '01011', 'K': '01111', 'L': '10010', 'M': '11100', 'N': '01100',
    'O': '11000', 'P': '10110', 'Q': '10111', 'R': '01010', 'S': '00101',
    'T': '10000', 'U': '00111', 'V': '11110', 'W': '10011', 'X': '11101',
    'Y': '10101', 'Z': '10001'
}

# ─── GENERADORES DE AUDIO ────────────────────────────────────────────────────
def sine(freq, ms):
    n = int(SAMPLE_HZ * ms / 1000)
    buf = (AMP * math.sin(2 * math.pi * freq * t / SAMPLE_HZ)
           for t in range(n))
    return struct.pack('<' + 'h'*n, *map(int, buf))

def silence(ms):
    return b'\0' * int(SAMPLE_HZ * ms / 1000 * 2)

def beep_bit(bit):
    return sine(FREQ_0 if bit == '0' else FREQ_1, BIT_MS)

# ─── CONVERSIÓN TEXTO → BYTES DE AUDIO ───────────────────────────────────────
def text_to_audio(text):
    audio = bytearray()
    words = text.upper().strip().split(' ')
    for wi, word in enumerate(words):
        for ci, ch in enumerate(word):
            bits5 = BAUDOT.get(ch)
            if not bits5:
                continue
            seq = '0' + bits5 + '1'           # start + 5 + stop
            for b in seq:
                audio += beep_bit(b)
            audio += silence(LETTER_PAUSE * 1000)
        if wi < len(words) - 1:
            audio += silence(WORD_PAUSE * 1000)
    return audio

# ─── ENTRADA / SALIDA ─────────────────────────────────────────────────────────
def main():
    text  = sys.argv[1] if len(sys.argv) > 1 else input("Texto: ")
    fname = sys.argv[2] if len(sys.argv) > 2 else "baudot.wav"

    audio = text_to_audio(text)

    with wave.open(fname, 'w') as w:
        w.setparams((1, 2, SAMPLE_HZ, 0, 'NONE', 'not compressed'))
        w.writeframes(audio)

    dur = len(audio) / 2 / SAMPLE_HZ
    print(f"✔ '{fname}' generado ({dur:.1f} s, {len(audio)//2:,} muestras)")

if __name__ == '__main__':
    main()
