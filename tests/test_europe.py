"""European statements: the agent reads each country's statutory format, in its language, in euros.

One small set of accounts per format — Spanish PGC, French PCG, German HGB, Italian civil code — with
the layout, labels, numbering, units and dates each one really uses. For each, the agent must find every
line, rebuild operating profit exactly (reading check), balance the balance sheet and raise no false alarm.
"""
import io
import unittest

from openpyxl import Workbook

from dd_assistant.extract import ExtractionError, _num, extract_excel
from dd_assistant.metrics import compute_metrics, reading_checks
from dd_assistant.rules import alerts, evaluate


def _book(sheets: dict[str, list[list]]) -> io.BytesIO:
    wb = Workbook()
    wb.remove(wb.active)
    for title, rows in sheets.items():
        ws = wb.create_sheet(title)
        for row in rows:
            ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


class EuropeanFormat:
    SHEETS: dict
    EBIT: dict              # operating profit as published, EUR thousands

    @classmethod
    def setUpClass(cls):
        cls.ext = extract_excel(_book(cls.SHEETS), "accounts.xlsx")
        cls.d = cls.ext.data
        cls.m = compute_metrics(cls.d)

    def test_operating_profit_rebuilt_from_the_lines(self):
        checks = [c for c in reading_checks(self.d) if c["Check"].startswith("Operating profit")]
        self.assertTrue(checks)
        self.assertTrue(all(c["OK"] for c in checks), checks)
        for year, ebit in self.EBIT.items():
            self.assertAlmostEqual(self.m["ebitda"][year] + self.d.v("da", year), ebit)

    def test_balance_sheet_balances(self):
        for year in self.d.bs_years:
            self.assertAlmostEqual(self.m["bs_diff"][year], 0, msg=year)

    def test_euros(self):
        self.assertEqual(self.d.currency, "EUR")


class SpanishPGCTest(EuropeanFormat, unittest.TestCase):
    """Cuenta de pérdidas y ganancias and balance (PGC): numbered lines, subtotals before their lines."""
    SHEETS = {
        "Pérdidas y ganancias": [
            ["Miles de euros", "Ejercicio 2024", "Ejercicio 2023"],
            ["1. Importe neto de la cifra de negocios", 12000, 11000], ["4. Aprovisionamientos", -7200, -6600],
            ["5. Otros ingresos de explotación", 100, 80], ["6. Gastos de personal", -2100, -2000],
            ["7. Otros gastos de explotación", -1300, -1250], ["8. Amortización del inmovilizado", -400, -380],
            ["A.1) RESULTADO DE EXPLOTACIÓN", 1100, 850], ["13. Gastos financieros", -120, -130],
            ["A.3) RESULTADO ANTES DE IMPUESTOS", 980, 720], ["17. Impuesto sobre beneficios", -245, -180],
            ["A.5) RESULTADO DEL EJERCICIO", 735, 540]],
        "Balance": [
            ["Miles de euros", "31/12/2024", "31/12/2023"], ["ACTIVO"],
            ["A) ACTIVO NO CORRIENTE", 5000, 5100], ["II. Inmovilizado material", 4500, 4600],
            ["V. Inversiones financieras a largo plazo", 500, 500],
            ["B) ACTIVO CORRIENTE", 4000, 3700], ["II. Existencias", 1500, 1400],
            ["III. Deudores comerciales y otras cuentas a cobrar", 1800, 1700],
            ["V. Inversiones financieras a corto plazo", 200, 100],
            ["VII. Efectivo y otros activos líquidos equivalentes", 500, 500],
            ["TOTAL ACTIVO (A + B)", 9000, 8800], ["PATRIMONIO NETO Y PASIVO"],
            ["A) PATRIMONIO NETO", 4000, 3500], ["VII. Resultado del ejercicio", 735, 540],
            ["B) PASIVO NO CORRIENTE", 2500, 2800], ["I. Provisiones a largo plazo", 200, 200],
            ["II. Deudas con entidades de crédito", 2300, 2600],
            ["C) PASIVO CORRIENTE", 2500, 2500], ["III. Deudas con entidades de crédito", 900, 1000],
            ["V. Acreedores comerciales y otras cuentas a pagar", 1400, 1300],
            ["VI. Otras deudas con las Administraciones Públicas", 200, 200],
            ["TOTAL PATRIMONIO NETO Y PASIVO (A + B + C)", 9000, 8800]],
    }
    EBIT = {2024: 1100, 2023: 850}

    def test_lines(self):
        d = self.d
        self.assertEqual(d.v("vendas", 2024), 12000)
        self.assertEqual(d.v("aft", 2024), 4500)                 # non-current: the subtotal comes first
        self.assertEqual(d.v("fin_lp", 2024), 2300)
        self.assertEqual(d.v("fin_cp", 2024), 900)               # same label, current section
        self.assertEqual(d.v("pbt", 2024), 980)
        self.assertEqual(d.v("rl_dre", 2024), 735)
        found = {b.category: b for b in d.balance_items}
        self.assertTrue(found["Marketable securities and short-term investments"].include)   # current
        self.assertFalse(found["Provisions"].include)


class FrenchPCGTest(EuropeanFormat, unittest.TestCase):
    """Compte de résultat and bilan (PCG): liabilities not split by maturity, grand totals only."""
    SHEETS = {
        "Compte de résultat": [
            ["En milliers d'euros", "Exercice 2024", "Exercice 2023"],
            ["Chiffre d'affaires net", 10000, 9000], ["Achats de marchandises", -5000, -4500],
            ["Variation de stocks", 100, -50], ["Autres achats et charges externes", -1500, -1400],
            ["Impôts, taxes et versements assimilés", -150, -140], ["Salaires et traitements", -1600, -1500],
            ["Charges sociales", -600, -560], ["Dotations aux amortissements", -300, -280],
            ["Autres charges", -50, -40], ["Résultat d'exploitation", 900, 530], ["Charges financières", -80, -90],
            ["Impôts sur les bénéfices", -205, -110], ["Résultat net", 615, 330]],
        "Bilan": [
            ["En milliers d'euros", "31/12/2024", "31/12/2023"], ["ACTIF"],
            ["Immobilisations corporelles", 3000, 3100], ["Immobilisations financières", 500, 500],
            ["Total actif immobilisé", 3500, 3600], ["Stocks et en-cours", 1200, 1100],
            ["Clients et comptes rattachés", 1800, 1700], ["Autres créances", 200, 150], ["Disponibilités", 400, 350],
            ["Total actif circulant", 3600, 3300], ["TOTAL ACTIF", 7100, 6900], ["PASSIF"],
            ["Capital social", 1000, 1000], ["Résultat de l'exercice", 615, 330], ["Total capitaux propres", 3000, 2500],
            ["Provisions pour risques et charges", 200, 180],
            ["Emprunts et dettes auprès des établissements de crédit", 2000, 2300],
            ["Dettes fournisseurs et comptes rattachés", 1300, 1250], ["Dettes fiscales et sociales", 400, 450],
            ["Autres dettes", 200, 220], ["TOTAL PASSIF", 7100, 6900]],
    }
    EBIT = {2024: 900, 2023: 530}

    def test_lines(self):
        d = self.d
        self.assertEqual(d.v("pess", 2024), -2200)               # salaries + social charges
        self.assertEqual(d.v("cmv", 2024), -4900)                # purchases + change in stock
        self.assertEqual(d.v("forn", 2024), 1300)
        self.assertEqual(d.v("opc", 2024), 200 + 400 + 200 + 0)  # from 'Total passif': provisions, tax, other
        self.assertEqual(self.m["ni_diff"][2024], 0)


class GermanHGBTest(EuropeanFormat, unittest.TestCase):
    """GuV (Gesamtkostenverfahren) with expenses shown as positive numbers, and HGB Bilanz, in TEUR."""
    SHEETS = {
        "GuV": [
            ["TEUR", "GJ 2024", "GJ 2023"],
            ["1. Umsatzerlöse", 20000, 18000],
            ["2. Erhöhung oder Verminderung des Bestands an fertigen und unfertigen Erzeugnissen", 200, -100],
            ["3. Andere aktivierte Eigenleistungen", 150, 100], ["4. Sonstige betriebliche Erträge", 150, 100],
            ["5. Materialaufwand", 9000, 8200], ["6. Personalaufwand", 5000, 4700], ["7. Abschreibungen", 800, 750],
            ["8. Sonstige betriebliche Aufwendungen", 3000, 2800], ["9. Betriebsergebnis", 2700, 1650],
            ["10. Zinsen und ähnliche Aufwendungen", 200, 220], ["11. Steuern vom Einkommen und vom Ertrag", 750, 430],
            ["12. Jahresüberschuss", 1750, 1000]],
        "Bilanz": [
            ["TEUR", "31.12.2024", "31.12.2023"], ["AKTIVA"], ["A. Anlagevermögen"],
            ["Sachanlagen", 6000, 5800], ["B. Umlaufvermögen"], ["Vorräte", 3000, 2800],
            ["Forderungen aus Lieferungen und Leistungen", 2500, 2300],
            ["Kassenbestand, Guthaben bei Kreditinstituten", 800, 600], ["Summe Aktiva", 12300, 11500],
            ["PASSIVA"], ["A. Eigenkapital"], ["Gezeichnetes Kapital", 1000, 1000], ["Jahresüberschuss", 1750, 1000],
            ["Summe Eigenkapital", 5000, 4070], ["B. Rückstellungen"], ["Pensionsrückstellungen", 900, 850],
            ["Sonstige Rückstellungen", 400, 380], ["C. Verbindlichkeiten"],
            ["Verbindlichkeiten gegenüber Kreditinstituten", 4000, 4300],
            ["Verbindlichkeiten aus Lieferungen und Leistungen", 2000, 1900], ["Summe Passiva", 12300, 11500]],
    }
    EBIT = {2024: 2700, 2023: 1650}

    def test_positive_expenses_and_inventory_change(self):
        d = self.d
        self.assertEqual(d.v("cmv", 2024), -9000 + 200)          # the change in inventories is not flipped
        self.assertEqual(d.v("own", 2024), 150)                  # own work capitalised: inside EBITDA
        self.assertEqual(d.v("irc", 2024), -750)

    def test_pension_provisions_are_debt_like_and_leave_working_capital(self):
        pension = next(b for b in self.d.balance_items if b.category == "Post-employment benefit obligations")
        self.assertTrue(pension.include and pension.in_nwc)


class ItalianCivilCodeTest(EuropeanFormat, unittest.TestCase):
    """Conto economico (art. 2425 c.c.) in euros, costs as positive numbers under 'Costi della produzione'."""
    SHEETS = {
        "Conto economico": [
            ["Importi in euro", "Esercizio 2024", "Esercizio 2023"], ["A) Valore della produzione"],
            ["1) Ricavi delle vendite e delle prestazioni", 5000000, 4600000], ["5) Altri ricavi e proventi", 40000, 30000],
            ["Totale valore della produzione", 5040000, 4630000], ["B) Costi della produzione"],
            ["6) per materie prime, sussidiarie, di consumo e di merci", 2600000, 2400000],
            ["7) per servizi", 900000, 850000], ["8) per godimento di beni di terzi", 120000, 110000],
            ["9) per il personale", 800000, 760000], ["10) ammortamenti e svalutazioni", 150000, 140000],
            ["14) oneri diversi di gestione", 30000, 25000], ["Totale costi della produzione", 4600000, 4285000],
            ["Differenza tra valore e costi della produzione (A - B)", 440000, 345000],
            ["C) Proventi e oneri finanziari"], ["17) interessi e altri oneri finanziari", 40000, 45000],
            ["Risultato prima delle imposte (A - B + - C + - D)", 400000, 300000],
            ["20) Imposte sul reddito dell'esercizio, correnti, differite e anticipate", 100000, 75000],
            ["21) Utile (perdita) dell'esercizio", 300000, 225000]],
        "Stato patrimoniale": [
            ["Importi in euro", "31/12/2024", "31/12/2023"], ["Attivo"], ["B) Immobilizzazioni"],
            ["II - Immobilizzazioni materiali", 1500000, 1450000], ["Totale immobilizzazioni (B)", 1500000, 1450000],
            ["C) Attivo circolante"], ["I - Rimanenze", 700000, 650000], ["Crediti verso clienti", 900000, 820000],
            ["IV - Disponibilità liquide", 300000, 250000], ["Totale attivo circolante (C)", 1900000, 1720000],
            ["Totale attivo", 3400000, 3170000], ["Passivo"], ["A) Patrimonio netto"],
            ["IX - Utile (perdita) dell'esercizio", 300000, 225000], ["Totale patrimonio netto", 1600000, 1270000],
            ["C) Trattamento di fine rapporto di lavoro subordinato", 200000, 180000], ["D) Debiti"],
            ["Debiti verso banche", 1000000, 1150000], ["Debiti verso fornitori", 600000, 570000],
            ["Totale passivo", 3400000, 3170000]],
    }
    EBIT = {2024: 440, 2023: 345}

    def test_units_and_lines(self):
        d = self.d
        self.assertIn("euros, converted to EUR thousands", self.ext.method)
        self.assertEqual(d.v("vendas", 2024), 5000)
        self.assertEqual(d.v("fse", 2024), -(900 + 120))         # services + use of third-party assets
        self.assertEqual(d.v("pess", 2024), -800)
        self.assertEqual(d.v("juros", 2024), -40)
        severance = next(b for b in d.balance_items if b.category == "Post-employment benefit obligations")
        self.assertEqual(severance.values[2024], 200)             # TFR: debt-like in Italy


class EuropeanConventionsTest(unittest.TestCase):
    def test_european_number_formats(self):
        self.assertEqual(_num("1.234.567,8"), 1234567.8)
        self.assertEqual(_num("(1.234)"), -1234)
        self.assertEqual(_num("1234,5"), 1234.5)
        self.assertEqual(_num("1,234,567"), 1234567)
        self.assertEqual(_num("—"), 0)

    def test_other_currencies_are_refused(self):
        for note in ("(£ in thousands)", "USD millions", "CHF 000"):
            buf = _book({"Income statement": [[note], ["", 2025, 2024], ["Revenue", 5000, 4500],
                                              ["Cost of sales", -3000, -2700]]})
            with self.subTest(note=note), self.assertRaises(ExtractionError) as e:
                extract_excel(buf)
            self.assertIn("euros", str(e.exception))

    def test_no_false_alarm_on_clean_european_accounts(self):
        """The four formats above are healthy companies: only R18 (documents not provided) may fire."""
        for cls in (SpanishPGCTest, FrenchPCGTest, GermanHGBTest, ItalianCivilCodeTest):
            d = extract_excel(_book(cls.SHEETS)).data
            ids = [r.rule.id for r in alerts(evaluate(d, compute_metrics(d)))]
            with self.subTest(fmt=cls.__name__):
                self.assertEqual([i for i in ids if i != "R18"], [])


if __name__ == "__main__":
    unittest.main()
