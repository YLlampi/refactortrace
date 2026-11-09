"""Descarga dos archivos públicos de LintEval y verifica su integridad."""
import hashlib
import os
import tempfile
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
ARCHIVOS = [
    ('https://raw.githubusercontent.com/6643789wsx/LintEval/master/lite/linteval_lite.jsonl',
     RAIZ / 'linteval_lite.jsonl', '4d7143ca984022e496b343dbffaa769ac99c35cb32fa45bd9e8c0151a00d7c06'),
    ('https://raw.githubusercontent.com/6643789wsx/LintEval/master/tools/testlib.h',
     RAIZ / 'ejemplos/linteval_p00364/testlib.h', 'bb323e3c89285214966076e0d23d5a295c5f6126da7ff198c1276ddb95ecb1a0'),
]


def descargar(url, destino, esperado):
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        actual = hashlib.sha256(destino.read_bytes()).hexdigest()
        if actual != esperado:
            raise ValueError(f'El archivo existente no coincide con el hash esperado: {destino}')
        print('Ya disponible y verificado:', destino)
        return
    temporal = None
    try:
        with urllib.request.urlopen(url, timeout=60) as respuesta, \
             tempfile.NamedTemporaryFile(dir=destino.parent, prefix='.descarga_', delete=False) as archivo:
            temporal = Path(archivo.name)
            digest = hashlib.sha256()
            while bloque := respuesta.read(1024 * 1024):
                digest.update(bloque)
                archivo.write(bloque)
        if digest.hexdigest() != esperado:
            raise ValueError(f'La descarga cambió; el hash no coincide: {url}')
        os.replace(temporal, destino)
        temporal = None
        print('Descargado y verificado:', destino)
    finally:
        if temporal and temporal.exists():
            temporal.unlink()


if __name__ == '__main__':
    for url, destino, esperado in ARCHIVOS:
        descargar(url, destino, esperado)
