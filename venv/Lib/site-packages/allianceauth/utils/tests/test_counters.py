from unittest import TestCase
from unittest.mock import patch

from allianceauth.utils.counters import ItemCounter

MODULE_PATH = "allianceauth.utils.counters"

COUNTER_NAME = "test-counter"


class TestItemCounter(TestCase):
    def test_can_create_counter(self):
        # when
        counter = ItemCounter(COUNTER_NAME)
        # then
        self.assertIsInstance(counter, ItemCounter)

    def test_can_reset_counter_to_default(self):
        # given
        counter = ItemCounter(COUNTER_NAME)
        # when
        counter.reset()
        # then
        self.assertEqual(counter.value(), 0)

    def test_can_reset_counter_to_custom_value(self):
        # given
        counter = ItemCounter(COUNTER_NAME)
        # when
        counter.reset(42)
        # then
        self.assertEqual(counter.value(), 42)

    def test_can_increment_counter_by_default(self):
        # given
        counter = ItemCounter(COUNTER_NAME)
        counter.reset(0)
        # when
        counter.incr()
        # then
        self.assertEqual(counter.value(), 1)

    def test_can_increment_counter_by_custom_value(self):
        # given
        counter = ItemCounter(COUNTER_NAME)
        counter.reset(0)
        # when
        counter.incr(8)
        # then
        self.assertEqual(counter.value(), 8)

    def test_can_decrement_counter_by_default(self):
        # given
        counter = ItemCounter(COUNTER_NAME)
        counter.reset(9)
        # when
        counter.decr()
        # then
        self.assertEqual(counter.value(), 8)

    def test_can_decrement_counter_by_custom_value(self):
        # given
        counter = ItemCounter(COUNTER_NAME)
        counter.reset(9)
        # when
        counter.decr(8)
        # then
        self.assertEqual(counter.value(), 1)

    def test_can_decrement_counter_below_zero(self):
        # given
        counter = ItemCounter(COUNTER_NAME)
        counter.reset(0)
        # when
        counter.decr(1)
        # then
        self.assertEqual(counter.value(), -1)

    def test_can_not_decrement_counter_below_minimum(self):
        # given
        counter = ItemCounter(COUNTER_NAME, minimum=0)
        counter.reset(0)
        # when
        counter.decr(1)
        # then
        self.assertEqual(counter.value(), 0)

    def test_can_not_reset_counter_below_minimum(self):
        # given
        counter = ItemCounter(COUNTER_NAME, minimum=0)
        # when/then
        with self.assertRaises(ValueError):
            counter.reset(-1)

    def test_can_not_init_without_name(self):
        # when/then
        with self.assertRaises(ValueError):
            ItemCounter(name="")

    def test_can_ignore_invalid_values_when_incrementing(self):
        # given
        counter = ItemCounter(COUNTER_NAME)
        counter.reset(0)
        # when
        with patch(MODULE_PATH + ".cache.incr") as m:
            m.side_effect = ValueError
            counter.incr()
        # then
        self.assertEqual(counter.value(), 0)

    def test_can_ignore_invalid_values_when_decrementing(self):
        # given
        counter = ItemCounter(COUNTER_NAME)
        counter.reset(1)
        # when
        with patch(MODULE_PATH + ".cache.decr") as m:
            m.side_effect = ValueError
            counter.decr()
        # then
        self.assertEqual(counter.value(), 1)
