"""Ejecuta un archivo e informa las líneas observadas, en un proceso separado."""
import json
import runpy
import sys

programa, salida = sys.argv[1:3]
sys.argv = [programa]
lineas = set()

def traza(frame, evento, arg):
    if evento == 'line' and frame.f_code.co_filename == programa:
        lineas.add(frame.f_lineno)
    return traza

try:
    sys.settrace(traza)
    runpy.run_path(programa, run_name='__main__')
finally:
    sys.settrace(None)
    with open(salida, 'w', encoding='utf-8') as archivo:
        json.dump(sorted(lineas), archivo)
