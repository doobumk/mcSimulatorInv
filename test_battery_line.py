import unittest
import csv
from pathlib import Path
from tempfile import TemporaryDirectory

from battery_line import BatteryLine
from line_datasheet import BatteryFrame, LineUnit, COLUMNS, DEFAULT_DATASHEET
from machine import frame, unit, machine


class BatteryLineTests(unittest.TestCase):
    def test_csv_controls_belts_products_and_input(self):
        with DEFAULT_DATASHEET.open(encoding='utf-8-sig', newline='') as source:
            rows = list(csv.DictReader(source))
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'configured.csv'
            for count in (1, 3):
                for row in rows:
                    if row['type'] == 'conveyor':
                        row.update(cvBeltLength='9000', cvBeltWidth='40', cvBeltHeight='20', cvbeltAmt=str(count))
                    elif row['type'] == 'product':
                        row.update(length='210', width='400', height='25')
                    elif row['type'] == 'product_input':
                        row.update(x='-4000', y='75', z='1500', cycle='2', amount='3')
                with path.open('w', encoding='utf-8-sig', newline='') as output:
                    writer = csv.DictWriter(output, fieldnames=COLUMNS)
                    writer.writeheader()
                    writer.writerows(reversed(rows))  # product references can precede definitions
                line = BatteryLine(path)
                self.assertIs(type(line.conveyor), unit)
                self.assertEqual(line.conveyor.cvBelt, (9000, 40, 20))
                self.assertEqual(len(line.conveyor.belt_centers_y), count)
                self.assertEqual(line.conveyor.belt_centers_y, [0] if count == 1 else [-145, 0, 145])
                self.assertEqual((line.LINE_START, line.LINE_END, line.BELT_TOP), (-4500, 4500, 1282))
                self.assertEqual(line.minimum_pitch, 210)
                line.start_input()
                line.step(2)
                self.assertEqual(len(line.products), 3)
                self.assertEqual(line.products[-1].size, (210, 400, 25))
                self.assertEqual((line.products[-1].x, line.products[-1].y, line.products[-1].z), (-4000, 75, 1500))

    def test_invalid_belt_and_product_configuration(self):
        with DEFAULT_DATASHEET.open(encoding='utf-8-sig', newline='') as source:
            original = list(csv.DictReader(source))
        cases = [('conveyor', 'cvbeltAmt', '0'), ('conveyor', 'cvbeltAmt', '1.5'),
                 ('conveyor', 'cvBeltWidth', '200'), ('conveyor', 'cvBeltHeight', 'nan'),
                 ('product', 'length', '-1'), ('product_input', 'product', 'missing'),
                 ('product_input', 'z', 'inf'), ('product_input', 'cycle', '0')]
        with TemporaryDirectory() as directory:
            for kind, key, value in cases:
                with self.subTest(kind=kind, key=key, value=value):
                    rows = [dict(row) for row in original]
                    next(row for row in rows if row['type'] == kind)[key] = value
                    path = Path(directory) / 'invalid.csv'
                    with path.open('w', encoding='utf-8', newline='') as output:
                        writer = csv.DictWriter(output, fieldnames=COLUMNS)
                        writer.writeheader()
                        writer.writerows(rows)
                    with self.assertRaisesRegex(ValueError, r'invalid.csv:\d+:'):
                        BatteryLine(path)

    def test_default_datasheet_preserves_original_layout(self):
        line = BatteryLine()
        self.assertIsInstance(line, machine)
        self.assertTrue(all(isinstance(f, BatteryFrame) and isinstance(f, frame) for f in line.frames))
        self.assertIs(type(line.conveyor), unit)
        self.assertNotIsInstance(line.conveyor, machine)
        self.assertIn(line.conveyor, line.units)
        self.assertEqual([(f.length, f.width) for f in line.frames[:3]], [(4970, 1860), (3445, 1860), (3415, 2210)])
        self.assertEqual((line.LINE_START, line.LINE_END, line.BELT_TOP), (-5875, 5875, 1280))
        self.assertEqual(line.frames[0].x_end, line.frames[1].x_start)
        self.assertEqual(line.frames[1].x_end, line.frames[2].x_start)

    def make_datasheet(self, directory, rows):
        path = Path(directory) / "custom.csv"
        expanded = []
        for row in rows:
            columns = row.split(',')
            if len(columns) == 8:
                columns += ([columns[5], '30', columns[7], '2', '', '', '']
                            if columns[0] == 'conveyor' else [''] * 7)
            expanded.append(','.join(columns))
        expanded += ['product,Cell Template,0,0,0,123,600,17.8,,,,,Cell,,',
                     'product_input,Input,40,100,1358.9,,,,,,,,Cell Template,5,7']
        path.write_text(','.join(COLUMNS) + '\n' + '\n'.join(expanded), encoding='utf-8-sig')
        return path

    def test_custom_frames_and_units_control_transport(self):
        with TemporaryDirectory() as directory:
            path = self.make_datasheet(directory, [
                "frame,Custom,2000,100,50,4000,1600,950",
                "conveyor,Transport,2000,100,1342,3920,330,16",
                "process,Inspection,3200,500,1400,300,400,200",
            ])
            line = BatteryLine(path)
        self.assertEqual(len(line.frames), 1)
        self.assertEqual(len(line.units), 2)
        self.assertEqual(line.frames[0].coordinate.z, 50)
        self.assertEqual(line.units[1].name, 'Inspection')
        self.assertEqual((line.LINE_START, line.LINE_END, line.BELT_TOP), (40, 3960, 1350))
        line.inject_batch()
        self.assertEqual(line.cells[-1].x, 40)
        line.step(20)
        self.assertEqual(line.cells, [])

    def test_invalid_datasheets_report_error(self):
        valid_frame = "frame,F1,0,0,0,4000,1800,930"
        valid_unit = "conveyor,Belt,0,0,1272,3920,330,16"
        cases = [
            ([valid_frame], 'exactly one'),
            ([valid_unit], 'at least one'),
            ([valid_frame, valid_unit, valid_unit], 'unique'),
            ([valid_frame, valid_unit.replace('Belt', 'Belt2'), valid_unit], 'exactly one'),
            ([valid_frame.replace('4000', 'nan'), valid_unit], 'finite'),
            ([valid_frame.replace('4000', '-1'), valid_unit], 'positive'),
            ([valid_frame, valid_unit.replace('conveyor', 'unknown')], 'unknown type'),
            ([valid_frame, valid_unit + ',extra'], 'columns'),
        ]
        with TemporaryDirectory() as directory:
            for rows, message in cases:
                with self.subTest(message=message):
                    path = self.make_datasheet(directory, rows)
                    with self.assertRaisesRegex(ValueError, message):
                        BatteryLine(path)

    def test_batch_pause_resume_and_spacing(self):
        line = BatteryLine()
        line.inject_batch()
        self.assertEqual(len(line.cells), 7)
        start = line.cells[0].x
        line.step(2)
        self.assertEqual(line.cells[0].x, start + 600)
        line.pause()
        line.step(2)
        self.assertEqual(line.cells[0].x, start + 600)
        line.inject_batch()
        self.assertEqual(len(line.cells), 14)
        self.assertEqual(line.cells[-1].x, line.inputs[0].input_pos.x)

    def test_continuous_transport_and_exit(self):
        line = BatteryLine()
        line.inject_batch()
        line.step(20)
        self.assertEqual(len(line.cells), 7)
        self.assertGreater(line.cells[-1].x, -945)
        line.step(100)
        self.assertEqual(line.cells, [])

    def test_validation_is_atomic(self):
        line = BatteryLine()
        for speed, pitch in [(float('nan'), 180), (300, 50), (3001, 180)]:
            with self.assertRaises(ValueError):
                line.configure(speed=speed, pitch=pitch)
        self.assertEqual((line.speed, line.pitch), (300, 180))


if __name__ == '__main__':
    unittest.main()
