import json
import subprocess
import unittest
from unittest.mock import patch
from pathlib import Path
from types import SimpleNamespace

import ejecutor_docker
import prototipo
import checker_contenedor


def resultado_simulado(programa, entrada, limite, cobertura=False, imagen=None):
    valor = int(entrada)
    salida = abs(valor) if Path(programa).name == 'original.py' else valor
    return {'estado': 'ok', 'codigo_salida': 0, 'stdout_hex': f'{salida}\n'.encode().hex(),
            'stderr_hex': '', 'lineas': ([1, 2, 3] if valor < 0 else [1, 2, 5]) if cobertura else [],
            'lineas_ejecutables': [1, 2, 3, 5], 'python_contenedor': 'prueba', 'segundos': 0.0}


class PruebasPrototipo(unittest.TestCase):
    def test_estado_checker_distingue_rechazo_y_fallo(self):
        self.assertEqual(checker_contenedor.interpretar({'estado': 'terminado', 'codigo': 0}), 'aceptada')
        self.assertEqual(checker_contenedor.interpretar({'estado': 'terminado', 'codigo': 1}), 'rechazada')
        self.assertEqual(checker_contenedor.interpretar({'estado': 'terminado', 'codigo': 2}), 'rechazada')
        self.assertEqual(checker_contenedor.interpretar({'estado': 'terminado', 'codigo': 3}), 'inconcluso')
        self.assertEqual(checker_contenedor.interpretar({'estado': 'tiempo_agotado', 'codigo': None}), 'inconcluso')

    @patch.object(prototipo, 'ejecutar', side_effect=resultado_simulado)
    def test_checker_registra_validez_separada_de_diferencia(self, _ejecucion):
        caso = Path(__file__).parent / 'ejemplos/valor_absoluto/caso.json'
        resultado_checker = {'estado': 'completado', 'original': {'interpretacion': 'aceptada'},
                             'propuesta': {'interpretacion': 'aceptada'}}
        with patch.object(prototipo.checker_testlib, 'verificar', return_value=resultado_checker):
            resultado = prototipo.evaluar(caso, 'cambios', checker_path='checker.cpp', testlib_path='testlib.h')
        self.assertEqual(resultado['estado'], 'diferencia_reproducida')
        self.assertFalse(resultado['comparaciones'][0]['stdout_identica'])
        self.assertEqual(resultado['comparaciones'][0]['checker']['propuesta']['interpretacion'], 'aceptada')

    def test_checker_requiere_ambos_archivos(self):
        caso = Path(__file__).parent / 'ejemplos/valor_absoluto/caso.json'
        with self.assertRaises(ValueError):
            prototipo.evaluar(caso, 'cambios', checker_path='checker.cpp')

    def test_comparacion_decimal_con_tolerancia(self):
        c = {'tipo': 'decimal_tolerancia_absoluta', 'tolerancia': 0.0010000001}
        hx = lambda s: s.encode().hex()
        self.assertTrue(prototipo.comparar_salidas(hx('2.0\n'), hx('2.0009\n'), c))
        self.assertFalse(prototipo.comparar_salidas(hx('2.0'), hx('2.002'), c))
        self.assertIsNone(prototipo.comparar_salidas(hx('2.0'), hx('nan'), c))
        self.assertIsNone(prototipo.comparar_salidas(hx('2.0'), hx('dos'), c))

    def test_priorizacion_por_cobertura_adicional_y_desempate(self):
        coberturas = {'b': [1, 2], 'a': [1, 2], 'c': [2, 3], 'd': []}
        self.assertEqual(prototipo.ordenar(coberturas, {1, 2, 3}), ['a', 'c', 'b', 'd'])

    def test_cambios_solo_en_original_y_agregados(self):
        original = 'x = 1\nprint(x)\n'
        self.assertEqual(prototipo.cambios_original(original, 'x = 2\nprint(x)\n'), {1})
        self.assertEqual(prototipo.cambios_original(original, original + 'print(2)\n'), set())

    @patch.object(prototipo, 'ejecutar', side_effect=resultado_simulado)
    def test_ejemplo_detecta_diferencia_reproducida(self, _ejecucion):
        caso = Path(__file__).parent / 'ejemplos/valor_absoluto/caso.json'
        resultado = prototipo.evaluar(caso, 'cambios')
        self.assertEqual(resultado['orden_candidato'][0], '02_negativo')
        self.assertEqual(resultado['contraejemplo'], '02_negativo')
        self.assertEqual(resultado['estado'], 'diferencia_reproducida')
        self.assertEqual(len(resultado['ejecuciones']), 6)

    def test_tiempo_agotado_no_es_contraejemplo(self):
        programa = Path(__file__).parent / 'ejemplos/valor_absoluto/original.py'
        respuesta = {'estado': 'tiempo_agotado', 'codigo_salida': None, 'stdout_hex': '',
                     'stderr_hex': '', 'lineas': []}
        proceso = SimpleNamespace(returncode=0, stdout=json.dumps(respuesta).encode(), stderr=b'')
        with patch.object(ejecutor_docker.subprocess, 'run', return_value=proceso) as llamada:
            resultado = prototipo.ejecutar(programa, '', 0.5)
        self.assertEqual(resultado['estado'], 'tiempo_agotado')
        comando = llamada.call_args.args[0]
        self.assertIn('--read-only', comando)
        self.assertEqual(comando[comando.index('--network') + 1], 'none')

    def test_no_hay_ejecucion_local_si_docker_falla(self):
        programa = Path(__file__).parent / 'ejemplos/valor_absoluto/original.py'
        with patch.object(ejecutor_docker.subprocess, 'run', side_effect=FileNotFoundError('docker')) as llamada:
            resultado = prototipo.ejecutar(programa, '1\n', 2)
        self.assertEqual(resultado['estado'], 'error_entorno')
        self.assertEqual(llamada.call_count, 1)

    def test_limpieza_si_el_contenedor_agota_su_limite(self):
        programa = Path(__file__).parent / 'ejemplos/valor_absoluto/original.py'
        fin = SimpleNamespace(returncode=0, stdout='', stderr='')
        with patch.object(ejecutor_docker.subprocess, 'run',
                          side_effect=[subprocess.TimeoutExpired('docker', 1), fin]) as llamada:
            resultado = prototipo.ejecutar(programa, '1\n', 1)
        self.assertEqual(resultado['estado'], 'error_entorno')
        primer_comando = llamada.call_args_list[0].args[0]
        nombre = primer_comando[primer_comando.index('--name') + 1]
        self.assertEqual(llamada.call_args_list[1].args[0], ['docker', 'rm', '--force', nombre])

    @patch.object(prototipo, 'ejecutar', side_effect=resultado_simulado)
    def test_aleatorio_no_prepara_cobertura(self, _ejecucion):
        caso = Path(__file__).parent / 'ejemplos/valor_absoluto/caso.json'
        resultado = prototipo.evaluar(caso, 'aleatoria', limite_entradas=1)
        self.assertTrue(all(r['fase'] != 'cobertura' for r in resultado['ejecuciones']))
        self.assertLessEqual(len(resultado['ejecuciones']), 4)


if __name__ == '__main__':
    unittest.main()
