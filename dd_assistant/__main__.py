"""Linha de comandos.

Uso:
    python -m dd_assistant data/DD_template_modulo1.xlsx
    python -m dd_assistant data/DD_template_modulo1.xlsx --out output
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .input_loader import load_input
from .metrics import compute_metrics
from .report import summary, write_csv, write_excel
from .rules import evaluate


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Due Diligence Assistant — gera os red flags a partir do template Excel.")
    p.add_argument("template", help="Caminho do template Excel preenchido (folha Input)")
    p.add_argument("--out", default="output", help="Pasta onde gravar os resultados (por defeito: output)")
    args = p.parse_args(argv)

    path = Path(args.template)
    if not path.exists():
        print(f"Ficheiro não encontrado: {path}", file=sys.stderr)
        return 1

    data = load_input(path)
    metrics = compute_metrics(data)
    results = evaluate(data, metrics)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stem = path.stem
    write_excel(results, metrics, data.years, out / f"{stem}_red_flags.xlsx")
    write_csv(results, out / f"{stem}_red_flags.csv")

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")   # acentos corretos na consola do Windows
    print(summary(results))
    print(f"\nResultados gravados em: {out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
