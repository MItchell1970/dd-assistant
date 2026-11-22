"""Sectors and euros: the suggestion, the calibration and the formatting."""
import unittest
from dataclasses import replace
from pathlib import Path

from dd_assistant import sectors
from dd_assistant.extract import extract_excel
from dd_assistant.rules import RULES, calibrate
from dd_assistant.units import Money

DATA = Path(__file__).resolve().parents[1] / "data"


class SectorTest(unittest.TestCase):
    def test_suggested_from_what_the_company_declares(self):
        """The declared activity ('Atividade | …') or the legal name; the three companies of the demo keep their
        sector (from the legal name)."""
        expected = {"Duriva_data_room.xlsx": ("distribution", ["distribuicao"]),
                    "Velmora_data_room.xlsx": ("distribution", ["distribuicao"]),
                    "TAP_2025_published.xlsx": ("transport", ["transportes"]),
                    "Toyota_Caetano_2025_published.xlsx": ("automotive", ["toyota"]),
                    "Corticeira_Amorim_2025_published.xlsx": ("materials", ["corticeira"]),
                    "Toyota_Caetano_2024_published.xlsx": ("automotive", ["toyota"]),
                    "Corticeira_Amorim_2024_published.xlsx": ("materials", ["corticeira"])}
        for file, (key, words) in expected.items():
            ext = extract_excel(DATA / file)
            with self.subTest(file=file):
                s, found = sectors.suggest(ext.source_text, ext.company)
                self.assertEqual((s.key, found), (key, words))

    def test_listed_companies_from_their_declared_activity(self):
        """The ESEF tag of principal activities, first sentence, as filed (FY2025)."""
        declared = {
            "Jerónimo Martins, SGPS, S.A.": ("O Grupo atua predominantemente no sector da Distribuição Alimentar em "
                                             "Portugal, na Polónia, na Colômbia e, desde março de 2025, na Eslováquia",
                                             "consumer_retail"),   # food retail, not wholesale distribution
            "Iberdrola, S.A.": ("Producción de electricidad mediante fuentes renovables y convencionales.", "energy"),
            "EDP, S.A.": ("As atividades do Grupo EDP estão atualmente centradas, por um lado, nas áreas da produção, "
                          "transmissão, distribuição e comercialização de energia elétrica e, por outro lado, na área "
                          "da comercialização de gás natural. Complementarmente, o Grupo EDP dedica-se a atividades "
                          "nas áreas da engenharia", "energy"),
            "Schneider Electric SE": ("La Société (article 2 des statuts) a pour objet, directement ou indirectement, "
                                      "sous quelque forme que ce soit, en France et dans tous pays :", "general"),
        }
        for company, (activity, key) in declared.items():
            with self.subTest(company=company):
                s, words = sectors.suggest(f"Nature of business | {activity}", company)
                self.assertEqual(s.key, key)
                self.assertEqual(bool(words), key != "general")   # general without words: to be confirmed

    def test_words_elsewhere_in_the_data_room_do_not_count(self):
        text = "Customers | supermarkets, energy utilities, car dealers\nRevenue | 1000"
        self.assertEqual(sectors.suggest(text, "Acme, S.A."), (sectors.GENERAL, []))

    def test_a_tie_is_to_be_confirmed(self):
        self.assertEqual(sectors.suggest("Activity | Software and construction", "Acme")[1], [])

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


class EuroTest(unittest.TestCase):
    def test_formatting(self):
        self.assertEqual(Money().fmt(1415.2), "€1,415k")
        self.assertEqual(Money().fmt(-250), "-€250k")
        self.assertEqual(Money(millions=True).fmt(939061), "€939m")
        self.assertEqual(Money(millions=True).unit, "EUR m")

    def test_large_groups_in_millions(self):
        duriva = extract_excel(DATA / "Duriva_data_room.xlsx").data
        self.assertFalse(Money.for_data(duriva).millions)
        big = replace(duriva, lines={**duriva.lines, "vendas": {2025: 1_200_000.0}})
        self.assertTrue(Money.for_data(big).millions)

    def test_portuguese_words_are_not_currencies(self):
        """'qualquer semelhança com empresas reais' in Duriva's read-me is not Brazilian reais."""
        ext = extract_excel(DATA / "Duriva_data_room.xlsx")
        self.assertEqual(ext.data.currency, "EUR")
        self.assertIn("EUR thousands", ext.method)


if __name__ == "__main__":
    unittest.main()
