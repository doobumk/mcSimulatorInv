import unittest

from battery_line import BatteryLine
from machine import coordinate
from product_input import Product, Cell, product_input


class ProductInputTests(unittest.TestCase):
    def test_coordinates_types_and_independent_copies(self):
        source = product_input(coordinate(10, 20, 30), Product(size=(5, 6, 7)), 2, 2)
        batch = source.create_batch(8)
        self.assertEqual([(p.x, p.y, p.z) for p in batch], [(2, 20, 30), (10, 20, 30)])
        batch[0].x = 999
        self.assertEqual(source.product.x, 0)
        self.assertEqual(batch[1].x, 10)

    def test_periods_and_pause_resume(self):
        line = BatteryLine(inputs=[product_input(coordinate(0, 2, 3), Cell(size=(123, 600, 17.8)), 2, 3)])
        line.start_input()
        line.step(1)
        self.assertFalse(line.products)
        line.pause()
        line.step(10)
        line.start_input()
        line.start_input()  # repeated START must not inject or reset
        line.step(1)
        self.assertEqual(len(line.products), 3)
        self.assertEqual(line.products[-1].x, 0)
        line.step(2)
        self.assertEqual(len(line.products), 6)
        self.assertEqual(line.products[2].x, 600)
        line.clear()
        line.start_input()
        line.step(1)
        self.assertFalse(line.products)

    def test_multiple_products_and_step_size_independence(self):
        def make_line():
            return BatteryLine(inputs=[
                product_input(coordinate(0, 1, 2), Cell(size=(123, 600, 17.8)), 2, 1),
                product_input(coordinate(0, 3, 4), Product(size=(100, 100, 100)), 3, 2)])
        one, many = make_line(), make_line()
        one.start_input()
        many.start_input()
        one.step(6)
        for _ in range(60):
            many.step(.1)
        self.assertEqual(len(one.products), 7)
        self.assertEqual(len(many.products), 7)
        for a, b in zip(one.products, many.products):
            self.assertEqual(type(a), type(b))
            self.assertEqual((a.id, a.y, a.z), (b.id, b.y, b.z))
            self.assertAlmostEqual(a.x, b.x)
        self.assertEqual(len({p.id for p in one.products}), 7)

    def test_invalid_settings_atomic(self):
        source = product_input(coordinate(), Cell(size=(123, 600, 17.8)), 2, 1)
        for cycle, amount in [(0, 1), (-1, 1), (float('nan'), 1), (2, 0), (2, 1.5), (2, True)]:
            with self.assertRaises(ValueError):
                source.configure(cycle=cycle, amount=amount)
            self.assertEqual((source.cycle, source.amount), (2, 1))


if __name__ == '__main__':
    unittest.main()
