import unittest
from datetime import datetime

from cmit.shift import assign_shift, make_shift


class ShiftRulesTest(unittest.TestCase):
    def test_d1_window(self):
        shift = make_shift(datetime(2026, 5, 28).date(), "D1")
        self.assertEqual(shift.start.hour, 6)
        self.assertEqual(shift.end.hour, 18)
        self.assertEqual(shift.work_date.isoformat(), "2026-05-28")

    def test_d2_crosses_midnight(self):
        shift = make_shift(datetime(2026, 5, 28).date(), "D2")
        self.assertEqual(shift.start.isoformat(), "2026-05-28T18:00:00")
        self.assertEqual(shift.end.isoformat(), "2026-05-29T06:00:00")

    def test_assign_shift_after_midnight(self):
        shift = assign_shift(datetime(2026, 5, 29, 2, 30))
        self.assertEqual(shift.code, "D2")
        self.assertEqual(shift.work_date.isoformat(), "2026-05-28")


if __name__ == "__main__":
    unittest.main()

