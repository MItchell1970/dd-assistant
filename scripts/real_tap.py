"""TAP — Transportes Aéreos Portugueses, S.A. — consolidated statements FY2025/FY2024 copied as printed in the 2025
Integrated Report (English translation; the Portuguese original prevails): statement of financial position p.152,
income statement p.153, cash flow statement p.156, notes 10 (p.190) and 20 (p.208). Amounts in euros, as printed.

Subtotals the report prints without a label are labelled here in square brackets, so a reader can tell them from
the printed labels; nothing else is added. The 2024 balance sheet is restated, as printed.
"""
import sys
from pathlib import Path

from openpyxl import Workbook

URL = ("https://publish-p133109-e1368204.adobeaemcloud.com/content/dam/tap-institucional/media/pdfs/investidores/"
       "info-financeira/2026/en/EN-Relatorio-integrado-TAP.2025-V5.pdf")
UNIT = "Amounts stated in euros"
BS = [  # label, note, 2025, 2024 restated
    ["ASSETS"],
    ["Non-current assets"],
    ["Tangible fixed assets", 4, 3339265575, 3153399157], ["Investment properties", 5, 1198000, 1198000],
    ["Intagible assets", 6, 28302209, 31088687], ["Goodwill", 7, 183250285, 180135637],
    ["Other financial assets", 8, 680947, 680937], ["Other non current assets", 13, 74227382, 57288668],
    ["Deferred tax assets", 9, 398887447, 471047253], ["Other receivables", 10, 138788463, 151525928],
    ["[Total non-current assets — printed without a label]", None, 4164600308, 4046364267],
    ["Current Assets"],
    ["Inventories", 11, 122193880, 97524652], ["Other receivables", 10, 660540024, 876762279],
    ["Income tax receivable", 12, 18170020, 13027371], ["Other financial assets", 8, 13178431, "-"],
    ["Other current assets", 13, 130127394, 111584604], ["Cash and cash equivalents", 14, 765329360, 651642530],
    ["[Total current assets — printed without a label]", None, 1709539109, 1750541436],
    ["Non-current assets held for sale", 7, 28869179, "-"],
    ["Total Assets", None, 5903008596, 5796905703],
    ["EQUITY AND LIABILITIES"],
    ["Equity"],
    ["Share Capital", 15, 656600000, 313600000], ["Supplementary capital contributions", 15, "-", 343000000],
    ["Legal reserves", 16, 8300000, 8300000], ["Hedge reserves", 16, -3678937, -1343925],
    ["Other reserves", 16, 37503592, -108853600], ["Other variations in equity", 16, -24990000, "-"],
    ["Retained earnings", 16, 34717558, -23075867], ["Net income/(loss) for the year", None, 4149874, 53721980],
    ["Total equity of the Group", None, 712602087, 585348588], ["Non-controlling interests", 16, 4404334, "-"],
    ["Total equity", None, 717006421, 585348588],
    ["Non-current liabilities"],
    ["Deferred tax liabilities", 9, 147202140, 84240222], ["Post-employment benefits obligations", 17, 173153669, 186458338],
    ["Provisions", 18, 414902016, 472792114], ["Restructuring provision", 18, 182792, 182792],
    ["Borrowings", 19, 702554408, 513045714], ["Lease liabilities with purchase option", 19, 742539672, 760801016],
    ["Lease liabilities without purchase option", 19, 1033575276, 1295428780], ["Other payables", 20, 4683006, 2008837],
    ["[Total non-current liabilities — printed without a label]", None, 3218792979, 3314957813],
    ["Current Liabilities"],
    ["Borrowings", 19, 19990796, 20007773], ["Lease liabilities with purchase option", 19, 117102021, 108125497],
    ["Lease liabilities without purchase option", 19, 265084936, 303795617], ["Other payables", 20, 727646558, 680369532],
    ["Income tax payable", 12, 3873215, 31607], ["Other current liabilities", 21, 103489177, 85267840],
    ["Liabilities from unused flight documents", 22, 710602333, 699001436],
    ["[Total current liabilities — printed without a label]", None, 1947789036, 1896599302],
    ["Liabilites related with non-current assets held for sale", 7, 19420160, "-"],
    ["Total liabilities", None, 5186002175, 5211557115],
    ["Total equity and liabilities", None, 5903008596, 5796905703],
]
IS = [  # label, note, 2025, 2024 (the revenue total is printed without a label and is left so)
    ["Revenue"],
    ["Passenger", 24, 3849317194, 3820622937], ["Maintenance", 24, 261544603, 236766190],
    ["Cargo and mail", 24, 160087049, 162730935], ["Gains and losses in associates", 7, "-", -2490020],
    ["Other operating income", "24 and 25", 42542172, 24803978],
    [None, None, 4313491018, 4242434020],
    ["Aircraft fuel", 26, -989776481, -1045805428], ["Traffic operating costs", 26, -884442310, -870145352],
    ["Aircraft maintenance costs", 26, -76927011, -60797940], ["Cost of materials consumed", 26, -217428121, -171630953],
    ["Comercial, communication and marketing costs", 26, -216391690, -217366433],
    ["Employee costs", 27, -972120680, -817129659], ["Impairment losses in receivables", 28, -2561816, 10588508],
    ["Impairment losses in inventories", 28, 355135, -1232465], ["Provisions", 28, 500105, -32276746],
    ["Other operating expenses", 29, -211766018, -161310299], ["Restructuring", 30, -307170, 934997],
    ["Other non recurrent items", 31, -16814330, -69191977],
    ["Depreciation, amortisation and impairment losses", 32, -499503187, -492676021],
    ["Operating income/(loss)", None, 226307444, 314394252],
    ["Interests and similar income", 33, 70611116, 79892564], ["Interests and similar expenses", 33, -195726548, -249758672],
    ["Net currency exchange", 33, -32997528, -48948504],
    ["Net income/(loss) before income tax", None, 68194484, 95579640],
    ["Income tax for the year", 34, -66079412, -41857660],
    ["Net income/(loss) for the year", None, 2115072, 53721980],
    ["Net income/(loss) attributable to owners of TAP S.A.", None, 4149874, 53721980],
    ["Net income/(loss) attributable to non-controlling interests", 16, -2034802, "-"],
]
CF = [  # label, note, 2025, 2024 (direct method)
    ["OPERATING ACTIVITIES"],
    ["Receipts from customers", None, 4612061627, 4591003754], ["Payments to suppliers", None, -3139691756, -3070786181],
    ["Payments to employees", None, -892989992, -844462744],
    ["Payments of low value and short-term leases", None, -23369879, -15719526],
    ["Cash generated from operations", None, 556010000, 660035303],
    ["Income tax (payment)/receipt", None, 8795095, -4222046],
    ["Other receipts/payments relating to operating activities", None, 39259849, -6477609],
    ["Cash flow from operating activities (1)", None, 604064944, 649335648],
    ["INVESTMENT ACTIVITIES"],
    ["Receipts from:"],
    ["Other financial assets", "4, 8, 10 and 18", 11356078, 3948717], ["Tangible fixed assets", 4, 26256656, 15737076],
    ["Loans granted", None, 111493344, 1014647100], ["Interests and similar income", None, 31340367, 64320119],
    [None, None, 180446445, 1098653012],
    ["Payments relating to:"],
    ["Financial investments", "7 e 2.4", -5652708, -3303319], ["Other financial assets", "4, 8, 10 and 18", -69958454, -53379583],
    ["Tangible fixed assets", 4, -434351669, -351416679], ["Intangible assets", None, -4183628, -15825327],
    ["Loans granted", None, -116202991, -1063049438],
    [None, None, -630349450, -1486974346],
    ["Cash flow from investment activities (2)", None, -449903005, -388321334],
    ["FINANCING ACTIVITIES"],
    ["Receipts from:"],
    ["Borrowings", 19, 200000000, 400000000], ["Capital increases", 15, 343000000, 343000000],
    [None, None, 543000000, 743000000],
    ["Payments relating to:"],
    ["Borrowings", 19, -15271922, -516757627], ["Lease liabilities with purchase option", 19, -152176161, -138004580],
    ["Lease liabilities without purchase option", 19, -311641797, -430946569],
    ["Interests and similar costs", 19, -29438767, -37363897],
    [None, None, -508528647, -1123072673],
    ["Cash flow from financing activities (3)", None, 34471353, -380072673],
    ["Net increase (decrease) in cash and cash equivalents (1)+(2)+(3)", None, 188633292, -119058359],
    ["Effects of currency exchange differences", None, -58859245, -18686809],
    ["Cash and cash equivalents at the beginning of the year", 14, 651642530, 789387698],
    ["Non-current assets held for sale", 7, -16087217, "-"],
    ["Cash and cash equivalents at the end of the year", 14, 765329360, 651642530],
]
NOTE10 = [  # label, 2025 current, 2025 non-current, 2024 current, 2024 non-current
    ["Customers", 372247352, "-", 305984780, "-"],
    ["Security deposits of lease contracts", 4430574, 37240716, 4826681, 41685545],
    ["Recoverable maintenance reserves", 82456337, 94202510, 67768247, 107078559],
    ["Swaps jet fuel (Note 23)", "-", "-", 4808692, "-"], ["Advances to suppliers", 13621170, "-", 22077780, "-"],
    ["Accrued income", 133816039, "-", 99439133, "-"], ["Other debtors", 1270179990, 12225687, 1561829978, 4683212],
    [None, 1876751462, 143668913, 2066735291, 153447316],
    ["Receivables impairment losses", -1216211438, -4880450, -1189973012, -1921388],
    [None, 660540024, 138788463, 876762279, 151525928],
]
NOTE20 = [  # label, 2025 current, 2025 non-current, 2024 current, 2024 non-current (2024 restated)
    ["Accrued expenses", 351749914, 4683006, 334351189, 2008837], ["Suppliers", 200436788, "-", 203193642, "-"],
    ["Jet fuel swaps (Note 23)", 5074396, "-", 1984535, "-"], ["Advances from customers", 499345, "-", 410838, "-"],
    ["Other", 169886115, "-", 140429328, "-"],
    [None, 727646558, 4683006, 680369532, 2008837],
]

wb = Workbook()
src = wb.active
src.title = "Source"
src.append(["Transportes Aéreos Portugueses, S.A. (TAP Air Portugal) — published consolidated accounts FY2025"])
src.append(["Copied as printed from the 2025 Integrated Report (English translation; the Portuguese original prevails): "
            "statement of financial position p.152, income statement p.153, cash flow statement p.156, note 10 p.190, "
            "note 20 p.208. Amounts in euros. The 2024 balance sheet is restated, as printed."])
src.append(["Source: " + URL])
src.append(["Obtained on 4 November 2026. Subtotals printed without a label are labelled in square brackets; nothing "
            "else is added. Real, published figures, used to test the agent on real accounts."])
src.column_dimensions["A"].width = 120
for title, heading, rows in (("Financial position", "Consolidated statement of financial position", BS),
                             ("Income statement", "Consolidated income statement", IS),
                             ("Cash flow", "Consolidated cash flow statement", CF)):
    ws = wb.create_sheet(title)
    ws.append([heading])
    ws.append([])
    ws.append([UNIT, "Notes", 2025, 2024])
    for r in rows:
        ws.append(r)
for title, heading, rows in (("Note 10 Other receivables", "10. Other accounts receivable", NOTE10),
                             ("Note 20 Other payables", "20. Other accounts payable", NOTE20)):
    ws = wb.create_sheet(title)
    ws.append([heading])
    ws.append([UNIT, 2025, None, 2024])
    ws.append([None, "Current", "Non-current", "Current", "Non-current"])
    for r in rows:
        ws.append(r)
out = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "data/TAP_2025_published.xlsx")
wb.save(out)
print("saved", out)
