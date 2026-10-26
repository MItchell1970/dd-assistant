"""Linha de comandos.

Uso:
    python -m dd_assistant data/DD_template_modulo1.xlsx
    python -m dd_assistant data/DD_template_modulo1.xlsx --out output
    python -m dd_assistant data/DD_template_modulo1.xlsx --memo --data-room data/Duriva_data_room.xlsx
    python -m dd_assistant data/DD_template_modulo1.xlsx --check-memo memo.md --data-room data/Duriva_data_room.xlsx
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .input_loader import load_input
from .metrics import compute_metrics
from .report import summary, write_csv, write_excel
from .rules import alerts, evaluate


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Due Diligence Assistant — gera os red flags a partir do template Excel.")
    p.add_argument("template", help="Caminho do template Excel preenchido (folha Input)")
    p.add_argument("--out", default="output", help="Pasta onde gravar os resultados (por defeito: output)")
    p.add_argument("--memo", action="store_true",
                   help="Escreve também o memo e a request list com a Claude API (precisa de --data-room e da chave)")
    p.add_argument("--data-room", help="Data room em Excel, enviado à IA em texto integral (usado com --memo)")
    p.add_argument("--check-memo", metavar="MEMO",
                   help="Verifica um memo já escrito (por exemplo, no claude.ai) contra o material; precisa de --data-room")
    args = p.parse_args(argv)
    if (args.memo or args.check_memo) and not args.data_room:
        p.error("--memo e --check-memo precisam de --data-room (o data room da empresa)")

    path = Path(args.template)
    extra = [Path(f) for f in (args.data_room, args.check_memo) if f]
    for f in [path] + extra:
        if not f.exists():
            print(f"Ficheiro não encontrado: {f}", file=sys.stderr)
            return 1

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")   # acentos corretos na consola do Windows

    data = load_input(path)
    metrics = compute_metrics(data)
    results = evaluate(data, metrics)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stem = path.stem
    write_excel(results, metrics, data.years, out / f"{stem}_red_flags.xlsx")
    write_csv(results, out / f"{stem}_red_flags.csv")

    print(summary(results))
    print(f"\nResultados gravados em: {out.resolve()}")
    rc = _memo(data, metrics, results, args.data_room, out, path) if args.memo else 0
    if args.check_memo:
        rc = max(rc, _check(data, metrics, results, args.data_room, Path(args.check_memo), out, path))
    return rc


def _verify(memo_text: str, material: str, results, report_file: Path) -> bool:
    """Corre o verificador, mostra o resultado e grava-o ao lado do memo."""
    from .memo_check import check_memo, report

    check = check_memo(memo_text, material, [r.rule.id for r in alerts(results)])
    text = report(check)
    report_file.write_text(text + "\n", encoding="utf-8")
    print(f"\n{text}\nVerificação gravada em: {report_file.resolve()}")
    return check.ok


def _check(data, metrics, results, data_room, memo_path: Path, out: Path, template: Path) -> int:
    """Verifica um memo já escrito contra o material que o programa enviaria à IA."""
    from .ai_memo import build_material

    material = build_material(data, metrics, results, data_room, name=template.name)
    ok = _verify(memo_path.read_text(encoding="utf-8"), material, results, out / f"{memo_path.stem}_verificacao.md")
    return 0 if ok else 1


def _memo(data, metrics, results, data_room, out: Path, template: Path) -> int:
    """Camada 5: envia o material à Claude API e grava o memo (e o material, para auditoria)."""
    import anthropic   # só é preciso quando se pede o memo
    from .ai_memo import MODEL, MemoError, build_material, load_env, write_memo

    material = build_material(data, metrics, results, data_room, name=template.name)
    material_file = out / f"{template.stem}_material_ia.md"
    material_file.write_text(material, encoding="utf-8")
    load_env()

    print(f"\nA escrever o memo com {MODEL} (pode demorar alguns minutos; primeiro o modelo pensa)...\n")
    try:
        memo = write_memo(material, on_text=lambda t: print(t, end="", flush=True))
    except anthropic.AuthenticationError:
        print("\nA chave da Claude API é inválida. Confirme ANTHROPIC_API_KEY no ficheiro .env.", file=sys.stderr)
        return 1
    except anthropic.RateLimitError:
        print("\nLimite de pedidos atingido. Espere um minuto e tente outra vez.", file=sys.stderr)
        return 1
    except anthropic.APIStatusError as e:
        print(f"\nErro da Claude API ({e.status_code}): {e.message}", file=sys.stderr)
        return 1
    except anthropic.APIConnectionError:
        print("\nSem ligação à Claude API. Verifique a internet.", file=sys.stderr)
        return 1
    except MemoError as e:
        print(f"\n{e}", file=sys.stderr)
        return 1
    except anthropic.AnthropicError as e:   # por exemplo, nenhuma chave configurada
        print(f"\nNão foi possível chamar a Claude API: {e}\n"
              "Crie o ficheiro .env a partir do .env.example e cole lá a sua chave.", file=sys.stderr)
        return 1

    memo_file = out / f"{template.stem}_memo.md"
    memo_file.write_text(memo.text, encoding="utf-8")
    print(f"\n\nMemo gravado em: {memo_file.resolve()}")
    print(f"Material enviado à IA: {material_file.resolve()}")
    print(f"{memo.model} · {memo.input_tokens:,} tokens de entrada, {memo.output_tokens:,} de saída "
          f"· custo estimado ≈ {memo.cost_usd:.2f} USD")
    if memo.truncated:
        print("Atenção: a resposta parou no limite de tokens e pode estar incompleta.", file=sys.stderr)
    _verify(memo.text, material, results, out / f"{template.stem}_memo_verificacao.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
