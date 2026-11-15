import ast
import json
from pathlib import Path
import runpy
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]

class ConfigurationTests(unittest.TestCase):
    def options(self):
        result = {'trocknungsbeginn_entitaet': 'input_datetime.kwh_reset'}
        for i in range(1, 9):
            result[f'th{i}_a_feuchte'] = f'sensor.th{i}_humidity'
            result[f'th{i}_a_temperatur'] = f'sensor.th{i}_air_temperature'
        for i in range(1, 4):
            result[f'kanal{i}_schalter'] = f'switch.kanal{i}'
        return result

    def load(self, options):
        with patch.object(Path, 'read_text', return_value=json.dumps(options)):
            return runpy.run_path(str(ROOT / 'trocknungsbericht/zuordnung.py'))

    def test_mapping_and_start_date(self):
        options = self.options()
        options['th1_a_feuchte'] = 'sensor.real_humidity'
        options['trocknungsbeginn_entitaet'] = 'input_datetime.trocknungsbeginn'
        module = self.load(options)
        self.assertEqual(module['HUMIDITY'][0], 'sensor.real_humidity')
        self.assertEqual(module['START_ENTITY'], 'input_datetime.trocknungsbeginn')
        self.assertEqual(len(module['TEMPERATURE']), 8)
        self.assertEqual(len(module['SWITCHES']), 3)

    def test_invalid_and_duplicate_entities(self):
        for key, value in [('th1_a_feuchte', 'wrong'),
                           ('th1_a_feuchte', 'sensor.th2_humidity'),
                           ('trocknungsbeginn_entitaet', 'sensor.date')]:
            with self.subTest(key=key, value=value):
                options = self.options()
                options[key] = value
                with self.assertRaises(ValueError):
                    self.load(options)

    def test_missing_optional_helper_only(self):
        source = (ROOT / 'trocknungsbericht/report.py').read_text()
        fn = next(n for n in ast.parse(source).body
                  if isinstance(n, ast.FunctionDef) and n.name == 'get_state')
        class Response:
            status_code = 404
            def raise_for_status(self):
                raise RuntimeError('HTTP error')
        class Requests:
            @staticmethod
            def get(*args, **kwargs):
                return Response()
        namespace = {'requests': Requests, 'HA_URL': 'http://test', 'HEADERS': {}}
        exec(compile(ast.Module(body=[fn], type_ignores=[]), 'get_state', 'exec'), namespace)
        get_state = namespace['get_state']
        self.assertEqual(get_state('input_text.th1', optional=True), 'nicht aktiv')
        with self.assertRaises(RuntimeError):
            get_state('input_datetime.kwh_reset')
        Response.status_code = 401
        with self.assertRaises(RuntimeError):
            get_state('input_text.th1', optional=True)

if __name__ == '__main__':
    unittest.main()
