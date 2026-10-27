"""Sector context: where the company operates changes what is normal and what to ask.

For each sector:
  - calibration: the few rule thresholds that differ from the general ones, each with the reason
    (shown next to the finding, never applied silently). 'General' keeps the template's thresholds;
    the parity tests run on it;
  - benchmarks: margins, working capital, capex and leverage of European listed companies in the
    closest Damodaran industry (scripts/sector_benchmarks.py), for orientation only;
  - lens: the questions a sector specialist adds to the request list;
  - keywords used to suggest the sector from the data room (the reviewer confirms it).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

# ---------------------------------------------------------------- benchmarks (scripts/sector_benchmarks.py)
BENCHMARK_SOURCE = "Damodaran Online (NYU Stern), European listed companies, January 2026"
BENCHMARKS = {
    "general": {"industry": "Total Market (without financials)", "firms": 5757, "gross_margin": 0.3467, "ebitda_margin": 0.157, "receivables_sales": 0.1427, "inventory_sales": 0.1239, "payables_sales": 0.1554, "nwc_sales": 0.0588, "capex_da": 1.201, "debt_ebitda": 3.1279},
    "distribution": {"industry": "Retail (Distributors)", "firms": 117, "gross_margin": 0.3068, "ebitda_margin": 0.1019, "receivables_sales": 0.1528, "inventory_sales": 0.1441, "payables_sales": 0.1297, "nwc_sales": 0.14, "capex_da": 1.2687, "debt_ebitda": 4.8275},
    "manufacturing": {"industry": "Machinery", "firms": 210, "gross_margin": 0.4468, "ebitda_margin": 0.1297, "receivables_sales": 0.1841, "inventory_sales": 0.1777, "payables_sales": 0.1018, "nwc_sales": 0.1737, "capex_da": 0.7913, "debt_ebitda": 1.8716},
    "materials": {"industry": "Packaging & Container", "firms": 42, "gross_margin": 0.2438, "ebitda_margin": 0.1159, "receivables_sales": 0.1541, "inventory_sales": 0.1632, "payables_sales": 0.1469, "nwc_sales": 0.1198, "capex_da": 1.004, "debt_ebitda": 4.4185},
    "automotive": {"industry": "Retail (Automotive)", "firms": 22, "gross_margin": 0.161, "ebitda_margin": 0.0344, "receivables_sales": 0.0521, "inventory_sales": 0.1473, "payables_sales": 0.0918, "nwc_sales": 0.0828, "capex_da": 0.9277, "debt_ebitda": 4.0158},
    "consumer_retail": {"industry": "Retail (General)", "firms": 31, "gross_margin": 0.2487, "ebitda_margin": 0.0552, "receivables_sales": 0.0841, "inventory_sales": 0.0955, "payables_sales": 0.143, "nwc_sales": 0.0114, "capex_da": 0.6627, "debt_ebitda": 7.0586},
    "food": {"industry": "Food Processing", "firms": 173, "gross_margin": 0.3294, "ebitda_margin": 0.1143, "receivables_sales": 0.1003, "inventory_sales": 0.1609, "payables_sales": 0.1474, "nwc_sales": 0.0956, "capex_da": 1.3901, "debt_ebitda": 3.6942},
    "hardware": {"industry": "Computers/Peripherals", "firms": 38, "gross_margin": 0.4396, "ebitda_margin": 0.1277, "receivables_sales": 0.1868, "inventory_sales": 0.1587, "payables_sales": 0.1296, "nwc_sales": 0.1669, "capex_da": 0.871, "debt_ebitda": 1.5454},
    "software": {"industry": "Software (System & Application)", "firms": 290, "gross_margin": 0.6521, "ebitda_margin": 0.1723, "receivables_sales": 0.1794, "inventory_sales": 0.006, "payables_sales": 0.0774, "nwc_sales": 0.1381, "capex_da": 1.4132, "debt_ebitda": 2.0581},
    "services": {"industry": "Business & Consumer Services", "firms": 176, "gross_margin": 0.3236, "ebitda_margin": 0.1033, "receivables_sales": 0.1804, "inventory_sales": 0.0088, "payables_sales": 0.1094, "nwc_sales": 0.0572, "capex_da": 0.6579, "debt_ebitda": 3.606},
    "construction": {"industry": "Engineering/Construction", "firms": 160, "gross_margin": 0.3525, "ebitda_margin": 0.0727, "receivables_sales": 0.2551, "inventory_sales": 0.0494, "payables_sales": 0.1915, "nwc_sales": -0.0176, "capex_da": 0.8628, "debt_ebitda": 4.5338},
    "healthcare": {"industry": "Healthcare Products", "firms": 163, "gross_margin": 0.5606, "ebitda_margin": 0.182, "receivables_sales": 0.1843, "inventory_sales": 0.1788, "payables_sales": 0.0925, "nwc_sales": 0.2499, "capex_da": 0.8626, "debt_ebitda": 3.1071},
    "hospitality": {"industry": "Hotel/Gaming", "firms": 103, "gross_margin": 0.4029, "ebitda_margin": 0.1684, "receivables_sales": 0.078, "inventory_sales": 0.0063, "payables_sales": 0.1379, "nwc_sales": -0.1589, "capex_da": 0.6872, "debt_ebitda": 3.8359},
    "energy": {"industry": "Utility (General)", "firms": 18, "gross_margin": 0.3167, "ebitda_margin": 0.1587, "receivables_sales": 0.218, "inventory_sales": 0.0304, "payables_sales": 0.1661, "nwc_sales": -0.0187, "capex_da": 1.9176, "debt_ebitda": 4.2971},
    "transport": {"industry": "Transportation", "firms": 56, "gross_margin": 0.2117, "ebitda_margin": 0.0839, "receivables_sales": 0.1508, "inventory_sales": 0.0226, "payables_sales": 0.1334, "nwc_sales": -0.0067, "capex_da": 0.5196, "debt_ebitda": 7.308},
}
BENCHMARK_LABELS = {
    "gross_margin": ("Gross margin", "pct"), "ebitda_margin": ("EBITDA margin", "pct"),
    "receivables_sales": ("Trade receivables / revenue", "pct"), "inventory_sales": ("Inventories / revenue", "pct"),
    "payables_sales": ("Trade payables / revenue", "pct"), "nwc_sales": ("Net working capital / revenue", "pct"),
    "capex_da": ("Capex / D&A", "x"), "debt_ebitda": ("Gross debt / EBITDA", "x"),
}


@dataclass(frozen=True)
class LensItem:
    area: str
    question: str
    request: str


@dataclass(frozen=True)
class Sector:
    key: str
    name: str
    keywords: tuple[str, ...] = ()
    calibration: dict[str, tuple[float, str]] = field(default_factory=dict)   # rule ID -> (threshold, reason)
    lens: tuple[LensItem, ...] = ()

    @property
    def benchmarks(self) -> dict:
        return BENCHMARKS[self.key]


def _s(key, name, keywords, calibration=None, lens=()):
    return Sector(key, name, tuple(keywords), calibration or {}, tuple(LensItem(*x) for x in lens))


SECTORS: list[Sector] = [
    _s("general", "General / not specified", []),
    _s("distribution", "Industrial distribution & wholesale",
       ["distribuicao", "distribuidor", "distribuidora", "grossista", "wholesale", "wholesaler", "distribution",
        "distributor", "revenda"],
       {"R11": (0.50, "working capital is usually funded with short-term revolving and confirming lines renewed "
                      "every year")},
       [("Supplier rebates", "How much of gross margin comes from supplier rebates and volume bonuses, how are they "
                             "accrued and are any targets at risk?",
         "Rebate agreements and rebate accruals by supplier, with the cash received"),
        ("Supply agreements", "Are the main distribution agreements exclusive, when do they expire and do they contain "
                              "change-of-control clauses?", "Distribution and agency agreements with the top 10 suppliers"),
        ("Inventory", "What share of stock has not moved in 12 months, and how is it provided for?",
         "Inventory ageing by SKU; slow-moving provision policy"),
        ("Credit risk", "Is the receivables book credit-insured, and what were write-offs and overdue balances over "
                        "the last 24 months?", "Credit insurance policy; AR ageing and write-off history"),
        ("Pricing", "How quickly are purchase price increases passed on to customers?",
         "Price lists and gross margin bridge by product family")]),
    _s("manufacturing", "Industrial manufacturing",
       ["fabrica", "fabricas", "fabril", "fabrico", "manufacturing", "manufacturer", "factory", "factories",
        "maquinas", "machinery", "metalomecanica"],
       {},
       [("Capex", "What are capacity utilisation and the split of capex between maintenance and growth?",
         "Capex plan by plant (maintenance vs growth); capacity utilisation by line"),
        ("Input costs", "How are raw-material and energy costs hedged or passed through to customers?",
         "Purchase contracts, hedging positions and price pass-through clauses"),
        ("Order book", "How much of next year's revenue is covered by the order book?",
         "Order book and its conversion history"),
        ("Warranties", "What were warranty claims and returns, and how is the warranty provision estimated?",
         "Warranty provision roll-forward; claims history"),
        ("Inventory valuation", "How are overheads absorbed into inventory, and were standard costs revised in the "
                                "period?", "Inventory costing policy; standard cost variances")]),
    _s("materials", "Materials & packaging",
       ["cortica", "corticeira", "cork", "embalagem", "embalagens", "packaging", "papel", "pulp", "quimica",
        "chemical", "chemicals", "ceramica", "vidro", "glass", "materiais"],
       {},
       [("Raw materials", "How secure is the supply of the main raw material, and how are price changes passed on?",
         "Purchase contracts and raw-material price history"),
        ("Inventory", "Long production cycles: how is raw-material and work-in-progress stock valued, and how much "
                      "is ageing or obsolete?", "Inventory by stage and age; valuation and provisioning policy"),
        ("Energy", "What is the energy intensity of production and how is energy cost hedged?",
         "Energy contracts and hedging; energy cost as % of revenue"),
        ("Capex", "What maintenance capex is needed to keep plants competitive?",
         "Capex plan (maintenance vs growth) and asset condition reports"),
        ("Environment", "Are there environmental permits, remediation obligations or emission costs?",
         "Environmental licences and audits; CO2 allowance position")]),
    _s("automotive", "Automotive distribution & retail",
       ["automovel", "automoveis", "veiculos", "concessionario", "concessionarios", "toyota", "lexus",
        "automotive", "vehicle", "vehicles", "dealer", "dealers", "dealership", "oem"],
       {"R11": (0.60, "vehicle stock is financed with short-term floorplan and stock-financing lines")},
       [("OEM agreement", "What are the term, renewal and change-of-control provisions of the distribution agreement "
                          "with the manufacturer?", "Distribution / importer agreement with the OEM"),
        ("OEM incentives", "How much income comes from OEM bonuses, marketing support and target-based incentives, "
                           "and where is it recorded (cost of sales or other income)?",
         "Schedule of OEM bonuses and incentives by year, with their accounting"),
        ("Stock financing", "Is vehicle stock financed through floorplan or OEM credit lines, and are these lines "
                            "included in reported debt?", "Floorplan and stock-financing agreements; month-end balances"),
        ("Used vehicles", "How are used and demonstration vehicles valued, and what write-downs were booked?",
         "Used-vehicle stock ageing and valuation policy"),
        ("Buy-back", "Are there buy-back or residual value commitments to rental or fleet customers?",
         "Schedule of buy-back and residual value commitments"),
        ("Mix", "What share of gross profit comes from after-sales (parts and service)?",
         "Gross profit by business line (new, used, after-sales)")]),
    _s("consumer_retail", "Consumer & retail",
       ["retalho", "lojas", "loja", "retail", "retailer", "store", "stores", "consumidor", "consumer",
        "e commerce", "ecommerce", "supermercado", "supermercados", "moda", "fashion"],
       {"R08": (5, "sales are mostly cash and card, so any increase in DSO is unusual"),
        "R11": (0.50, "seasonal stock is usually funded with short-term lines")},
       [("Like-for-like", "What is like-for-like growth, excluding store openings and closures?",
         "Revenue by store with opening dates; like-for-like bridge"),
        ("Store economics", "How many stores are loss-making at store level, and what closures are planned?",
         "Store-level P&L for the last 24 months"),
        ("Leases", "Is EBITDA presented before or after IFRS 16, and what are the lease terms and break options?",
         "Lease schedule (rent, term, break options); IFRS 16 reconciliation"),
        ("Stock", "What are shrinkage and markdown levels, and how is seasonal stock provided for?",
         "Shrinkage and markdown history; stock ageing by season"),
        ("Customer liabilities", "Are there gift card, loyalty or returns liabilities, and how are they measured?",
         "Gift card and loyalty liability roll-forward")]),
    _s("food", "Food & beverage",
       ["alimentar", "alimentos", "bebidas", "food", "foods", "beverage", "beverages", "vinho", "vinhos", "wine",
        "conservas", "lacticinios", "agroalimentar"],
       {},
       [("Commodities", "How are commodity price movements hedged or passed on to customers?",
         "Commodity purchase contracts and hedging positions"),
        ("Trade spend", "How are promotions, listing fees and retailer rebates accrued, and are they netted against "
                        "revenue?", "Trade spend accruals by customer and their settlement"),
        ("Retailer concentration", "What are the terms of the contracts with the main retailers?",
         "Contracts with the top 5 customers"),
        ("Seasonality", "What is the seasonal working capital peak, and how is it funded?",
         "Monthly working capital and debt for 24 months"),
        ("Food safety", "Have there been recalls, quality claims or regulatory inspections?",
         "Recall and claims log; certifications and inspection reports")]),
    _s("hardware", "Technology hardware & electronics",
       ["hardware", "electronics", "eletronica", "eletronicos", "devices", "dispositivos", "semiconductores",
        "semiconductors", "computers", "iphone", "ipad", "mac", "wearables", "smartphones", "componentes"],
       {},
       [("Supply chain", "How concentrated is the supply of key components and contract manufacturing?",
         "Top suppliers by spend; supply agreements and single-source components"),
        ("Channel inventory", "How does sell-in compare with sell-out, and what stock do distributors hold?",
         "Sell-in vs sell-out data; channel inventory reports"),
        ("Product cycle", "How much revenue comes from products launched in the last two years, and what is the "
                          "obsolescence risk on stock?", "Revenue by product generation; inventory ageing"),
        ("Warranties", "How is the warranty provision estimated, and how do claims compare with it?",
         "Warranty provision roll-forward and claims"),
        ("Bundled services", "How is revenue from bundled services and software allocated and deferred?",
         "Revenue recognition policy; deferred revenue roll-forward")]),
    _s("software", "Software & SaaS",
       ["software", "saas", "subscription", "subscriptions", "subscricao", "subscricoes", "licencas", "licenses",
        "licences", "cloud", "arr"],
       {"R01": (0.10, "recurring-revenue businesses are valued on the stickiness of their largest accounts"),
        "R08": (10, "subscriptions are billed regularly, so collection periods should be stable"),
        "R10": (0.80, "upfront billing normally makes cash conversion higher than in other sectors")},
       [("ARR", "What is the ARR bridge (new, expansion, contraction, churn) for the last 24 months?",
         "Monthly ARR/MRR by customer"),
        ("Retention", "What are net revenue retention and logo churn by cohort?", "Cohort analysis of revenue retention"),
        ("Capitalised development", "How much development cost is capitalised, and on what criteria?",
         "Capitalised development roll-forward and policy"),
        ("Deferred revenue", "How is deferred revenue recognised, and are multi-year prepayments included?",
         "Deferred revenue roll-forward and billing terms"),
        ("Acquisition cost", "What are customer acquisition cost and payback by channel?",
         "Sales and marketing spend and new ARR by channel")]),
    _s("services", "Business & IT services",
       ["consultoria", "consulting", "outsourcing", "nearshore", "consultores", "consultants", "staffing",
        "it services", "servicos de ti", "professional services", "servicos profissionais"],
       {},
       [("Utilisation", "What are utilisation and billable headcount, and how have rates evolved?",
         "Monthly utilisation, headcount and average day rates"),
        ("Contracts", "What share of revenue is time-and-materials vs fixed-price, and are fixed-price projects "
                      "profitable?", "Revenue by contract type; project margins"),
        ("Unbilled work", "How much accrued income (unbilled work) is outstanding, and how old is it?",
         "Accrued income ageing and post year-end billing"),
        ("People", "How many contractors work like employees, and what is staff attrition?",
         "Headcount by contract type; attrition"),
        ("Clients", "Are revenues secured by framework agreements, and when do they expire?",
         "Framework agreements with the top 10 clients")]),
    _s("construction", "Construction & engineering",
       ["construcao", "obras", "empreitada", "empreitadas", "engenharia", "construction", "contractor",
        "infraestruturas", "infrastructure", "building"],
       {"R07": (20, "milestone billing makes receivables lumpy from year to year"),
        "R08": (30, "milestone billing makes receivables lumpy from year to year")},
       [("Contract margins", "How do current margin estimates on major contracts compare with the margins at tender "
                             "(margin fade)?", "Contract schedule: tender margin, current margin, % complete"),
        ("Contract assets", "How much revenue is recognised but not yet billed, and are there claims included?",
         "Contract assets and claims by contract"),
        ("Onerous contracts", "Are loss-making contracts fully provided for?", "Loss provisions by contract"),
        ("Backlog", "What is the backlog and how much of next year's revenue does it cover?",
         "Backlog by contract and expected execution"),
        ("Guarantees", "What performance bonds, retentions and advance payments are outstanding?",
         "Schedule of bank guarantees, retentions and customer advances")]),
    _s("healthcare", "Healthcare & life sciences",
       ["saude", "health", "healthcare", "farmaceutica", "pharma", "pharmaceutical", "hospital", "clinica",
        "clinicas", "medical", "medicamentos"],
       {},
       [("Reimbursement", "How exposed is revenue to regulated prices and reimbursement changes?",
         "Revenue by payer and price regime"),
        ("Licences", "Are all licences and regulatory approvals current, and are any under review?",
         "Licences, approvals and inspection reports"),
        ("Public payers", "What are payment delays from public payers, and are overdue balances provided for?",
         "AR ageing by payer"),
        ("Liability", "Are there product liability or malpractice claims?", "Claims register and insurance cover"),
        ("R&D", "How much R&D is capitalised, and on what criteria?", "R&D spend and capitalisation policy")]),
    _s("hospitality", "Hospitality & leisure",
       ["hotel", "hoteis", "hotelaria", "turismo", "tourism", "restaurante", "restaurantes", "restaurant",
        "alojamento", "leisure", "lazer"],
       {"R08": (5, "guests pay at or before the stay, so any increase in DSO is unusual")},
       [("Trading KPIs", "How have occupancy, ADR and RevPAR evolved by property?",
         "Monthly occupancy, ADR and RevPAR by property"),
        ("Seasonality", "What is the cash low point of the year, and how is it funded?", "Monthly cash and debt"),
        ("Leases", "Which properties are leased, on what terms, and is EBITDA before or after IFRS 16?",
         "Lease schedule; IFRS 16 reconciliation"),
        ("Maintenance capex", "What FF&E reserve is set aside, and has maintenance been deferred?",
         "Capex history and FF&E plan by property"),
        ("Staff", "How dependent is the business on seasonal staff, and what are staff cost trends?",
         "Headcount and staff costs by month")]),
    _s("energy", "Energy & utilities",
       ["energia", "energy", "eletricidade", "electricity", "renovaveis", "renewable", "renewables", "solar",
        "eolica", "wind", "utilities", "utility"],
       {},
       [("Tariffs", "What share of revenue is regulated or under long-term PPAs, and when do they expire?",
         "PPAs and regulatory decisions"),
        ("Merchant exposure", "How exposed is the company to market prices, and how is it hedged?",
         "Hedging book and merchant revenue"),
        ("Decommissioning", "Are decommissioning and environmental obligations fully provided for?",
         "Decommissioning provision roll-forward"),
        ("Project finance", "Is cash ring-fenced in project companies, and what are the distribution conditions?",
         "Project finance agreements; restricted cash"),
        ("Grants", "Are any grants or subsidies repayable or conditional?", "Grant agreements")]),
    _s("transport", "Transport & logistics",
       ["transportes", "transporte", "logistica", "logistics", "transport", "frota", "fleet", "armazenagem",
        "shipping", "freight"],
       {},
       [("Fleet", "What are the age of the fleet and the replacement capex plan?", "Fleet register and capex plan"),
        ("Fuel", "How are fuel costs passed through to customers?", "Customer contracts with fuel clauses"),
        ("Leases", "How is the fleet financed (leases, renting), and is it all in reported debt?",
         "Fleet financing agreements; IFRS 16 reconciliation"),
        ("Contracts", "What volumes and terms are secured with the main customers?", "Top 10 customer contracts"),
        ("Claims", "What is the history of damage and accident claims?", "Claims register and insurance")]),
]
SECTOR_BY_KEY = {s.key: s for s in SECTORS}
GENERAL = SECTOR_BY_KEY["general"]


def get(key: str | Sector | None) -> Sector:
    if isinstance(key, Sector):
        return key
    if not key:
        return GENERAL
    if key not in SECTOR_BY_KEY:
        raise ValueError(f"Unknown sector '{key}'. Options: {', '.join(SECTOR_BY_KEY)}")
    return SECTOR_BY_KEY[key]


def _norm(text: str) -> str:
    t = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", t)).strip()


def suggest(text: str, company: str = "") -> tuple[Sector, list[str]]:
    """The sector with the most distinct keywords in the data room (a keyword in the company name counts
    three times), with the words found; 'General' when nothing matches. Distinct words, not counts, so a
    customer listing full of 'Automóvel' does not make a distributor a car dealer. The reviewer confirms it."""
    # what the company says it does ('Atividade | Distribuição B2B de…') weighs like its name; only the first
    # words, before the customers it serves ('… a clientes dos setores automóvel, alimentar')
    activity = " ".join(" ".join(_norm(m.group(1)).split()[:8]) for m in re.finditer(
        r"(?im)(?:atividade|actividade|activity|activities|business description|nature of (?:the )?business|"
        r"objeto social)\s*\|\s*(?:[A-Z]+\d+:\s*)?(.*)$", text))
    body, name = f" {_norm(text)} ", f" {_norm(company)} {_norm(activity)} "
    best, best_score, best_words = GENERAL, 0, []
    for s in SECTORS[1:]:
        score, words = 0, []
        for k in s.keywords:
            n = (f" {k} " in body) + 3 * (f" {k} " in name)
            if n:
                score += n
                words.append(k)
        if score > best_score:
            best, best_score, best_words = s, score, words
    return best, best_words
