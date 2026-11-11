"""TAP — Transportes Aéreos Portugueses, S.A. — consolidated statements FY2024/FY2023 copied as printed in the 2024
Consolidated Annual Report (English translation; the Portuguese original prevails): statement of financial position
p.54, income statement p.55, cash flow statement p.58, notes 10 (p.123) and 20 (p.145) — PDF page numbers. Amounts
in euros, as printed.

Subtotals the report prints without a label are labelled here in square brackets, so a reader can tell them from
the printed labels; nothing else is added. The 2024 figures are the ones first published in this report, before the
restatement shown in the 2025 Integrated Report (scripts/real_tap.py).
"""
import sys
from pathlib import Path

from openpyxl import Workbook

URL = ("https://publish-p133109-e1368204.adobeaemcloud.com/content/dam/tap-institucional/media/pdfs/investidores/"
       "info-financeira/2024/en/RC-TAPSA-Consolidado-2024-ENG-FINAL.pdf")
SHA256 = "76f3fb95e45374a65867ebd9c122a0ce4149a705aa9fad881ec13435e7b93530"
UNIT = "Amounts stated in euros"
BS = [  # label, note, 2024, 2023
    ["ASSETS"],
    ["Non-current assets"],
    ["Tangible fixed assets", 4, 3153399157, 3181168268], ["Investment properties", 5, 1198000, 1903882],
    ["Intagible assets", 6, 31088687, 22489747], ["Goodwill", 7, 180135637, "-"],
    ["Other financial assets", 8, 680937, 488745], ["Other non current assets", 13, 14259503, 15080108],
    ["Deferred tax assets", 9, 471047253, 486302382], ["Other receivables", 10, 151525928, 120939688],
    ["[Total non-current assets — printed without a label]", None, 4003335102, 3828372820],
    ["Current Assets"],
    ["Inventories", 11, 97524652, 78716635], ["Other receivables", 10, 876762279, 1128374337],
    ["Income tax receivable", 12, 13027371, 3226450], ["Other current assets", 13, 97045480, 63964685],
    ["Cash and cash equivalents", 14, 651642530, 789387698],
    ["[Total current assets — printed without a label]", None, 1736002312, 2063669805],
    ["Total Assets", None, 5739337414, 5892042625],
    ["EQUITY AND LIABILITIES"],
    ["Equity"],
    ["Share Capital", 15, 313600000, 980000000], ["Supplementary capital contributions", 15, 343000000, "-"],
    ["Legal reserves", 16, 8300000, 8300000], ["Hedge reserves", 16, -1343925, -450915],
    ["Other reserves", 16, -108853600, -27332786], ["Other variations in equity", 16, "-", -9459912],
    ["Retained earnings", 16, -23075867, -514393395], ["Net income/(loss) for the year", None, 53721980, 177260543],
    ["Total equity of the Group", None, 585348588, 613923535], ["Non-controlling interests", 15, "-", "-"],
    ["Total equity", None, 585348588, 613923535],
    ["Non-current liabilities"],
    ["Deferred tax liabilities", 9, 84240222, 82913685], ["Post-employment benefits obligations", 17, 186458338, 176722477],
    ["Provisions", 18, 472792114, 305234778], ["Restructuring provision", 18, 182792, 2108784],
    ["Borrowings", 19, 513045714, 200003376], ["Lease liabilities with purchase option", 19, 760801016, 698261176],
    ["Lease liabilities without purchase option", 19, 1295428780, 1498461708],
    ["[Total non-current liabilities — printed without a label]", None, 3312948976, 2963705984],
    ["Current Liabilities"],
    ["Borrowings", 19, 20007773, 450485093], ["Lease liabilities with purchase option", 19, 108125497, 91697176],
    ["Lease liabilities without purchase option", 19, 303795617, 302656699], ["Other payables", 20, 624810080, 674742509],
    ["Income tax payable", 12, 31607, 19326], ["Other current liabilities", 21, 85267840, 79028839],
    ["Liabilities from unused flight documents", 22, 699001436, 715783464],
    ["[Total current liabilities — printed without a label]", None, 1841039850, 2314413106],
    ["Total liabilities", None, 5153988826, 5278119090],
    ["Total equity and liabilities", None, 5739337414, 5892042625],
]
IS = [  # label, note, 2024, 2023 (the revenue total is printed without a label and is left so)
    ["Revenue"],
    ["Passenger", 24, 3820622937, 3851624072], ["Maintenance", 24, 236766190, 163732236],
    ["Cargo and mail", 24, 162730935, 173077981], ["Gains and losses in associates", 7, -2490020, "-"],
    ["Other operating income", "24 and 25", 24803978, 26383921],
    [None, None, 4242434020, 4214818210],
    ["Aircraft fuel", 26, -1045805428, -1114753942], ["Traffic operating costs", 26, -870145352, -906509030],
    ["Aircraft maintenance costs", 26, -60797940, -56128515], ["Cost of materials consumed", 26, -171630953, -127713853],
    ["Comercial, communication and marketing costs", 26, -217366433, -211896653],
    ["Employee costs", 27, -817129659, -722620603], ["Impairment losses in receivables", 28, 10588508, -3911967],
    ["Impairment losses in inventories", 28, -1232465, -3041248], ["Provisions", 28, -32276746, -35452534],
    ["Other operating expenses", 29, -161310299, -161196920], ["Restructuring", 30, 934997, 1426055],
    ["Other non recurrent items", 31, -69191977, -40525393],
    ["Depreciation, amortisation and impairment losses", 32, -492676021, -485765081],
    ["Operating income/(loss)", None, 314394252, 346728526],
    ["Interests and similar income", 33, 79892564, 64629424], ["Interests and similar expenses", 33, -249758672, -254541523],
    ["Net currency exchange", 33, -48948504, 29649279],
    ["Net income/(loss) before income tax", None, 95579640, 186465706],
    ["Income tax for the year", 34, -41857660, -9205163],
    ["Net income/(loss) for the year", None, 53721980, 177260543],
    ["Net income/(loss) attributable to owners of TAP S.A.", None, 53721980, 177260543],
    ["Net income/(loss) attributable to non-controlling interests", None, "-", "-"],
]
CF = [  # label, note, 2024, 2023 (direct method; the text of the page has no heading above the investment block)
    ["Operating activities:"],
    ["Receipts from customers", None, 4591003754, 4581408978], ["Payments to suppliers", None, -3070786181, -2973838142],
    ["Payments to employees", None, -844462744, -587375048],
    ["Payments of low value and short-term leases", None, -15719526, -6023147],
    ["Cash generated from operations", None, 660035303, 1014172641],
    ["Income tax (payment)/receipt", None, -4222046, -686882],
    ["Other receipts/payments relating to operating activities", None, -6477609, -8235939],
    ["Cash flow from operating activities (1)", None, 649335648, 1005249820],
    ["Receipts from:"],
    ["Financial investments"],  # printed with no amounts
    ["Other financial assets", "4, 8, 10 and 18", 3948717, 6101065], ["Tangible fixed assets", 4, 15737076, 27415188],
    ["Investment grants", None, "-", "-"],
    ["Loans granted", None, 1014647100, 984362222], ["Interests and similar income", None, 64320119, 61337035],
    [None, None, 1098653012, 1079215510],
    ["Payments relating to:"],
    ["Financial investments", "7 e 2.3", -3303319, "-"], ["Other financial assets", "4, 8, 10 and 18", -53379583, -77765172],
    ["Tangible fixed assets", 4, -351416679, -196667531], ["Intangible assets", None, -15825327, -5638559],
    ["Loans granted", None, -1063049438, -1023857100],
    [None, None, -1486974346, -1303928362],
    ["Cash flow from investment activities (2)", None, -388321334, -224712852],
    ["Financing activities:"],
    ["Receipts from:"],
    ["Borrowings", 19, 400000000, 2763456], ["Capital increases", 15, 343000000, "-"],
    [None, None, 743000000, 2763456],
    ["Payments relating to:"],
    ["Borrowings", 19, -516757627, -264796790], ["Lease liabilities with purchase option", 19, -138004580, -77777963],
    ["Lease liabilities without purchase option", 19, -430946569, -469864057],
    ["Interests and similar costs", 19, -37363897, -86175613],
    [None, None, -1123072673, -898614423],
    ["Cash flow from financing activities (3)", None, -380072673, -895850967],
    ["Net increase (decrease) in cash and cash equivalents (1)+(2)+(3)", None, -119058359, -115313999],
    ["Effects of currency exchange differences", None, -18686809, -11375354],
    ["Cash and cash equivalents at the beginning of the year", 14, 789387698, 916077051],
    ["Cash and cash equivalents at the end of the year", 14, 651642530, 789387698],
]
NOTE10 = [  # label, 2024 current, 2024 non-current, 2023 current, 2023 non-current
    ["Customers", 305984780, "-", 352648295, "-"],
    ["Security deposits of lease contracts", 4826681, 41685545, 2713652, 35981107],
    ["Recoverable maintenance reserves", 67768247, 107078559, 23307613, 67040574],
    ["Swaps jet fuel (Note 23)", 4808692, "-", "-", "-"], ["Advances to suppliers", 22077780, "-", 18701192, "-"],
    ["Accrued income", 99439133, "-", 38735235, "-"], ["Other debtors", 1561829978, 4683212, 1844332616, 19839395],
    [None, 2066735291, 153447316, 2280438603, 122861076],
    ["Receivables impairment losses", -1189973012, -1921388, -1152064266, -1921388],
    [None, 876762279, 151525928, 1128374337, 120939688],
]
NOTE20 = [  # label, 2024, 2023 (the 2024 report prints one column a year: every amount is current)
    ["Accrued expenses", 278791737, 352160074], ["Suppliers", 203193642, 185957007],
    ["Jet fuel swaps (Note 23)", 1984535, 639596], ["Advances from customers", 410838, 522454],
    ["Other", 140429328, 135463378],
    [None, 624810080, 674742509],
]

wb = Workbook()
src = wb.active
src.title = "Source"
src.append(["Transportes Aéreos Portugueses, S.A. (TAP Air Portugal) — published consolidated accounts FY2024"])
src.append(["Copied as printed from 'Consolidated Financial Statements as of 31 December 2024' (Consolidated Annual "
            "Report 2024, English translation; the Portuguese original prevails), PDF page numbers: statement of "
            "financial position p.54, income statement p.55, cash flow statement p.58, note 10 p.123, note 20 p.145. "
            "Amounts in euros. The 2024 figures are as first published, before the restatement printed in the 2025 "
            "Integrated Report."])
src.append(["Source: " + URL])
src.append(["Obtained on 10 November 2026. SHA-256 of the PDF: " + SHA256 + ". Subtotals printed without a label are "
            "labelled in square brackets; nothing else is added. Real, published figures, used to test the agent on "
            "real accounts."])
src.column_dimensions["A"].width = 120
for title, heading, rows in (("Financial position", "Consolidated statement of financial position", BS),
                             ("Income statement", "Consolidated income statement", IS),
                             ("Cash flow", "Consolidated cash flow statement", CF)):
    ws = wb.create_sheet(title)
    ws.append([heading])
    ws.append([])
    ws.append([UNIT, "Notes", 2024, 2023])
    for r in rows:
        ws.append(r)
ws = wb.create_sheet("Note 10 Other receivables")
ws.append(["10 Other accounts receivable"])
ws.append([UNIT, 2024, None, 2023])
ws.append([None, "Current", "Non-current", "Current", "Non-current"])
for r in NOTE10:
    ws.append(r)
ws = wb.create_sheet("Note 20 Other payables")
ws.append(["20 Other accounts payable"])
ws.append([UNIT, 2024, 2023])
for r in NOTE20:
    ws.append(r)
out = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "data/TAP_2024_published.xlsx")
wb.save(out)
print("saved", out)
