"""Standard-library tests: no database, Docker, network or app startup."""

import unittest
from decimal import Decimal

from app.services.safe_formula import FormulaError, evaluate, parse


class SafeFormulaTests(unittest.TestCase):
    def test_inspected_excel_arithmetic_and_rounding(self):
        self.assertEqual(evaluate("ROUND((SUM(a,b,c)+d*1+e*1)/5,1)",
                                  dict(a=10, b=12, c=14, d=16, e=18)), Decimal("14.0"))
        self.assertEqual(evaluate("ROUND(MEAN(a,b),1)", dict(a=14, b=20)), Decimal("17.0"))
        self.assertEqual(evaluate("ROUND(a,1)", dict(a="16.45")), Decimal("16.5"))

    def test_operations_and_functions(self):
        self.assertEqual(evaluate("MAX(a,b)-MIN(a,b)+SUM(1,-2,+3)", dict(a=10, b=4)), 8)

    def test_missing_is_distinct_from_zero(self):
        self.assertIsNone(evaluate("SUM(a,b)", dict(a=None, b=0)))
        self.assertEqual(evaluate("SUM(a,b)", dict(a=0, b=0)), 0)

    def test_rejects_code_and_non_numeric_language(self):
        for source in ["__import__('os')", "a.__class__", "a[0]", "[x for x in a]",
                       "lambda: 1", "a**2", "True", "'1'", "(x:=1)", "open(1)",
                       "SUM(*a)", "SUM(a=1)", "ROUND(a,b)", "ROUND(a,5)"]:
            with self.subTest(source=source), self.assertRaises(FormulaError):
                evaluate(source, dict(a=1, b=2))

    def test_invalid_numeric_values(self):
        for value in [True, float("nan"), float("inf"), "NaN", "1e100", "x", object()]:
            with self.subTest(value=type(value).__name__), self.assertRaises(FormulaError):
                evaluate("a", dict(a=value))

    def test_division_by_zero_and_unknown_reference(self):
        for expression in ["1/0", "missing+1", "1000000000*1000000000"]:
            with self.subTest(expression=expression), self.assertRaises(FormulaError):
                evaluate(expression, {})

    def test_complexity_limits(self):
        for expression in ["1+" * 300 + "1", "+" * 25 + "1", "SUM(" + "1," * 33 + "1)"]:
            with self.assertRaises(FormulaError):
                parse(expression, {})


if __name__ == "__main__":
    unittest.main()
