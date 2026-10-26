"""Verificador do memo: tem de apanhar números inventados, alertas em falta e recomendações."""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from dd_assistant.__main__ import main
from dd_assistant.ai_memo import build_material
from dd_assistant.input_loader import load_input
from dd_assistant.memo_check import _readings, check_memo
from dd_assistant.metrics import compute_metrics
from dd_assistant.rules import alerts, evaluate

DATA = Path(__file__).resolve().parents[1] / "data"
TEMPLATE = DATA / "DD_template_modulo1.xlsx"
DATA_ROOM = DATA / "Duriva_data_room.xlsx"

# Memo curto e correto: todos os números vêm do material da Duriva, em vários formatos.
GOOD = """# Duriva — memo

O EBITDA reportado desceu de 1.640 para 1.415 € k; sem o ganho, seria 1 165 € k (R19, R04).
Os ajustes valem 32,2% do EBITDA reportado (R05, R06). As vendas subiram 9,2%; o cliente A tem 23,8% (R01, R02, R03).
A conversão de caixa foi 20.5% (R10, R07, R09). Vencem em 12 meses 55,2% da dívida, ou 4,35 milhões no total (R11, R20).
A DFC de 2024 difere do balanço em 85 € k (R13, R14). Faltam documentos (R18).

| Evidência (alerta e fonte) | O que pode significar | Pergunta à empresa |
|---|---|---|
| Outros rendimentos de 310 € k em 2025 (R04). | Um item pontual. | Qual o detalhe dos outros rendimentos? |

## Information request list

| Nº | Tema | Pedido | Pergunta associada | Alertas | Prioridade |
|---|---|---|---|---|---|
| 17 | Qualidade do EBITDA | Razão de outros rendimentos | Qual o detalhe dos outros rendimentos de 2025? | R04 | Alta |
"""


class MemoCheckTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        d = load_input(TEMPLATE)
        m = compute_metrics(d)
        cls.results = evaluate(d, m)
        cls.ids = [r.rule.id for r in alerts(cls.results)]
        cls.material = build_material(d, m, cls.results, DATA_ROOM)

    def check(self, memo):
        return check_memo(memo, self.material, self.ids)

    def test_good_memo_passes(self):
        c = self.check(GOOD)
        self.assertTrue(c.ok, c.errors)
        self.assertEqual(c.warnings, [])
        self.assertGreater(c.numbers_checked, 10)

    def test_invented_number_is_an_error(self):
        c = self.check(GOOD + "\nO EBITDA normalizado seria 9.876 € k.\n")
        self.assertFalse(c.ok)
        self.assertEqual([n for n, _ in c.unmatched_numbers], ["9.876"])

    def test_missing_alert_is_an_error(self):
        c = self.check(GOOD.replace("R20", ""))
        self.assertEqual(c.missing_alerts, ["R20"])
        self.assertFalse(c.ok)

    def test_investment_recommendation_is_an_error(self):
        c = self.check(GOOD + "\nRecomendamos a compra da empresa.\n")
        self.assertEqual(c.recommendations, ["Recomendamos a compra"])

    def test_question_without_request_is_a_warning(self):
        memo = GOOD.replace("| Um item pontual. | Qual o detalhe dos outros rendimentos? |",
                            "| Um item pontual. | Qual o detalhe dos outros rendimentos? |\n"
                            "| Imparidade de 160 € k (R05). | Custo recorrente. | Quem decidiu mudar de auditor? |")
        c = self.check(memo)
        self.assertTrue(c.ok)                                   # é só um aviso
        self.assertEqual(c.orphan_questions, ["Quem decidiu mudar de auditor?"])

    def test_missing_request_list_is_an_error(self):
        c = self.check(GOOD.split("## Information request list")[0])
        self.assertFalse(c.request_list_found)
        self.assertFalse(c.ok)

    def test_years_small_numbers_and_index_column_are_not_data(self):
        c = self.check("Em 2025, os 3 temas e os 15 alertas.\n\n| Nº | Pergunta associada |\n|---|---|\n| 17 | x? |\n")
        self.assertEqual(c.numbers_checked, 1)                  # só o 15

    def test_long_sentence_is_a_warning(self):
        c = self.check(GOOD + "\n" + " ".join(["palavra"] * 30) + ".\n")
        self.assertEqual(len(c.long_sentences), 1)

    def test_number_formats(self):
        self.assertEqual(_readings("23,8"), [(23.8, 1)])
        self.assertEqual(_readings("20.5"), [(20.5, 1)])
        self.assertEqual(_readings("1.415"), [(1415.0, 0), (1.415, 3)])   # milhares (pt) ou decimal (en)
        self.assertEqual(_readings("1 415"), [(1415.0, 0)])
        self.assertEqual(_readings("−114"), [(-114.0, 0)])


class CheckMemoCliTest(unittest.TestCase):
    def run_cli(self, memo_text):
        with tempfile.TemporaryDirectory() as tmp:
            memo = Path(tmp) / "memo.md"
            memo.write_text(memo_text, encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()) as out:
                rc = main([str(TEMPLATE), "--check-memo", str(memo), "--data-room", str(DATA_ROOM), "--out", tmp])
            report = (Path(tmp) / "memo_verificacao.md").read_text(encoding="utf-8")
        return rc, out.getvalue(), report

    def test_good_memo_exit_code_0(self):
        rc, out, report = self.run_cli(GOOD)
        self.assertEqual(rc, 0)
        self.assertIn("Verificação automática do memo: OK", out)
        self.assertIn("OK", report)

    def test_bad_memo_exit_code_1(self):
        rc, _, report = self.run_cli(GOOD + "\nO EBITDA normalizado seria 9.876 € k.\n")
        self.assertEqual(rc, 1)
        self.assertIn("9.876", report)


if __name__ == "__main__":
    unittest.main()
