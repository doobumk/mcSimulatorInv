import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from battery_line import BatteryLine
from line_datasheet import BatteryFrame, LineUnit, COLUMNS
from machine import frame, unit, machine


class BatteryLineTests(unittest.TestCase):
    def test_default_datasheet_preserves_original_layout(self):
        line = BatteryLine()
        self.assertIsInstance(line, machine)
        self.assertTrue(all(isinstance(f, BatteryFrame) and isinstance(f, frame) for f in line.frames))
        self.assertIsInstance(line.units[0], unit)
        self.assertIsInstance(line.units[0], LineUnit)
        self.assertEqual([(f.length, f.width) for f in line.frames], [(4970, 1860), (3445, 1860), (3415, 2210)])
        self.assertEqual((line.LINE_START, line.LINE_END, line.BELT_TOP), (-5875, 5875, 1280))
        self.assertEqual(line.frames[0].x_end, line.frames[1].x_start)
        self.assertEqual(line.frames[1].x_end, line.frames[2].x_start)

    def make_datasheet(self, directory, rows):
        path = Path(directory) / "custom.csv"
        path.write_text(','.join(COLUMNS) + '\n' + '\n'.join(rows), encoding='utf-8-sig')
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
        positions = sorted(c.x for c in line.cells)
        self.assertTrue(all(b - a >= 180 for a, b in zip(positions, positions[1:])))

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
