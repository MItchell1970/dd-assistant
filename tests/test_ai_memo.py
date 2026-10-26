"""Camada de IA, sem chamar a API: o material enviado e a forma da chamada.

Um cliente falso substitui a Claude API, por isso estes testes não gastam nada.
"""
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from dd_assistant import ai_memo
from dd_assistant.input_loader import load_input
from dd_assistant.metrics import compute_metrics
from dd_assistant.rules import RULES, alerts, evaluate

DATA = Path(__file__).resolve().parents[1] / "data"
TEMPLATE = DATA / "DD_template_modulo1.xlsx"
DATA_ROOM = DATA / "Duriva_data_room.xlsx"


class FakeStream:
    def __init__(self, chunks, stop_reason):
        self.text_stream = iter(chunks)
        self._msg = SimpleNamespace(
            stop_reason=stop_reason, model=ai_memo.MODEL,
            content=[SimpleNamespace(type="text", text="".join(chunks))],
            usage=SimpleNamespace(input_tokens=1000, output_tokens=500))

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get_final_message(self):
        return self._msg


class FakeClient:
    """Imita client.beta.messages.stream(...) e guarda os argumentos da chamada."""

    def __init__(self, chunks=("# Memo", "\n\ntexto"), stop_reason="end_turn"):
        self.kwargs = None
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self._stream))
        self._chunks, self._stop = list(chunks), stop_reason

    def _stream(self, **kwargs):
        self.kwargs = kwargs
        return FakeStream(self._chunks, self._stop)


class MaterialTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_input(TEMPLATE)
        cls.metrics = compute_metrics(cls.data)
        cls.results = evaluate(cls.data, cls.metrics)
        cls.material = ai_memo.build_material(cls.data, cls.metrics, cls.results, DATA_ROOM,
                                              reviews={"R13": ("Descartado", "Erro já corrigido pela empresa")})

    def test_every_alert_with_evidence(self):
        for r in alerts(self.results):
            self.assertIn(f"{r.rule.id} · {r.rule.name}", self.material)
            self.assertIn(r.evidence, self.material)

    def test_full_rule_catalog(self):
        for rule in RULES:
            self.assertIn(f"| {rule.id} | {rule.name} |", self.material)

    def test_data_room_text_with_cell_references(self):
        self.assertIn("### Folha 'Relatório de Gestão'", self.material)
        self.assertIn("A5: §2 Margens", self.material)
        self.assertIn("D5: 21400", self.material)       # DRE!D5: vendas de 2025

    def test_review_state_goes_to_the_ai(self):
        self.assertIn("Estado do revisor: Descartado — Erro já corrigido pela empresa", self.material)
        self.assertIn("Estado do revisor: Pendente", self.material)

    def test_never_the_answer_key(self):
        self.assertNotIn("gabarito", self.material.lower())


class CallTest(unittest.TestCase):
    def test_call_uses_model_prompt_and_effort(self):
        client = FakeClient()
        seen = []
        memo = ai_memo.write_memo("material", client=client, on_text=seen.append)
        self.assertEqual(memo.text, "# Memo\n\ntexto")
        self.assertEqual(seen, ["# Memo", "\n\ntexto"])
        kw = client.kwargs
        self.assertEqual(kw["model"], "claude-opus-5-5")
        self.assertEqual(kw["output_config"], {"effort": "high"})
        self.assertEqual(kw["fallbacks"], "default")
        self.assertEqual(kw["messages"], [{"role": "user", "content": "material"}])
        self.assertTrue(kw["system"].startswith("## Papel"))
        self.assertIn("Não fazes contas", kw["system"])
        self.assertIn("Não crias alertas", kw["system"])
        self.assertNotIn("temperature", kw)          # rejeitado pela API desde outubro de 2026
        self.assertAlmostEqual(memo.cost_usd, (1000 * 4 + 500 * 20) / 1e6)

    def test_refusal_raises(self):
        with self.assertRaises(ai_memo.MemoError):
            ai_memo.write_memo("material", client=FakeClient(stop_reason="refusal"))

    def test_missing_key_gives_clear_message(self):
        client = FakeClient()
        client.beta.messages.stream = mock.Mock(side_effect=TypeError(   # o que o SDK lança sem chave
            '"Could not resolve authentication method. Expected one of api_key, auth_token, or credentials"'))
        with self.assertRaises(ai_memo.MemoError) as ctx:
            ai_memo.write_memo("material", client=client)
        self.assertIn("ANTHROPIC_API_KEY", str(ctx.exception))

    def test_truncated_answer_is_flagged(self):
        memo = ai_memo.write_memo("material", client=FakeClient(stop_reason="max_tokens"))
        self.assertTrue(memo.truncated)


class EnvTest(unittest.TestCase):
    def test_load_env_reads_key_without_overriding(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = Path(tmp) / ".env"
            env.write_text("# comentário\nANTHROPIC_API_KEY=sk-teste\nOUTRA=\nJA_EXISTE=do_ficheiro\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {"JA_EXISTE": "do_ambiente"}, clear=False):
                os.environ.pop("ANTHROPIC_API_KEY", None)
                ai_memo.load_env(env)
                self.assertEqual(os.environ["ANTHROPIC_API_KEY"], "sk-teste")
                self.assertEqual(os.environ["JA_EXISTE"], "do_ambiente")   # o ambiente ganha ao ficheiro
                self.assertNotIn("OUTRA", os.environ)                     # valor vazio é ignorado


if __name__ == "__main__":
    unittest.main()
