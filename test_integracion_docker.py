"""Pruebas reales optativas: REFACTORTRACE_TEST_DOCKER=1 y Docker operativo."""
import os
import tempfile
import unittest
from pathlib import Path

import ejecutor_docker
import prototipo


@unittest.skipUnless(os.environ.get('REFACTORTRACE_TEST_DOCKER') == '1', 'Docker no solicitado')
class IntegracionDocker(unittest.TestCase):
    def test_comparacion_y_cobertura_reales(self):
        caso = Path(__file__).parent / 'ejemplos/valor_absoluto/caso.json'
        resultado = prototipo.evaluar(caso, 'cambios')
        self.assertEqual(resultado['estado'], 'diferencia_reproducida')
        self.assertEqual(resultado['contraejemplo'], '02_negativo')
        self.assertEqual(resultado['orden_candidato'][0], '02_negativo')
        self.assertEqual(len(resultado['ejecuciones']), 6)

    def test_restricciones_y_limite_de_tiempo(self):
        ejecutor_docker.TEMPORALES.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ejecutor_docker.TEMPORALES) as carpeta:
            archivo = Path(carpeta) / 'prueba.py'
            codigo = ('import os\n'
                      "print(','.join(sorted(os.listdir('/sys/class/net'))))\n"
                      'try:\n'
                      "    open('/programa/programa.py', 'w').write('modificado')\n"
                      "    print('escritura_permitida')\n"
                      'except OSError:\n'
                      "    print('solo_lectura')\n")
            archivo.write_text(codigo, encoding='utf-8')
            resultado = ejecutor_docker.ejecutar(archivo, '', 3)
            self.assertEqual(resultado['estado'], 'ok')
            self.assertEqual(bytes.fromhex(resultado['stdout_hex']).decode(), 'lo\nsolo_lectura\n')
            self.assertEqual(archivo.read_text(encoding='utf-8'), codigo)
            archivo.write_text('while True: pass\n', encoding='utf-8')
            resultado = ejecutor_docker.ejecutar(archivo, '', 0.5)
            self.assertEqual(resultado['estado'], 'tiempo_agotado')
            archivo.write_text("print('x' * 1000001)\n", encoding='utf-8')
            resultado = ejecutor_docker.ejecutar(archivo, '', 3)
            self.assertEqual(resultado['estado'], 'salida_excesiva')


if __name__ == '__main__':
    unittest.main()
