"""Sector benchmarks for dd_assistant/sectors.py, from Aswath Damodaran's public industry datasets (Europe).

Source: Damodaran Online, NYU Stern — https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datacurrent.html
Files (Europe, updated January 2026): marginEurope.xls, wcdataEurope.xls, capexEurope.xls, dbtfundEurope.xls,
downloaded from https://pages.stern.nyu.edu/~adamodar/pc/datasets/

Run once a year, when the datasets are updated, and paste the output into BENCHMARKS in sectors.py:
    pip install xlrd          # reads the old .xls format; not needed by the app itself
    python scripts/sector_benchmarks.py <folder with the four .xls files>
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

import xlrd

# sector key in sectors.py -> Damodaran industry name
INDUSTRIES = {
    "general": "Total Market (without financials)", "distribution": "Retail (Distributors)",
    "manufacturing": "Machinery", "materials": "Packaging & Container", "automotive": "Retail (Automotive)",
    "consumer_retail": "Retail (General)", "food": "Food Processing", "hardware": "Computers/Peripherals",
    "software": "Software (System & Application)", "services": "Business & Consumer Services",
    "construction": "Engineering/Construction", "healthcare": "Healthcare Products", "hospitality": "Hotel/Gaming",
    "energy": "Utility (General)", "transport": "Transportation",
}
# benchmark key -> (file, column header)
COLUMNS = {
    "firms": ("marginEurope", "Number of firms"), "gross_margin": ("marginEurope", "Gross Margin"),
    "ebitda_margin": ("marginEurope", "EBITDA/Sales"), "receivables_sales": ("wcdataEurope", "Acc Rec/ Sales"),
    "inventory_sales": ("wcdataEurope", "Inventory/Sales"), "payables_sales": ("wcdataEurope", "Acc Pay/ Sales"),
    "nwc_sales": ("wcdataEurope", "Non-cash WC/ Sales"), "capex_da": ("capexEurope", "Cap Ex/Deprecn"),
    "debt_ebitda": ("dbtfundEurope", "Debt to EBITDA"),
}


def table(path: Path) -> tuple[dict[str, dict[str, float]], str]:
    sh = xlrd.open_workbook(path).sheet_by_name("Industry Averages")
    head = next(r for r in range(20) if sh.cell_value(r, 0) == "Industry Name")
    cols = [str(sh.cell_value(head, c)).strip() for c in range(sh.ncols)]
    rows = {str(sh.cell_value(r, 0)).strip(): dict(zip(cols, sh.row_values(r))) for r in range(head + 1, sh.nrows)}
    updated = datetime(1899, 12, 30) + timedelta(days=float(sh.cell_value(0, 1)))
    return rows, updated.strftime("%B %Y")


def main(folder: str) -> None:
    tables = {name: table(Path(folder) / f"{name}.xls") for name in {f for f, _ in COLUMNS.values()}}
    print(f'BENCHMARK_SOURCE = "Damodaran Online (NYU Stern), European listed companies, {tables["marginEurope"][1]}"')
    print("BENCHMARKS = {")
    for sector, industry in INDUSTRIES.items():
        values = {key: round(float(tables[f][0][industry][col]), 4) for key, (f, col) in COLUMNS.items()}
        values["firms"] = int(values["firms"])
        print(f'    "{sector}": {{"industry": "{industry}", ' + ", ".join(f'"{k}": {v}' for k, v in values.items()) + "},")
    print("}")


if __name__ == "__main__":
    main(sys.argv[1])
