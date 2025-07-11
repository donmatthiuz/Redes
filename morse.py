
import sys, math, wave, struct, argparse

FREQ_HZ   = 800          # tono (Hz)
SAMPLE_HZ = 44100        # muestreo
AMP       = int(32767*0.6)

MORSE = {
    'A':'·-','B':'-···','C':'-·-·','D':'-··','E':'·','F':'··-·',
    'G':'--·','H':'····','I':'··','J':'·---','K':'-·-','L':'·-··',
    'M':'--','N':'-·','O':'---','P':'·--·','Q':'--·-','R':'·-·',
    'S':'···','T':'-','U':'··-','V':'···-','W':'·--','X':'-··-',
    'Y':'-·--','Z':'--··',
    '0':'-----','1':'·----','2':'··---','3':'···--','4':'····-',
    '5':'·····','6':'-····','7':'--···','8':'---··','9':'----·',
    '.':'·-·-·-','?':'··--··',',':'--··--','/':'-··-·','@':'·--·-·',
    "'":'·----·','!':'-·-·--','-':'-····-','(':'-·--·',')':'-·--·-'
}

def tone(ms):
    n = int(SAMPLE_HZ*ms/1000)
    buf = (AMP*math.sin(2*math.pi*FREQ_HZ*t/SAMPLE_HZ) for t in range(n))
    return struct.pack('<'+'h'*n,*map(int,buf))

silence = lambda ms: b'\0'*int(SAMPLE_HZ*ms/1000*2)

def events(text, dot, gap):
    dash = dot*3
    gap_sym = dot
    gap_word = gap*2
    ev=[]
    words=text.upper().strip().split()
    for wi,w in enumerate(words):
        for ci,ch in enumerate(w):
            pat=MORSE.get(ch)
            if not pat: continue
            for si,s in enumerate(pat):
                ev.append((True, dot if s=='·' else dash))
                if si<len(pat)-1:        ev.append((False,gap_sym))
            if ci<len(w)-1:              ev.append((False,gap))
        if wi<len(words)-1:              ev.append((False,gap_word))
    return ev

def main():
    pa=argparse.ArgumentParser()
    pa.add_argument("texto",nargs='?',help="Texto a enviar")
    pa.add_argument("wav",nargs='?',help="Archivo WAV")
    pa.add_argument("--dot",type=int,default=150,help="Duración punto ms")
    pa.add_argument("--gap",type=int,default=600,help="Silencio entre letras ms")
    a=pa.parse_args()

    txt=a.texto or input("Texto: ")
    wav=a.wav or "morse.wav"
    dot=max(50,a.dot)
    gap=max(dot,a.gap)

    audio=bytearray()
    for beep,d in events(txt,dot,gap):
        audio+=tone(d) if beep else silence(d)

    with wave.open(wav,'w') as w:
        w.setparams((1,2,SAMPLE_HZ,0,'NONE','not compressed'))
        w.writeframes(audio)

    print(f"✔ Generado '{wav}' | punto={dot} ms | gap_letra={gap} ms")

if __name__=="__main__":
    main()
