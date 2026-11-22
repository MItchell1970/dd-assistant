"""Layer 1d — ESEF: the annual financial report every EU listed company files in iXBRL since 2021.

Each figure in an ESEF report is tagged with its IFRS meaning, period, unit and sign, so nothing has
to be guessed: the reader takes the tagged facts of the consolidated primary statements, lays them out
in the order the company presents them, and hands them to the same engine as an Excel data room.
  - IFRS concepts get the name the dictionary knows ('ifrs-full:Revenue' -> 'Revenue');
  - the company's own concepts (extensions) are understood through their ESEF anchoring, the IFRS
    concepts they contain ('Cost of energy sales and other' contains 'RawMaterialsAndConsumablesUsed'),
    or else through their English label;
  - every figure keeps its tag as the source ('ifrs-full:Revenue').
Upload the report package (.zip, from https://filings.xbrl.org or the company's website): it carries the
presentation, labels and anchoring the reader needs. Euros only, like the rest of the engine.
"""
from __future__ import annotations

import io
import re
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import PurePosixPath

from openpyxl import Workbook

from .extract import FIELDS, ExtractionError, _norm

# IFRS concept -> the name the dictionary of extract.py recognises. The order matters when a company's own
# concept contains several of them: it is named after the first ('Purchase of property, plant and equipment
# and purchase of intangible assets').
CANONICAL = {
    # income statement
    "Revenue": "Revenue", "RevenueFromContractsWithCustomers": "Revenue", "CostOfSales": "Cost of sales",
    "RawMaterialsAndConsumablesUsed": "Cost of materials consumed", "CostOfMerchandiseSold": "Cost of goods sold",
    "CostOfPurchasedEnergySold": "Cost of materials consumed",
    "ChangesInInventoriesOfFinishedGoodsAndWorkInProgress": "Change in manufactured inventories",
    "OtherWorkPerformedByEntityAndCapitalised": "Own work capitalised", "GrossProfit": "Gross profit",
    "ServicesExpense": "External supplies and services", "EmployeeBenefitsExpense": "Staff costs",
    "DistributionCosts": "Distribution costs", "AdministrativeExpense": "Administrative expenses",
    "SellingGeneralAndAdministrativeExpense": "Selling, general and administrative",
    "ResearchAndDevelopmentExpense": "Research and development", "OtherIncome": "Other income",
    "OtherOperatingIncomeExpense": "Other operating income", "OtherExpenseByNature": "Other expenses",
    "OtherOperatingExpense": "Other operating expenses",
    "TaxExpenseOtherThanIncomeTaxExpense": "Taxes other than income tax", "OtherGainsLosses": "Other gains and losses",
    "ExpenseOfRestructuringActivities": "Restructuring",
    "ImpairmentLossRecognisedInProfitOrLossIntangibleAssetsAndGoodwill": "Impairment losses",
    "ImpairmentLossImpairmentGainAndReversalOfImpairmentLossDeterminedInAccordanceWithIFRS9":
        "Impairment of receivables",
    "DepreciationAndAmortisationExpense": "Depreciation and amortisation",
    "DepreciationAmortisationAndImpairmentLossReversalOfImpairmentLossRecognisedInProfitOrLoss":
        "Depreciation and amortisation",
    "ShareOfProfitLossOfAssociatesAndJointVenturesAccountedForUsingEquityMethod":
        "Share of profit of associates and joint ventures",
    "ProfitLossFromOperatingActivities": "Operating profit", "FinanceIncome": "Finance income",
    "FinanceCosts": "Finance costs", "ProfitLossBeforeTax": "Profit before tax",
    "IncomeTaxExpenseContinuingOperations": "Income tax", "ProfitLoss": "Profit for the year",
    "ProfitLossAttributableToOwnersOfParent": "Attributable to owners of the parent",
    # balance sheet
    "PropertyPlantAndEquipment": "Property, plant and equipment", "Inventories": "Inventories",
    "CurrentInventoriesHeldForSale": "Inventories", "TradeAndOtherCurrentReceivables": "Trade and other receivables",
    "CurrentTradeReceivables": "Trade receivables", "CashAndCashEquivalents": "Cash and cash equivalents",
    "Equity": "Total equity", "LongtermBorrowings": "Borrowings", "NoncurrentPortionOfNoncurrentBorrowings": "Borrowings",
    "ShorttermBorrowings": "Borrowings", "CurrentBorrowingsAndCurrentPortionOfNoncurrentBorrowings": "Borrowings",
    "CurrentPortionOfLongtermBorrowings": "Borrowings", "TradeAndOtherCurrentPayables": "Trade and other payables",
    "TradeAndOtherCurrentPayablesToTradeSuppliers": "Trade payables", "CurrentTradePayables": "Trade payables",
    "NoncurrentAssets": "Total non-current assets", "CurrentAssets": "Total current assets",
    "NoncurrentLiabilities": "Total non-current liabilities", "CurrentLiabilities": "Total current liabilities",
    "Assets": "Total assets", "EquityAndLiabilities": "Total equity and liabilities",
    "NoncurrentLeaseLiabilities": "Lease liabilities", "CurrentLeaseLiabilities": "Lease liabilities",
    "NoncurrentProvisionsForEmployeeBenefits": "Post-employment benefit obligations",
    "CurrentProvisionsForEmployeeBenefits": "Post-employment benefit obligations",
    "OtherLongtermProvisions": "Provisions", "OtherShorttermProvisions": "Provisions",
    "CurrentTaxLiabilitiesCurrent": "Current tax liabilities", "OtherCurrentFinancialAssets": "Other financial assets",
    "OtherNoncurrentFinancialAssets": "Other financial assets",
    "OtherCurrentFinancialLiabilities": "Other financial liabilities",
    "OtherNoncurrentFinancialLiabilities": "Other financial liabilities",
    "NoncurrentAssetsOrDisposalGroupsClassifiedAsHeldForSale": "Assets held for sale",
    # cash flow statement
    "CashFlowsFromUsedInOperatingActivities": "Net cash from operating activities",
    "CashFlowsFromUsedInOperations": "Cash generated from operations",
    "AdjustmentsForDepreciationAndAmortisationExpense": "Depreciation and amortisation",
    "AdjustmentsForDepreciationAndAmortisationExpenseAndImpairmentLossReversalOfImpairmentLossRecognisedInProfitOrLoss":
        "Depreciation and amortisation",
    "AdjustmentsForDepreciationOfPropertyPlantAndEquipment": "Depreciation of property, plant and equipment",
    "AdjustmentsForAmortisationExpense": "Amortisation of intangible assets",
    "AdjustmentsForDepreciationOfIntangibleAssetsOtherThanGoodwill": "Amortisation of intangible assets",
    "PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities": "Purchase of property, plant and equipment",
    "PurchaseOfIntangibleAssetsClassifiedAsInvestingActivities": "Purchase of intangible assets",
    "ProceedsFromSalesOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities":
        "Proceeds from sale of property, plant and equipment",
}
# lines a company's own concept may be named after when it contains them (not totals, not items to assess)
CORE = [k for k, v in CANONICAL.items() if v not in (
    "Lease liabilities", "Post-employment benefit obligations", "Provisions", "Current tax liabilities",
    "Other financial assets", "Other financial liabilities", "Assets held for sale", "Total equity",
    "Total non-current assets", "Total current assets", "Total non-current liabilities", "Total current liabilities",
    "Total assets", "Total equity and liabilities")]
# section headers of the balance sheet, from the IFRS abstract concepts (they carry no figure)
HEADERS = {"NoncurrentAssetsAbstract": "Non-current assets", "CurrentAssetsAbstract": "Current assets",
           "EquityAbstract": "Equity", "EquityAndLiabilitiesAbstract": "Equity and liabilities",
           "LiabilitiesAbstract": "Liabilities", "NoncurrentLiabilitiesAbstract": "Non-current liabilities",
           "CurrentLiabilitiesAbstract": "Current liabilities"}
TITLES = {"pl": "ESEF income statement", "bs": "ESEF balance sheet", "cf": "ESEF cash flow"}
LABEL_ROLES = ("/label", "/terseLabel", "/totalLabel", "/verboseLabel", "/periodEndLabel", "/negatedLabel",
               "/negatedTerseLabel", "/documentation")
ENTITY = {"NameOfReportingEntityOrOtherMeansOfIdentification": "Name of the reporting entity",
          "LegalFormOfEntity": "Legal form", "CountryOfIncorporation": "Country of incorporation",
          "DomicileOfEntity": "Domicile", "PrincipalPlaceOfBusiness": "Principal place of business",
          "DescriptionOfNatureOfEntitysOperationsAndPrincipalActivities": "Nature of business"}
_ATTRS = re.compile(r"([\w:.-]+)=\"([^\"]*)\"")

# A report package is opened only within these limits: a malicious or broken .zip could otherwise expand to fill the
# memory (a 'zip bomb') or write outside its folder. Real ESEF packages: 1-100 MB expanded (EDP FY2025, the largest
# seen: 96 MB compressed), XHTML and XML compress 5-30 times.
MAX_EXPANDED = 300 * 1024 * 1024      # bytes, the whole package once expanded
MAX_RATIO = 200                       # expanded / compressed, for any member above 1 MB expanded
MAX_MEMBERS = 5000


def check_package(name: str, z: zipfile.ZipFile) -> None:
    """Refuse a package that is too large once expanded, compressed suspiciously well or has unsafe paths. The sizes
    are the ones the archive declares, and Python's zipfile never expands a member beyond its declared size."""
    infos = z.infolist()
    if len(infos) > MAX_MEMBERS:
        raise ExtractionError(f"{name} has {len(infos):,} files: more than an ESEF report package ({MAX_MEMBERS:,}). "
                              "Not opened.")
    total = 0
    for i in infos:
        path = i.filename.replace("\\", "/")
        if path.startswith("/") or re.match(r"[A-Za-z]:", path) or ".." in PurePosixPath(path).parts:
            raise ExtractionError(f"{name} contains an unsafe path ({i.filename}). Not opened.")
        total += i.file_size
        if i.file_size > 1024 * 1024 and i.file_size > MAX_RATIO * max(i.compress_size, 1):
            raise ExtractionError(f"{name}: {i.filename} expands {i.file_size / max(i.compress_size, 1):,.0f} times "
                                  f"(limit {MAX_RATIO}). Not opened: it looks like a zip bomb, not a report package.")
    if total > MAX_EXPANDED:
        raise ExtractionError(f"{name} expands to {total / 1024 ** 2:,.0f} MB, above the {MAX_EXPANDED // 1024 ** 2} MB "
                              "limit for a report package. Not opened.")


@dataclass
class EsefReport:
    name: str
    company: str
    book: bytes                          # the primary statements as a workbook for the engine
    where: dict[tuple[str, int], str]    # (sheet, row) -> the tag of that line
    facts: int                           # tagged facts in euros used
    text: str                            # statements and entity information, for the memo
    blocks: list[str] = field(default_factory=list)      # IFRS text blocks of the notes tagged in the report
    conflicts: list[str] = field(default_factory=list)   # a statement tag with two different values, same period

    def tag(self, source: str, prefix: str = "") -> str:
        """'ESEF income statement!B7:C7' -> 'ifrs-full:Revenue': the tag is the source."""
        titles = "|".join(map(re.escape, TITLES.values()))

        def sub(m):
            concept = self.where.get((m.group(1), int(m.group(2))))
            return prefix + concept if concept else m.group(0)
        return re.sub(rf"(?<!\w)({titles})!B(\d+):[A-Z]+\d+", sub, source)


def _attrs(tag: str) -> dict[str, str]:
    return dict(_ATTRS.findall(tag))


def _local(href: str) -> str:
    """'ifrs-full_Revenue' or 'ifrs-full:Revenue' -> 'Revenue'."""
    return re.split(r"[_:]", href, maxsplit=1)[-1]


def _qname(href: str) -> str:
    return href.replace("_", ":", 1)


def _humanise(local: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", local).capitalize()


def _clean(label: str) -> str:
    return re.sub(r"\s*\[(?:abstract|line items|table)\]\s*$", "", label, flags=re.I).strip()


PACKAGES = (".zip", ".xbri")   # .xbri: the XBRL Report Package 1.0 name for an inline report package (a .zip)


def is_esef(name: str, content: bytes) -> bool:
    """An ESEF report package (.zip or .xbri with reports/*.xhtml) or an inline XBRL report on its own."""
    low = name.lower()
    if low.endswith(PACKAGES):
        try:
            return any(_is_report(n) for n in zipfile.ZipFile(io.BytesIO(content)).namelist())
        except zipfile.BadZipFile:
            return False
    return low.endswith((".xhtml", ".html", ".htm")) and b"<ix:header" in content


def _is_report(member: str) -> bool:
    return member.lower().endswith((".xhtml", ".html")) and "/reports/" in f"/{member.lower()}"


NAMESPACES = {"link": "http://www.xbrl.org/2003/linkbase", "xbrli": "http://www.xbrl.org/2003/instance",
              "ix": "http://www.xbrl.org/2013/inlineXBRL"}
LINK_ELEMENTS = ("linkbase", "roleRef", "arcroleRef", "loc", "label", "labelLink", "labelArc", "presentationLink",
                 "presentationArc", "definitionLink", "definitionArc", "calculationLink", "calculationArc")


def _prefixes(text: str, prefix: str) -> str:
    """The reader looks for 'link:', 'xbrli:' and 'ix:'. A prefix is only a name for a namespace: a file that binds
    another one (or the linkbase as default namespace, as Schneider Electric's) is written with the usual ones."""
    uri = NAMESPACES[prefix]
    head = text[:20000]
    for other in re.findall(rf'xmlns:([\w.-]+)="{re.escape(uri)}"', head):
        if other != prefix:
            text = re.sub(rf"<(/?){re.escape(other)}:", rf"<\1{prefix}:", text)
    if prefix == "link" and re.search(rf'xmlns="{re.escape(uri)}"', head):
        text = re.sub(rf"<(/?)(?=(?:{'|'.join(LINK_ELEMENTS)})\b)", r"<\1link:", text)
    return text


def _balances(z: zipfile.ZipFile) -> dict[str, str]:
    """The company's own concepts and their balance in its schema (.xsd): 'GastosDeServicios' -> 'credit'."""
    out = {}
    for n in z.namelist():
        if n.lower().endswith(".xsd"):
            for tag in re.findall(r"<(?:\w+:)?element\b[^>]*>", z.read(n).decode("utf-8", "ignore")):
                a = _attrs(tag)
                if a.get("name") and a.get("xbrli:balance"):
                    out[a["name"]] = a["xbrli:balance"]
    return out


def _nature(label: str) -> str | None:
    """'cost' or 'income': what the dictionary of extract.py reads an income statement line as; None: not known."""
    n = _norm(label.split(" (")[0])
    for f in FIELDS:
        if f.statement == "pl" and any(n == x or n.startswith(x + " ") for x in f.synonyms + f.adds):
            return "cost" if f.sign < 0 else "income" if f.key in ("vendas", "orend", "own") else None
    return None


def _package(name: str, content: bytes) -> tuple[str, dict[str, str]]:
    """The report and the company's taxonomy files (labels, presentation, anchoring)."""
    try:
        z = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile:
        raise ExtractionError(f"{name} is not a valid .zip file.") from None
    check_package(name, z)
    report = next(n for n in z.namelist() if _is_report(n))
    taxonomy = {PurePosixPath(n).name: _prefixes(z.read(n).decode("utf-8", "ignore"), "link") for n in z.namelist()
                if re.search(r"_(lab-[\w-]+|pre|def)\.xml$", n.lower())}
    taxonomy["balances"] = _balances(z)
    return _prefixes(_prefixes(z.read(report).decode("utf-8", "ignore"), "xbrli"), "ix"), taxonomy


def _periods(text: str) -> tuple[dict[str, tuple[str, int]], dict[str, str]]:
    """Contexts without dimensions (the consolidated figures) at the financial year end: id -> ('instant' or
    'duration', fiscal year); and units: id -> measure."""
    raw = []
    for m in re.finditer(r"<xbrli:context\b([^>]*)>(.*?)</xbrli:context>", text, re.S):
        body = m.group(2)
        if "segment" in body or "scenario" in body:
            continue
        cid = _attrs(m.group(1)).get("id")
        if (inst := re.search(r"<xbrli:instant>\s*(\d{4}-\d\d-\d\d)", body)):
            raw.append((cid, "instant", None, date.fromisoformat(inst.group(1))))
        elif (start := re.search(r"<xbrli:startDate>\s*(\d{4}-\d\d-\d\d)", body)) and \
                (end := re.search(r"<xbrli:endDate>\s*(\d{4}-\d\d-\d\d)", body)):
            raw.append((cid, "duration", date.fromisoformat(start.group(1)), date.fromisoformat(end.group(1))))
    years = [e for _, kind, s, e in raw if kind == "duration" and 350 <= (e - s).days <= 380]
    if not years:
        raise ExtractionError("No full financial year found in this ESEF report.")
    year_end = max(years)

    def at_year_end(d: date) -> bool:                  # 31 December, or the company's own year end (52/53 weeks)
        try:
            return abs((d.replace(year=year_end.year) - year_end).days) <= 7
        except ValueError:                             # 29 February
            return False

    contexts = {cid: (kind, e.year) for cid, kind, s, e in raw if at_year_end(e) and
                (kind == "instant" or 350 <= (e - s).days <= 380)}
    units = {}
    for m in re.finditer(r"<xbrli:unit\b([^>]*)>(.*?)</xbrli:unit>", text, re.S):
        units[_attrs(m.group(1)).get("id")] = "/".join(re.findall(r"<xbrli:measure>\s*([^<\s]+)", m.group(2)))
    return contexts, units


def _value(raw: str, a: dict[str, str]) -> float | None:
    """The fact's value in EUR thousands: displayed number, transformation format, scale and sign."""
    fmt = a.get("format", "").lower()
    shown = re.sub(r"<[^>]+>", "", raw).strip()
    if "zero" in fmt or shown in ("-", "—", "–", ""):  # ixt:fixed-zero, ixt:zerodash
        number = 0.0
    else:
        digits = re.sub(r"[^\d.,]", "", shown)
        if "comma" in fmt:                             # num-comma-decimal: 1.234.567,8
            digits = digits.replace(".", "").replace(",", ".")
        else:                                          # num-dot-decimal: 1,234,567.8
            digits = digits.replace(",", "")
        try:
            number = float(digits)
        except ValueError:
            return None
    number *= 10 ** int(a.get("scale") or 0) / 1000
    return -number if a.get("sign") == "-" else number


def _tolerance(precision: float) -> float:
    """What a fact rounded to `decimals` may differ by, in EUR thousands (decimals -3: 1; -6: 1,000)."""
    return 0.0 if precision >= 99 else 10 ** -precision / 1000 if precision > -99 else float("inf")


def _facts(text: str, contexts: dict, units: dict) -> tuple[dict[str, dict[str, dict[int, float]]], int, dict]:
    """Monetary facts in euros: concept -> period type -> {year: EUR k}; how many; and the entity's text facts.
    entity['conflicts'] lists (concept, period type, year, values) when the same tag and period carries figures
    that differ by more than their rounding: XBRL 'inconsistent duplicates', a sign of a mis-tagged line."""
    best: dict[tuple[str, str, int], tuple[float, float]] = {}
    seen: dict[tuple[str, str, int], list[tuple[float, float]]] = defaultdict(list)
    currencies: dict[str, int] = defaultdict(int)
    for m in re.finditer(r"<ix:nonFraction\b([^>]*)>(.*?)</ix:nonFraction>", text, re.S):
        a = _attrs(m.group(1))
        unit = units.get(a.get("unitRef"), "")
        if a.get("contextRef") not in contexts or not re.fullmatch(r"iso4217:[A-Z]{3}", unit):
            continue                                   # segments, shares, ratios, per-share amounts
        currencies[unit[-3:]] += 1
        v = _value(m.group(2), a)
        if unit != "iso4217:EUR" or v is None:
            continue
        kind, year = contexts[a["contextRef"]]
        precision = 99.0 if a.get("decimals", "").upper() == "INF" else float(a.get("decimals") or -99)
        key = (a["name"], kind, year)
        seen[key].append((precision, v))
        if key not in best or precision > best[key][0]:  # the same figure rounded in the management report
            best[key] = (precision, v)
    if currencies and max(currencies, key=currencies.get) != "EUR":
        raise ExtractionError(f"This ESEF report is in {max(currencies, key=currencies.get)}. DD Assistant analyses "
                              "statements in euros (European market).")
    values: dict[str, dict[str, dict[int, float]]] = defaultdict(lambda: defaultdict(dict))
    for (concept, kind, year), (_, v) in best.items():
        values[concept][kind][year] = v
    entity = {}
    for m in re.finditer(r"<ix:nonNumeric\b([^>]*)>", text):   # by the opening tag: a text block can contain them
        local = _local(_attrs(m.group(1)).get("name", ""))
        if local in ENTITY and local not in entity:
            end = text.find("</ix:nonNumeric>", m.end())
            entity[local] = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text[m.end():end])).strip()[:400]
    if (lei := re.search(r"<xbrli:identifier\b[^>]*>\s*([A-Z0-9]{20})\s*<", text)):
        entity["LEI"] = lei.group(1)
    conflicts = []
    for key, found in seen.items():
        p, v = best[key]
        other = [(q, w) for q, w in found if abs(w - v) > max(_tolerance(q), _tolerance(p), 0.5)]
        if other:
            conflicts.append((*key, sorted({v, *(w for _, w in other)})))
    return values, len(best), {**entity, "conflicts": conflicts}


def _labels(taxonomy: dict[str, str]) -> dict[str, str]:
    """The company's labels for its own concepts: English first, then any other language."""
    out: dict[str, str] = {}
    for name in sorted((n for n in taxonomy if "_lab-" in n), key=lambda n: ("_lab-en" not in n, n)):
        lab = taxonomy[name]
        locs = {_attrs(t)["xlink:label"]: _attrs(t)["xlink:href"].split("#")[-1]
                for t in re.findall(r"<link:loc\b[^>]*>", lab)}
        texts: dict[str, dict[str, str]] = defaultdict(dict)
        for m in re.finditer(r"<link:label\b([^>]*)>(.*?)</link:label>", lab, re.S):
            a = _attrs(m.group(1))
            role = next((r for r in LABEL_ROLES if a.get("xlink:role", "").endswith(r)), None)
            if role:
                texts[a["xlink:label"]][role] = re.sub(r"\s+", " ", m.group(2)).strip()
        for arc in re.findall(r"<link:labelArc\b[^>]*>", lab):
            a = _attrs(arc)
            concept, found = locs.get(a.get("xlink:from"), ""), texts.get(a.get("xlink:to"), {})
            if concept not in out and (best := next((found[r] for r in LABEL_ROLES if r in found), None)):
                out[concept] = best
    return out


def _anchors(taxonomy: dict[str, str]) -> dict[str, list[str]]:
    """The company's own concept -> the IFRS concepts it contains (ESEF wider-narrower anchoring)."""
    out: dict[str, list[str]] = defaultdict(list)
    for name, d in taxonomy.items():
        if not name.endswith("_def.xml"):
            continue
        for link in re.finditer(r"<link:definitionLink\b[^>]*>(.*?)</link:definitionLink>", d, re.S):
            locs = {_attrs(t)["xlink:label"]: _attrs(t)["xlink:href"].split("#")[-1]
                    for t in re.findall(r"<link:loc\b[^>]*>", link.group(1))}
            for t in re.findall(r"<link:definitionArc\b[^>]*>", link.group(1)):
                a = _attrs(t)
                if a.get("xlink:arcrole", "").endswith("wider-narrower"):
                    out[locs[a["xlink:from"]]].append(locs[a["xlink:to"]])
    return out


def _kind(root: str) -> tuple[str, int] | None:
    """Which primary statement a presentation tree is, from its root ('StatementOfCashFlowsAbstract'), and a
    preference: the income statement before a statement of comprehensive income."""
    r = _local(root).lower()
    if not r.startswith(("statementof", "incomestatement", "balancesheet")):
        return None                                    # notes ('DisclosureOf…'), changes in equity
    if "cashflow" in r:
        return "cf", 0
    if "financialposition" in r or "balancesheet" in r:
        return "bs", 0
    if "incomestatement" in r or "profitorloss" in r:
        return "pl", 0
    return ("pl", 1) if "comprehensiveincome" in r else None


def _statements(taxonomy: dict[str, str]) -> dict[str, list[tuple[int, str]]]:
    """Each primary statement as (depth, concept) in presentation order, from the presentation linkbase."""
    pre = next((t for n, t in taxonomy.items() if n.endswith("_pre.xml")), "")
    found: dict[str, tuple[int, list[tuple[int, str]]]] = {}
    for role in re.finditer(r"<link:presentationLink\b[^>]*>(.*?)</link:presentationLink>", pre, re.S):
        body = role.group(1)
        locs = {_attrs(t)["xlink:label"]: _attrs(t)["xlink:href"].split("#")[-1]
                for t in re.findall(r"<link:loc\b[^>]*>", body)}
        kids, children = defaultdict(list), set()
        for t in re.findall(r"<link:presentationArc\b[^>]*>", body):
            a = _attrs(t)
            kids[a["xlink:from"]].append((float(a.get("order") or 0), a["xlink:to"]))
            children.add(a["xlink:to"])
        roots = [n for n in kids if n not in children]
        kind = next((k for r in roots if (k := _kind(locs[r]))), None)
        if not kind:
            continue
        rows: list[tuple[int, str]] = []

        def walk(node, depth):
            rows.append((depth, locs[node]))
            for _, k in sorted(kids[node]):
                walk(k, depth + 1)

        for r in roots:
            walk(r, 0)
        if kind[0] in found and found[kind[0]][0] <= kind[1]:
            # a balance sheet presented in two parts (assets; equity and liabilities, as Schneider Electric's): the
            # second part completes the first. Otherwise the first statement of each kind is the consolidated one.
            first = {_local(h) for _, h in found[kind[0]][1]}
            these = {_local(h) for _, h in rows}
            if kind[0] == "bs" and "Assets" in first and "Assets" not in these and \
                    "EquityAndLiabilities" not in first and {"EquityAndLiabilities", "Equity"} & these:
                found["bs"] = (found["bs"][0], found["bs"][1] + rows)
            continue
        found[kind[0]] = (kind[1], rows)
    return {k: rows for k, (_, rows) in found.items()}


def read_esef(name: str, content: bytes) -> EsefReport:
    """The consolidated primary statements of an ESEF report package, ready for the engine."""
    from .report import fmt_value

    if not name.lower().endswith(PACKAGES):
        raise ExtractionError(f"{name} is the ESEF report on its own. Upload the report package (.zip) instead — "
                              "on filings.xbrl.org it is the 'package' link: it carries the order of the statements "
                              "and the company's own labels and anchoring.")
    text, taxonomy = _package(name, content)
    contexts, units = _periods(text)
    values, count, entity = _facts(text, contexts, units)
    statements = _statements(taxonomy)
    if "pl" not in statements or "bs" not in statements:
        raise ExtractionError(f"No income statement or balance sheet found in the ESEF report {name}.")
    in_statements = {_qname(h) for rows in statements.values() for _, h in rows}
    conflicts = [f"{c} {'FY' + str(y)[2:]}: " + " vs ".join(fmt_value(v) for v in vs)
                 for c, kind, y, vs in sorted(entity.pop("conflicts"), key=lambda x: (x[0], x[2]))
                 if c in in_statements]
    blocks = sorted({_local(n) for n in re.findall(r"<ix:nonNumeric\b[^>]*?\bname=\"(ifrs-full:[^\"]+)\"", text)
                     if _local(n).startswith("DisclosureOf")})
    labels, anchors = _labels(taxonomy), _anchors(taxonomy)

    def label(href: str) -> str:
        local = _local(href)
        if href.startswith("ifrs-full") and local in CANONICAL:
            return CANONICAL[local]
        # a company concept that contains IFRS lines is named after them
        inside = sorted({_local(n) for n in anchors.get(href, []) if _local(n) in CORE}, key=CORE.index)
        names = list(dict.fromkeys(CANONICAL[c] for c in inside))
        own = _clean(labels.get(href) or _humanise(local))
        if not names and local in CANONICAL:            # a company concept named exactly like an IFRS one: the IFRS
            return CANONICAL[local]                     # name (its tag, the source, shows it is the company's own)
        if names:                                      # ... and the company's own name stays visible
            text = names[0] + "".join(f" and {n[0].lower()}{n[1:]}" for n in names[1:])
            return text if _norm(own) == _norm(text) else f"{text} ({own})"
        return own

    wb, where = Workbook(), {}
    ws = wb.active
    ws.title = "ESEF entity"
    company = entity.get("NameOfReportingEntityOrOtherMeansOfIdentification") or PurePosixPath(name).stem
    ws.append([company])
    info = [(ENTITY.get(k, k), v) for k, v in entity.items()]
    for key, value in info:
        if len(value) <= 80:                            # the description of the business goes to the memo only
            ws.append([key, value])
    out = [f"ESEF annual financial report (iXBRL) of {company}. Figures in EUR thousands, read from the tags; "
           "the tag of each line is in brackets."] + [f"{k} | {v}" for k, v in info]
    for kind in ("pl", "bs", "cf"):
        period = "instant" if kind == "bs" else "duration"
        anchor = {"pl": "Revenue", "bs": "Assets", "cf": "CashFlowsFromUsedInOperatingActivities"}[kind]
        years = sorted(values.get(f"ifrs-full:{anchor}", {}).get(period, {})) or \
            sorted({y for c in values.values() for y in c.get(period, {})})
        ws = wb.create_sheet(TITLES[kind])
        ws.append(["EUR thousands"] + years)
        out += ["", f"### {TITLES[kind].removeprefix('ESEF ').capitalize()} (EUR thousands)"]

        def line(text_label, figures, tag):
            ws.append([text_label] + figures)
            where[(ws.title, ws.max_row)] = tag
            out.append(f"{text_label} [{tag}] | " + " | ".join(f"FY{str(y)[2:]}: {fmt_value(v)}"
                                                               for y, v in zip(years, figures) if v is not None))

        for depth, href in statements.get(kind, []):
            local, facts = _local(href), values.get(_qname(href), {}).get(period, {})
            balance = taxonomy["balances"].get(local) if kind == "pl" and not href.startswith("ifrs-full") else None
            if local.endswith("Abstract"):
                if kind != "pl":                        # sections of the balance sheet and the cash flow
                    ws.append([HEADERS.get(local) or _clean(labels.get(href) or _humanise(local[:-8]))])
                    out.append(ws.cell(ws.max_row, 1).value + ":")
                continue
            if any(y in facts for y in years) and not (kind == "cf" and local == "CashAndCashEquivalents"):
                text_label, figures = label(href), [facts.get(y) for y in years]
                # IFRS tags a cost as a positive debit and an income as a positive credit, and the reader relies on
                # it. A company's own cost concept defined as a credit (Iberdrola's 'Gastos de servicios') carries
                # the cost as a negative figure: it is turned to the IFRS way (and an income defined as a debit).
                if (balance, _nature(text_label)) in (("credit", "cost"), ("debit", "income")):
                    figures = [None if v is None else -v for v in figures]
                    text_label += f" (sign turned: {balance} concept)"
                line(text_label, figures, _qname(href))
        if kind == "cf":                                # opening and closing cash, from the balance sheet dates
            cash = values.get("ifrs-full:CashAndCashEquivalents", {}).get("instant", {})
            line("Cash and cash equivalents at beginning of period", [cash.get(y - 1) for y in years],
                 "ifrs-full:CashAndCashEquivalents (opening)")
            line("Cash and cash equivalents at end of period", [cash.get(y) for y in years],
                 "ifrs-full:CashAndCashEquivalents")
    buf = io.BytesIO()
    wb.save(buf)
    return EsefReport(name, company, buf.getvalue(), where, count, "\n".join(out), blocks, conflicts)
