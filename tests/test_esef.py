"""ESEF: the iXBRL annual report of a listed company, read from its tags.

The fixture is a small report package written here, laid out like a real one (EDP's FY2025 filing):
statements in the presentation linkbase, the company's own concepts anchored to IFRS, English and
Portuguese labels, a rounded duplicate in the management report, a segment and a half-year figure
that must be left out. The real EDP package (96 MB) is not in the project; reading it gives the
published operating profit to the thousand euros (2,999,414 in FY25).
"""
import io
import unittest
import zipfile

from openpyxl import Workbook

from dd_assistant import europe
from dd_assistant.dataroom import read_data_room
from dd_assistant.esef import _value, is_esef
from dd_assistant.extract import ExtractionError, extract_excel
from dd_assistant.metrics import compute_metrics, reading_checks
from dd_assistant.pipeline import analyse

IFRS = "https://xbrl.ifrs.org/taxonomy/2023-03-23/full_ifrs/full_ifrs-cor_2023-03-23.xsd#ifrs-full_"
OWN = "acme-2025-12-31.xsd#acme_"
# concept: (FY25, FY24) in EUR thousands, as tagged (expenses positive, a loss negative)
PL = {"Revenue": (10040, 9000), "acme:CostOfEnergySoldAndOther": (6000, 5400), "OtherIncome": (50, 40),
      "ServicesExpense": (1000, 950), "EmployeeBenefitsExpense": (800, 760), "OtherExpenseByNature": (150, 140),
      "ShareOfProfitLossOfAssociatesAndJointVenturesAccountedForUsingEquityMethod": (100, -20),
      "DepreciationAndAmortisationExpense": (700, 650), "acme:OperatingResult": (1540, 1120),
      "FinanceIncome": (20, 10), "FinanceCosts": (300, 280), "ProfitLossBeforeTax": (1260, 850),
      "IncomeTaxExpenseContinuingOperations": (290, 190), "ProfitLoss": (970, 660),
      "ProfitLossAttributableToOwnersOfParent": (930, 640)}
BS = {"PropertyPlantAndEquipment": (8000, 7600), "IntangibleAssetsOtherThanGoodwill": (1000, 1000),
      "acme:CollateralDeposits": (50, 40), "NoncurrentAssets": (9050, 8640), "Inventories": (300, 280),
      "CurrentTradeReceivables": (1600, 1500), "CashAndCashEquivalents": (900, 700), "CurrentAssets": (2800, 2480),
      "Assets": (11850, 11120), "IssuedCapital": (2000, 2000), "RetainedEarnings": (2850, 2310),
      "Equity": (4850, 4310), "LongtermBorrowings": (4000, 4000), "NoncurrentProvisionsForEmployeeBenefits": (200, 210),
      "NoncurrentLiabilities": (4200, 4210), "ShorttermBorrowings": (600, 500),
      "TradeAndOtherCurrentPayablesToTradeSuppliers": (1700, 1600), "CurrentTaxLiabilitiesCurrent": (500, 500),
      "CurrentLiabilities": (2800, 2600), "Liabilities": (7000, 6810), "EquityAndLiabilities": (11850, 11120)}
CF = {"ProfitLossBeforeTax": (1260, 850), "AdjustmentsForDepreciationAndAmortisationExpense": (700, 650),
      "CashFlowsFromUsedInOperations": (1700, 1350), "CashFlowsFromUsedInOperatingActivities": (1450, 1150),
      "acme:PaymentsForTangibleAndIntangibleAssets": (900, 800),
      "ProceedsFromSalesOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities": (10, 5),
      "CashFlowsFromUsedInInvestingActivities": (-890, -795),
      "ProceedsFromBorrowingsClassifiedAsFinancingActivities": (100, 100),
      "DividendsPaidClassifiedAsFinancingActivities": (400, 300), "InterestPaidClassifiedAsFinancingActivities": (60, 55),
      "CashFlowsFromUsedInFinancingActivities": (-360, -255)}
LABELS_EN = {"CostOfEnergySoldAndOther": ("label", "Cost of energy sold and other"),
             "OperatingResult": ("totalLabel", "Profit before financial income and expenses and income tax"),
             "CollateralDeposits": ("label", "Collateral deposits associated to financial debt"),
             "PaymentsForTangibleAndIntangibleAssets": ("label", "Payments for tangible and intangible assets")}
LABELS_PT = {"OperatingResult": ("label", "Resultado antes de resultados financeiros e impostos")}
ANCHORS = [("acme_CostOfEnergySoldAndOther", "ifrs-full_RawMaterialsAndConsumablesUsed"),
           ("acme_PaymentsForTangibleAndIntangibleAssets", "ifrs-full_PurchaseOfIntangibleAssetsClassifiedAsInvestingActivities"),
           ("acme_PaymentsForTangibleAndIntangibleAssets",
            "ifrs-full_PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities"),
           ("ifrs-full_NoncurrentFinancialAssets", "acme_CollateralDeposits")]   # narrower: keeps its own name
STATEMENTS = [
    ("Notes", "DisclosureOfRevenueAbstract", ["Revenue"]),                       # a note: not a statement
    ("OCI", "StatementOfComprehensiveIncomeAbstract", ["ProfitLoss", "ComprehensiveIncome"]),
    ("IncomeStatement", "IncomeStatementAbstract", list(PL)),
    ("FinancialPosition", "StatementOfFinancialPositionAbstract", [
        ("AssetsAbstract", [("NoncurrentAssetsAbstract", list(BS)[:4]), ("CurrentAssetsAbstract", list(BS)[4:8]),
                            "Assets"]),
        ("EquityAndLiabilitiesAbstract", [("EquityAbstract", list(BS)[9:12]), ("LiabilitiesAbstract", [
            ("NoncurrentLiabilitiesAbstract", list(BS)[12:15]), ("CurrentLiabilitiesAbstract", list(BS)[15:19]),
            "Liabilities"]), "EquityAndLiabilities"])]),
    ("CashFlows", "StatementOfCashFlowsAbstract", list(CF) + ["CashAndCashEquivalents"]),
]


def _href(concept: str) -> str:
    return OWN + concept[5:] if concept.startswith("acme:") else IFRS + concept


def _fact(concept, context, value, unit="u-1"):
    name = concept if ":" in concept else f"ifrs-full:{concept}"
    if value == 0:
        return f'<ix:nonFraction name="{name}" contextRef="{context}" unitRef="{unit}" format="ixt:fixed-zero">-' \
               '</ix:nonFraction>'
    sign = ' sign="-"' if value < 0 else ""
    shown = f"{abs(value):,.0f}".replace(",", ".")
    return (f'<ix:nonFraction name="{name}" contextRef="{context}" unitRef="{unit}" decimals="-3" scale="3" '
            f'format="ixt:num-comma-decimal"{sign}>{shown}</ix:nonFraction>')


def _context(cid, period, segment=""):
    return (f'<xbrli:context id="{cid}"><xbrli:entity><xbrli:identifier scheme="http://standards.iso.org/iso/17442">'
            f'5299000ACMEENERGIA42</xbrli:identifier>{segment}</xbrli:entity><xbrli:period>{period}</xbrli:period>'
            f'</xbrli:context>')


def _report(currency: str) -> str:
    year = lambda y: f"<xbrli:startDate>{y}-01-01</xbrli:startDate><xbrli:endDate>{y}-12-31</xbrli:endDate>"
    contexts = [_context("c-1", year(2025)), _context("c-2", year(2024)),
                _context("c-3", "<xbrli:instant>2025-12-31</xbrli:instant>"),
                _context("c-4", "<xbrli:instant>2024-12-31</xbrli:instant>"),
                _context("c-5", "<xbrli:instant>2023-12-31</xbrli:instant>"),
                _context("c-h1", "<xbrli:startDate>2025-01-01</xbrli:startDate><xbrli:endDate>2025-06-30"
                                 "</xbrli:endDate>"),
                _context("c-seg", year(2025), '<xbrli:segment><xbrldi:explicitMember dimension="ifrs-full:SegmentsAxis">'
                                              'acme:RenewablesMember</xbrldi:explicitMember></xbrli:segment>')]
    rows = []
    for table, (now, before) in ((PL, ("c-1", "c-2")), (BS, ("c-3", "c-4")), (CF, ("c-1", "c-2"))):
        rows += [f"<tr><td>{c}</td><td>{_fact(c, now, v25)}</td><td>{_fact(c, before, v24)}</td></tr>"
                 for c, (v25, v24) in table.items()]
    rows.append(f"<tr><td>Cash 2023</td><td>{_fact('CashAndCashEquivalents', 'c-5', 600)}</td></tr>")
    return f"""<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"
 xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:xbrldi="http://xbrl.org/2006/xbrldi">
<head><title>Acme Energia 2025</title></head><body>
<div style="display:none"><ix:header><ix:resources>{''.join(contexts)}
<xbrli:unit id="u-1"><xbrli:measure>iso4217:{currency}</xbrli:measure></xbrli:unit>
<xbrli:unit id="u-2"><xbrli:measure>xbrli:shares</xbrli:measure></xbrli:unit>
</ix:resources></ix:header></div>
<p>Highlights: revenue of EUR <ix:nonFraction name="ifrs-full:Revenue" contextRef="c-1" unitRef="u-1" decimals="-5"
 scale="6" format="ixt:num-dot-decimal">10.0</ix:nonFraction> million (renewables:
 {_fact('Revenue', 'c-seg', 4000)}; first half: {_fact('Revenue', 'c-h1', 5000)}).</p>
<p><ix:nonFraction name="ifrs-full:NumberOfSharesOutstanding" contextRef="c-3" unitRef="u-2" decimals="0"
 format="ixt:num-comma-decimal">1.000.000</ix:nonFraction> shares.</p>
<p><ix:nonNumeric name="ifrs-full:NameOfReportingEntityOrOtherMeansOfIdentification" contextRef="c-1">Acme Energia,
 S.A.</ix:nonNumeric> · <ix:nonNumeric name="ifrs-full:CountryOfIncorporation" contextRef="c-1">Portugal</ix:nonNumeric>
 · <ix:nonNumeric name="ifrs-full:DescriptionOfNatureOfEntitysOperationsAndPrincipalActivities" contextRef="c-1">Wind
 and solar electricity generation.</ix:nonNumeric></p>
<table>{''.join(rows)}</table></body></html>"""


def _tree(spec, locs, arcs, parent=None):
    """Presentation arcs for a nested spec: 'Concept' or ('ConceptAbstract', [children])."""
    for order, item in enumerate(spec, 1):
        concept, kids = item if isinstance(item, tuple) else (item, [])
        label = f"loc{len(locs)}"
        locs.append(f'<link:loc xlink:type="locator" xlink:href="{_href(concept)}" xlink:label="{label}"/>')
        if parent:
            arcs.append(f'<link:presentationArc xlink:type="arc" xlink:arcrole="http://www.xbrl.org/2003/arcrole/'
                        f'parent-child" xlink:from="{parent}" xlink:to="{label}" order="{order}"/>')
        _tree(kids, locs, arcs, label)


def _linkbase(body: str) -> str:
    return ('<?xml version="1.0" encoding="utf-8"?><link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase" '
            f'xmlns:xlink="http://www.w3.org/1999/xlink">{body}</link:linkbase>')


def _presentation() -> str:
    links = []
    for role, root, children in STATEMENTS:
        locs, arcs = [], []
        _tree([(root, children)], locs, arcs)
        links.append(f'<link:presentationLink xlink:type="extended" xlink:role="http://www.acme.pt/role/{role}">'
                     f'{"".join(locs + arcs)}</link:presentationLink>')
    return _linkbase("".join(links))


def _labels(labels: dict, lang: str) -> str:
    parts = []
    for concept, (role, text) in labels.items():
        parts += [f'<link:loc xlink:type="locator" xlink:href="{OWN}{concept}" xlink:label="loc_{concept}"/>',
                  f'<link:label xlink:type="resource" xlink:label="lab_{concept}" xlink:role="http://www.xbrl.org/2003/'
                  f'role/{role}" xml:lang="{lang}">{text}</link:label>',
                  f'<link:labelArc xlink:type="arc" xlink:arcrole="http://www.xbrl.org/2003/arcrole/concept-label" '
                  f'xlink:from="loc_{concept}" xlink:to="lab_{concept}"/>']
    return _linkbase(f'<link:labelLink xlink:type="extended" xlink:role="http://www.xbrl.org/2003/role/link">'
                     f'{"".join(parts)}</link:labelLink>')


def _definition() -> str:
    parts = []
    for i, (wide, narrow) in enumerate(ANCHORS):
        href = lambda c: (IFRS + c[10:]) if c.startswith("ifrs-full_") else OWN + c[5:]
        parts += [f'<link:loc xlink:type="locator" xlink:href="{href(wide)}" xlink:label="w{i}"/>',
                  f'<link:loc xlink:type="locator" xlink:href="{href(narrow)}" xlink:label="n{i}"/>',
                  f'<link:definitionArc xlink:type="arc" xlink:arcrole="http://www.esma.europa.eu/xbrl/esef/arcrole/'
                  f'wider-narrower" xlink:from="w{i}" xlink:to="n{i}"/>']
    return _linkbase('<link:definitionLink xlink:type="extended" xlink:role="http://www.esma.europa.eu/xbrl/role/'
                     f'all/ias_1_2014-03-05_role-610000">{"".join(parts)}</link:definitionLink>')


def package(currency: str = "EUR") -> bytes:
    buf = io.BytesIO()
    base, tax = "acme-2025-12-31", "acme-2025-12-31/www.acme.pt/2025-12-31/acme-2025-12-31"
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(f"{base}/META-INF/reportPackage.json", '{"documentInfo": {"documentType": "esef"}}')
        z.writestr(f"{base}/reports/{base}.xhtml", _report(currency))
        z.writestr(f"{tax}_pre.xml", _presentation())
        z.writestr(f"{tax}_lab-en.xml", _labels(LABELS_EN, "en"))
        z.writestr(f"{tax}_lab-pt.xml", _labels(LABELS_PT, "pt"))
        z.writestr(f"{tax}_def.xml", _definition())
    return buf.getvalue()


class EsefTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.zip = package()
        cls.ext = read_data_room([("acme-2025-12-31.zip", cls.zip)])
        cls.d = cls.ext.data

    def test_recognises_a_report_package(self):
        self.assertTrue(is_esef("acme.zip", self.zip))
        self.assertFalse(is_esef("other.zip", zipfile_with("notes.txt")))
        self.assertIn("ESEF (iXBRL)", self.ext.method)
        self.assertEqual(self.ext.company, "Acme Energia, S.A.")
        self.assertEqual(self.ext.files[0]["Read as"], "ESEF — tagged financial statements (iXBRL)")

    def test_figures_come_from_the_tags(self):
        d = self.d
        self.assertEqual(d.years, [2024, 2025])
        self.assertEqual(d.v("vendas", 2025), 10040)   # the precise figure, not the rounded '10.0 million',
        self.assertEqual(d.v("vendas", 2024), 9000)    # the segment or the first half
        self.assertEqual(d.v("cmv", 2025), -6000)      # expenses are positive in XBRL: costs in the model
        self.assertEqual(d.v("assoc", 2024), -20)      # a loss keeps its sign
        self.assertEqual(d.v("opinc", 2025), 1540)
        self.assertEqual(d.v("pbt", 2025), 1260)
        self.assertEqual(d.v("irc", 2025), -290)
        self.assertEqual((d.v("fin_lp", 2025), d.v("fin_cp", 2025), d.v("caixa", 2025)), (4000, 600, 900))
        self.assertEqual((d.v("cli", 2025), d.v("forn", 2025)), (1600, 1700))
        self.assertEqual((d.v("cx_ini", 2025), d.v("cx_ini", 2024), d.v("cx_fim", 2025)), (700, 600, 900))
        self.assertEqual(d.v("fco", 2025), 1450)
        self.assertEqual(d.v("cgo", 2025), 1700)

    def test_own_concepts_are_read_through_their_anchors(self):
        d, found = self.d, {i["key"]: i["Found as"] for i in self.ext.items}
        self.assertEqual(found["cmv"], "Cost of materials consumed (Cost of energy sold and other)")
        self.assertEqual(d.v("capex", 2025), -900)     # contains PPE and intangible purchases
        self.assertTrue(found["capex"].startswith("Purchase of property, plant and equipment and purchase of "
                                                  "intangible assets"))
        # no anchor: understood from the English label (the Portuguese one is not used)
        self.assertEqual(found["opinc"], "Profit before financial income and expenses and income tax")
        restricted = [b for b in d.balance_items if b.category == "Restricted cash"]
        self.assertEqual([(b.label, b.include) for b in restricted],
                         [("Collateral deposits associated to financial debt", False)])

    def test_every_figure_keeps_its_tag(self):
        s = self.d.sources
        self.assertEqual(s["vendas"], "ifrs-full:Revenue")
        self.assertEqual(s["cmv"], "acme:CostOfEnergySoldAndOther")
        self.assertEqual(s["oac"], "ifrs-full:CurrentAssets less the lines identified")
        self.assertEqual(s["cx_ini"], "ifrs-full:CashAndCashEquivalents (opening)")
        self.assertIn("Revenue [ifrs-full:Revenue] | FY24: 9000 | FY25: 10040", self.ext.source_text)
        self.assertIn("Country of incorporation | Portugal", self.ext.source_text)

    def test_reading_checks_pass(self):
        checks = reading_checks(self.d)
        self.assertEqual([c["OK"] for c in checks], [True, True])     # operating profit, both years
        m = compute_metrics(self.d)
        self.assertEqual(m["ebitda"][2025], 10040 - 6000 + 50 - 1000 - 800 - 150 + 100)
        for year in self.d.years:
            self.assertEqual(m["bs_diff"][year], 0, f"balance sheet {year}")

    def test_country_comes_from_the_report(self):
        country, why = europe.suggest(self.ext.source_text, self.ext.company)
        self.assertEqual(country.code, "PT")
        self.assertIn("ESEF", why)
        a = analyse(self.ext)
        self.assertEqual((a.country.code, a.sector.key), ("PT", "energy"))
        self.assertIn("IFRS", a.country.framework)                    # an ESEF filing is consolidated IFRS
        self.assertEqual([c for c in a.checks if not c["OK"]], [])

    def test_with_other_workbooks_each_file_is_named(self):
        wb = Workbook()
        ws = wb.active
        ws.title = "Sales by customer"
        for row in (["Customer", 2024, 2025], ["Rede Nacional", 3100, 3300], ["Other", 5900, 6740]):
            ws.append(row)
        buf = io.BytesIO()
        wb.save(buf)
        ext = read_data_room([("acme-2025-12-31.zip", self.zip), ("Customers.xlsx", buf.getvalue()),
                              ("Board minutes.txt", b"Minutes of the board")])
        d = ext.data
        self.assertEqual(d.sources["vendas"], "acme-2025-12-31.zip › ifrs-full:Revenue")
        self.assertEqual(d.clients_source, "Customers.xlsx › Sales by customer!B2:C2")
        self.assertEqual(d.clients[0].values[2025], 3300)
        self.assertEqual([f["File"] for f in ext.files], ["acme-2025-12-31.zip", "Customers.xlsx", "Board minutes.txt"])
        self.assertIn("ESEF (iXBRL) — each line read from its tag and Excel", ext.method)

    def test_euros_only(self):
        with self.assertRaisesRegex(ExtractionError, "USD"):
            read_data_room([("us-2025.zip", package("USD"))])

    def test_the_report_alone_asks_for_the_package(self):
        report = zipfile.ZipFile(io.BytesIO(self.zip)).read("acme-2025-12-31/reports/acme-2025-12-31.xhtml")
        with self.assertRaisesRegex(ExtractionError, "report package"):
            read_data_room([("acme-2025-12-31.xhtml", report)])

    def test_one_report_at_a_time(self):
        with self.assertRaisesRegex(ExtractionError, "one ESEF report"):
            read_data_room([("a.zip", self.zip), ("b.zip", self.zip)])

    def test_number_formats(self):
        self.assertEqual(_value("1.234.567,8", {"format": "ixt:num-comma-decimal", "scale": "3"}), 1234567.8)
        self.assertEqual(_value("1,234,567.8", {"format": "ixt:num-dot-decimal", "scale": "3"}), 1234567.8)
        self.assertEqual(_value("2,5", {"format": "ixt:num-comma-decimal", "scale": "6", "sign": "-"}), -2500)
        self.assertEqual(_value("750 000", {"format": "ixt:num-dot-decimal"}), 750)    # euros -> EUR thousands
        self.assertEqual(_value("-", {"format": "ixt:fixed-zero", "scale": "3"}), 0)


def zipfile_with(name: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(name, "x")
    return buf.getvalue()


class AssociatesTest(unittest.TestCase):
    """The share of associates and joint ventures counts in EBITDA only where the company puts it, above
    operating profit (EDP); below it (most groups), it stays out."""

    def _read(self, rows):
        wb = Workbook()
        ws = wb.active
        ws.title = "Income statement"
        ws.append(["EUR thousands", 2024, 2025])
        for row in rows:
            ws.append(row)
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return extract_excel(buf, "group.xlsx").data

    def test_above_operating_profit_it_is_in_ebitda(self):
        d = self._read([["Revenue", 1000, 1100], ["Cost of materials consumed", -600, -650], ["Staff costs", -200, -210],
                        ["Share of profit of associates and joint ventures", 30, -10],
                        ["Depreciation and amortisation", -50, -55], ["Operating profit", 180, 175]])
        self.assertEqual(d.v("assoc", 2025), -10)
        self.assertEqual([c["OK"] for c in reading_checks(d)], [True, True])

    def test_below_operating_profit_it_is_not(self):
        d = self._read([["Revenue", 1000, 1100], ["Cost of materials consumed", -600, -650], ["Staff costs", -200, -210],
                        ["Depreciation and amortisation", -50, -55], ["Operating profit", 150, 185],
                        ["Share of profit of associates and joint ventures", 30, -10], ["Profit before tax", 180, 175]])
        self.assertIsNone(d.lines.get("assoc"))
        self.assertEqual([c["OK"] for c in reading_checks(d)], [True, True])


if __name__ == "__main__":
    unittest.main()
