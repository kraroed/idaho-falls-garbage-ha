import importlib.util
import pathlib
import unittest
from datetime import date

path = (
    pathlib.Path(__file__).parent.parent
    / "custom_components/idaho_falls_garbage/schedule.py"
)
spec = importlib.util.spec_from_file_location("schedule", path)
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)

DM = s.build_delay_map([2025, 2026, 2027])


class ScheduleTests(unittest.TestCase):
    def test_holiday_dates_2026(self):
        h = s.holiday_dates(2026)
        self.assertEqual(h["memorial_day"], date(2026, 5, 25))
        self.assertEqual(h["labor_day"], date(2026, 9, 7))
        self.assertEqual(h["thanksgiving"], date(2026, 11, 26))

    def test_thanksgiving_2026(self):
        a = lambda d: s.actual_pickup(d, DM)[0]
        self.assertEqual(a(date(2026, 11, 25)), date(2026, 11, 25))
        self.assertEqual(a(date(2026, 11, 26)), date(2026, 11, 27))
        self.assertEqual(a(date(2026, 11, 27)), date(2026, 11, 28))

    def test_memorial_day_2026_shifts_whole_week(self):
        a = lambda d: s.actual_pickup(d, DM)[0]
        self.assertEqual(a(date(2026, 5, 25)), date(2026, 5, 26))
        self.assertEqual(a(date(2026, 5, 29)), date(2026, 5, 30))

    def test_christmas_2026_friday(self):
        self.assertEqual(
            s.actual_pickup(date(2026, 12, 25), DM)[0], date(2026, 12, 26)
        )

    def test_new_years_day_2026_thursday(self):
        self.assertEqual(
            s.actual_pickup(date(2026, 1, 1), DM)[0], date(2026, 1, 2)
        )
        self.assertEqual(
            s.actual_pickup(date(2026, 1, 2), DM)[0], date(2026, 1, 3)
        )

    def test_labor_day_2026_shifts_rest_of_week(self):
        self.assertEqual(
            s.actual_pickup(date(2026, 9, 7), DM)[0], date(2026, 9, 8)
        )
        self.assertEqual(
            s.actual_pickup(date(2026, 9, 11), DM)[0], date(2026, 9, 12)
        )

    def test_weekend_independence_day_and_observed_friday_do_not_shift(self):
        # In 2026 Independence Day is Saturday and the city ran Friday,
        # July 3 on its normal schedule.
        self.assertEqual(
            s.actual_pickup(date(2026, 7, 3), DM)[0], date(2026, 7, 3)
        )

    def test_weekend_holiday_no_effect(self):
        self.assertEqual(
            s.actual_pickup(date(2026, 7, 3), DM)[0], date(2026, 7, 3)
        )

    def test_non_delay_holiday(self):
        # The city lists MLK Day, Presidents Day, Juneteenth,
        # Columbus Day, and Veterans Day as on-schedule in 2026.
        for pickup in (
            date(2026, 1, 19),
            date(2026, 2, 16),
            date(2026, 6, 19),
            date(2026, 10, 12),
            date(2026, 11, 11),
        ):
            with self.subTest(pickup=pickup):
                self.assertEqual(s.actual_pickup(pickup, DM)[0], pickup)

    def test_ignored_and_extra(self):
        dm = s.build_delay_map([2026], ignored={"labor_day"})
        self.assertEqual(
            s.actual_pickup(date(2026, 9, 7), dm)[0], date(2026, 9, 7)
        )
        dm = s.build_delay_map([2026], extra_dates={date(2026, 2, 3)})
        self.assertEqual(
            s.actual_pickup(date(2026, 2, 4), dm)[0], date(2026, 2, 5)
        )

    def test_upcoming(self):
        up = s.upcoming_pickups(date(2026, 11, 24), "thursday", DM, 2)
        self.assertEqual(
            [u[0] for u in up], [date(2026, 11, 27), date(2026, 12, 3)]
        )
        self.assertTrue(up[0][2])

    def test_today_is_pickup(self):
        up = s.upcoming_pickups(date(2026, 10, 27), "tuesday", DM, 1)
        self.assertEqual(up[0][0], date(2026, 10, 27))

    def test_pickups_in_range(self):
        out = s.pickups_in_range(
            date(2026, 11, 23), date(2026, 12, 6), "thursday", DM
        )
        self.assertEqual(
            [o[0] for o in out], [date(2026, 11, 27), date(2026, 12, 3)]
        )

    def test_range_inclusive_bounds(self):
        out = s.pickups_in_range(
            date(2026, 10, 27), date(2026, 10, 27), "tuesday", DM
        )
        self.assertEqual([o[0] for o in out], [date(2026, 10, 27)])


if __name__ == "__main__":
    unittest.main()
