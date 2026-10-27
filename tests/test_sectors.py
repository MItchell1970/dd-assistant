"""Sectors and currencies: the suggestion, the calibration and the formatting."""
import io
import unittest
from pathlib import Path

from openpyxl import Workbook

from dd_assistant import sectors
from dd_assistant.extract import extract_excel
from dd_assistant.rules import RULES, calibrate
from dd_assistant.units import Money

DATA = Path(__file__).resolve().parents[1] / "data"


class SectorTest(unittest.TestCase):
    def test_suggested_from_the_data_room(self):
        expected = {"Duriva_data_room.xlsx": "distribution", "Velmora_data_room.xlsx": "distribution",
                    "Toyota_Caetano_2024_published.xlsx": "automotive",
                    "Corticeira_Amorim_2024_published.xlsx": "materials", "Apple_FY2024_published.xlsx": "hardware"}
        for file, key in expected.items():
            ext = extract_excel(DATA / file)
            with self.subTest(file=file):
                self.assertEqual(sectors.suggest(ext.source_text, ext.company)[0].key, key)

    def test_nothing_to_go_on_means_general(self):
        self.assertEqual(sectors.suggest("", "Acme")[0].key, "general")

    def test_general_keeps_the_template_thresholds(self):
        """The parity tests rely on it: without a sector, the rules are those of the Excel template."""
        self.assertEqual([(r.id, r.limit) for r in calibrate(RULES, None)], [(r.id, r.limit) for r in RULES])

    def test_calibration_is_explained(self):
        rules = {r.id: r for r in calibrate(RULES, "software")}
        self.assertEqual(rules["R10"].limit, 0.80)
        self.assertIn("general threshold 70%", rules["R10"].calibration)
        self.assertIn("calibrated for Software & SaaS", rules["R10"].rule_text())

    def test_every_sector_is_complete(self):
        ids = {r.id for r in RULES}
        for s in sectors.SECTORS:
            with self.subTest(sector=s.key):
                self.assertTrue(set(s.calibration) <= ids)
                self.assertEqual(set(s.benchmarks) - {"industry", "firms"}, set(sectors.BENCHMARK_LABELS))
                if s.key != "general":
                    self.assertGreaterEqual(len(s.lens), 5)
                    self.assertTrue(s.keywords)


class CurrencyTest(unittest.TestCase):
    def test_formatting(self):
        self.assertEqual(Money("EUR").fmt(1415.2), "€1,415k")
        self.assertEqual(Money("EUR").fmt(-250), "-€250k")
        self.assertEqual(Money("USD", millions=True).fmt(134661000), "$134,661m")
        self.assertEqual(Money("GBP").fmt(2500), "£2,500k")
        self.assertEqual(Money("USD", millions=True).unit, "USD m")

    def test_large_companies_in_millions(self):
        apple = extract_excel(DATA / "Apple_FY2024_published.xlsx").data
        duriva = extract_excel(DATA / "Duriva_data_room.xlsx").data
        self.assertTrue(Money.for_data(apple).millions)
        self.assertFalse(Money.for_data(duriva).millions)

    def test_currency_from_symbols_and_unit_note(self):
        wb = Workbook()
        ws = wb.active
        ws.title = "Income statement"
        ws.append(["Consolidated income statement"])
        ws.append(["(£ in thousands)"])
        ws.append(["", 2025, 2024])
        ws.append(["Revenue", 5000, 4500])
        ws.append(["Cost of sales", -3000, -2700])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        ext = extract_excel(buf)
        self.assertEqual(ext.data.currency, "GBP")
        self.assertIn("GBP thousands", ext.method)

    def test_portuguese_words_are_not_currencies(self):
        """'qualquer semelhança com empresas reais' in Duriva's read-me is not Brazilian reais."""
        ext = extract_excel(DATA / "Duriva_data_room.xlsx")
        self.assertEqual(ext.data.currency, "EUR")
        self.assertIn("EUR thousands", ext.method)


if __name__ == "__main__":
    unittest.main()
