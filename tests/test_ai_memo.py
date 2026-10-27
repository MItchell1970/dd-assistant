"""AI layer without calling the API: the material sent and the shape of the call.

A fake client replaces the Claude API, so these tests cost nothing.
"""
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from dd_assistant import ai_memo
from dd_assistant.extract import extract_excel
from dd_assistant.metrics import compute_metrics
from dd_assistant.rules import RULES, alerts, evaluate

DATA_ROOM = Path(__file__).resolve().parents[1] / "data" / "Duriva_data_room.xlsx"


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
    """Imitates client.beta.messages.stream(...) and records the call arguments."""

    def __init__(self, chunks=("# Memo", "\n\ntext"), stop_reason="end_turn"):
        self.kwargs = None
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self._stream))
        self._chunks, self._stop = list(chunks), stop_reason

    def _stream(self, **kwargs):
        self.kwargs = kwargs
        return FakeStream(self._chunks, self._stop)


class MaterialTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ext = extract_excel(DATA_ROOM, DATA_ROOM.name)
        cls.data = ext.data
        cls.metrics = compute_metrics(cls.data)
        cls.results = evaluate(cls.data, cls.metrics)
        cls.material = ai_memo.build_material(cls.data, cls.metrics, cls.results, ext.source_text,
                                              reviews={"R13": ("Dismissed", "Error already corrected by the company")})

    def test_every_finding_with_evidence(self):
        for r in alerts(self.results):
            self.assertIn(f"{r.rule.id} · {r.rule.name}", self.material)
            self.assertIn(r.evidence, self.material)

    def test_full_rule_catalogue(self):
        for rule in RULES:
            self.assertIn(f"| {rule.id} | {rule.name} |", self.material)

    def test_data_room_text_with_cell_references(self):
        self.assertIn("### Sheet 'Relatório de Gestão'", self.material)
        self.assertIn("A5: §2 Margens", self.material)
        self.assertIn("D5: 21400", self.material)       # DRE!D5: FY25 revenue

    def test_review_status_reaches_the_ai(self):
        self.assertIn("Reviewer status: Dismissed — Error already corrected by the company", self.material)
        self.assertIn("Reviewer status: Pending", self.material)

    def test_never_the_answer_key(self):
        self.assertNotIn("gabarito", self.material.lower())


class CallTest(unittest.TestCase):
    def test_call_uses_model_prompt_and_effort(self):
        client = FakeClient()
        seen = []
        memo = ai_memo.write_memo("material", client=client, on_text=seen.append)
        self.assertEqual(memo.text, "# Memo\n\ntext")
        self.assertEqual(seen, ["# Memo", "\n\ntext"])
        kw = client.kwargs
        self.assertEqual(kw["model"], "claude-opus-5-5")
        self.assertEqual(kw["output_config"], {"effort": "high"})
        self.assertEqual(kw["fallbacks"], "default")
        self.assertEqual(kw["messages"], [{"role": "user", "content": "material"}])
        self.assertTrue(kw["system"].startswith("## Role"))
        self.assertIn("No calculations", kw["system"])
        self.assertIn("No new findings", kw["system"])
        self.assertNotIn("temperature", kw)          # rejected by the API since October 2026
        self.assertAlmostEqual(memo.cost_usd, (1000 * 4 + 500 * 20) / 1e6)

    def test_refusal_raises(self):
        with self.assertRaises(ai_memo.MemoError):
            ai_memo.write_memo("material", client=FakeClient(stop_reason="refusal"))

    def test_missing_key_gives_clear_message(self):
        client = FakeClient()
        client.beta.messages.stream = mock.Mock(side_effect=TypeError(   # what the SDK raises without a key
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
            env.write_text("# comment\nANTHROPIC_API_KEY=sk-test\nOTHER=\nALREADY=from_file\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {"ALREADY": "from_env"}, clear=False):
                os.environ.pop("ANTHROPIC_API_KEY", None)
                ai_memo.load_env(env)
                self.assertEqual(os.environ["ANTHROPIC_API_KEY"], "sk-test")
                self.assertEqual(os.environ["ALREADY"], "from_env")    # the environment wins over the file
                self.assertNotIn("OTHER", os.environ)                   # empty values are ignored


if __name__ == "__main__":
    unittest.main()
