import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import prototipo
import checker_contenedor


class PruebasPrototipo(unittest.TestCase):
    def test_estado_checker_distingue_rechazo_y_fallo(self):
        self.assertEqual(checker_contenedor.interpretar({'estado': 'terminado', 'codigo': 0}), 'aceptada')
        self.assertEqual(checker_contenedor.interpretar({'estado': 'terminado', 'codigo': 1}), 'rechazada')
        self.assertEqual(checker_contenedor.interpretar({'estado': 'terminado', 'codigo': 2}), 'rechazada')
        self.assertEqual(checker_contenedor.interpretar({'estado': 'terminado', 'codigo': 3}), 'inconcluso')
        self.assertEqual(checker_contenedor.interpretar({'estado': 'tiempo_agotado', 'codigo': None}), 'inconcluso')

    def test_checker_registra_validez_separada_de_diferencia(self):
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

    def test_ejemplo_detecta_diferencia_reproducida(self):
        caso = Path(__file__).parent / 'ejemplos/valor_absoluto/caso.json'
        resultado = prototipo.evaluar(caso, 'cambios')
        self.assertEqual(resultado['orden_candidato'][0], '02_negativo')
        self.assertEqual(resultado['contraejemplo'], '02_negativo')
        self.assertEqual(resultado['estado'], 'diferencia_reproducida')
        self.assertEqual(len(resultado['ejecuciones']), 6)

    def test_tiempo_agotado_no_es_contraejemplo(self):
        prototipo.TEMPORALES.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=prototipo.TEMPORALES) as temp:
            programa = Path(temp) / 'espera.py'
            programa.write_text('while True: pass\n', encoding='utf-8')
            resultado = prototipo.ejecutar(programa, '', 0.5)
        self.assertEqual(resultado['estado'], 'tiempo_agotado')

    def test_aleatorio_no_prepara_cobertura(self):
        caso = Path(__file__).parent / 'ejemplos/valor_absoluto/caso.json'
        resultado = prototipo.evaluar(caso, 'aleatoria', limite_entradas=1)
        self.assertTrue(all(r['fase'] != 'cobertura' for r in resultado['ejecuciones']))
        self.assertLessEqual(len(resultado['ejecuciones']), 4)


if __name__ == '__main__':
    unittest.main()
