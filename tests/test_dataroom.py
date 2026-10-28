"""The data room as the seller sends it: several Excel files, PDFs and Word documents at once."""
import io
import unittest
import zipfile
from pathlib import Path

from dd_assistant.dataroom import NeedsPdfReading, files_in, read_data_room
from dd_assistant.extract import ExtractionError, extract_excel
from dd_assistant.metrics import compute_metrics
from dd_assistant.rules import alerts, evaluate

DATA = Path(__file__).resolve().parents[1] / "data"
FOLDER = DATA / "Duriva_data_room"


def _docx(text: str) -> bytes:
    """A minimal Word document."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/'
                   'package/2006/content-types"><Default Extension="xml" ContentType="application/xml"/></Types>')
        z.writestr("word/document.xml", '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/'
                   f'2006/main"><w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>')
    return buf.getvalue()


def _filled(values: dict) -> dict:
    return {y: v for y, v in values.items() if v is not None}


class FolderTest(unittest.TestCase):
    """Duriva's data room in five documents (scripts/duriva_folder.py) against the single workbook."""

    @classmethod
    def setUpClass(cls):
        cls.ext = read_data_room(files_in([FOLDER]))
        cls.one = extract_excel(DATA / "Duriva_data_room.xlsx")

    def test_same_figures_and_findings_as_one_workbook(self):
        a, b = self.ext.data, self.one.data
        for key in b.lines:
            self.assertEqual(_filled(a.lines.get(key, {})), _filled(b.lines[key]), key)
        self.assertEqual([(c.name, _filled(c.values)) for c in a.clients], [(c.name, _filled(c.values)) for c in b.clients])
        ids = lambda d: [r.rule.id for r in alerts(evaluate(d, compute_metrics(d)))]
        self.assertEqual(ids(a), ids(b))

    def test_every_figure_names_its_file_and_cell(self):
        self.assertEqual(self.ext.data.sources["vendas"], "01 Demonstrações financeiras 2023-2025.xlsx › DRE!B5:D5")
        self.assertTrue(self.ext.data.clients_source.startswith("02 Vendas por cliente.xlsx › "))
        self.assertEqual(self.ext.company, "Duriva Distribuição Industrial, S.A.")

    def test_the_management_report_pdf_goes_to_the_memo(self):
        self.assertIn("## Document '05 Relatório de gestão 2025.pdf'", self.ext.source_text)
        self.assertIn("§2 Margens", self.ext.source_text)
        self.assertEqual(len(self.ext.files), 5)


class DocumentsTest(unittest.TestCase):
    def setUp(self):
        self.statements = (DATA / "Duriva_data_room.xlsx").read_bytes()

    def test_word_and_text_documents_tick_the_checklist(self):
        ext = read_data_room([("Duriva.xlsx", self.statements),
                              ("Contrato de financiamento - Banco A.docx", _docx("Cláusula 12.ª — covenants")),
                              ("Antiguidade de saldos de clientes 2025.txt", "Cliente A: 1.200 a 90 dias".encode()),
                              ("logo.png", b"\x89PNG")])
        received = dict(ext.data.documents)
        self.assertTrue(received["Facility agreements"])
        self.assertTrue(received["AR ageing"])
        self.assertFalse(received["Inventory ageing"])
        self.assertIn("Cláusula 12.ª", ext.source_text)
        self.assertEqual(ext.files[-1], {"File": "logo.png", "Read as": "Not read", "Found": "format not supported"})

    def test_statements_only_in_a_pdf_need_claude(self):
        pdf = (FOLDER / "05 Relatório de gestão 2025.pdf").read_bytes()
        with self.assertRaises(NeedsPdfReading) as e:
            read_data_room([("Contas 2025.pdf", pdf)])
        self.assertEqual(e.exception.pdfs, ["Contas 2025.pdf"])

    def test_a_template_goes_on_its_own(self):
        template = (DATA / "DD_template_modulo1.xlsx").read_bytes()
        with self.assertRaises(ExtractionError):
            read_data_room([("DD_template_modulo1.xlsx", template), ("Duriva.xlsx", self.statements)])
        self.assertIn("template", read_data_room([("DD_template_modulo1.xlsx", template)]).method)


if __name__ == "__main__":
    unittest.main()
