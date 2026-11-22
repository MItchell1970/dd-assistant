"""Finding a listed company and downloading its ESEF report, without the internet.

The register answers are recorded in tests/fixtures/registry/ (real answers of GLEIF and filings.xbrl.org for
'Jeronimo Martins', 22 November 2026). The package itself is the small one written by tests/test_esef.py, so the
download, the hash check and the analysis run end to end with no network call: any other URL fails the test.
"""
import hashlib
import io
import json
import tempfile
import unittest
import urllib.error
import urllib.parse
from pathlib import Path
from unittest import mock

from dd_assistant import registry
from dd_assistant.dataroom import read_data_room
from dd_assistant.pipeline import analyse
from tests.test_esef import package

FIXTURES = Path(__file__).parent / "fixtures" / "registry"
JM = "259400A8SZP10GB5IB19"


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


class RecordedHttp(registry.Http):
    """The registers as recorded; a package served from memory. Anything else is an error, never the internet."""

    def __init__(self, packages: dict[str, bytes] | None = None, gleif: bytes | None = None):
        self.packages, self.gleif, self.calls = packages or {}, gleif, []

    def get(self, url: str, limit: int | None = None) -> bytes:
        self.calls.append(url)
        if url.startswith(registry.GLEIF + "/fuzzycompletions"):
            return self.gleif or fixture("gleif_fuzzy_jeronimo_martins.json")
        if url.startswith(registry.FILINGS + "/api/entities?filter="):
            wanted = json.loads(urllib.parse.unquote(url.split("filter=", 1)[1]))[0]["val"]
            known = json.loads(fixture("filings_entities_jeronimo_martins.json"))
            known["data"] = [d for d in known["data"] if d["attributes"]["identifier"] in wanted]
            return json.dumps(known).encode()
        if url == f"{registry.FILINGS}/api/entities/{JM}/filings":
            return fixture(f"filings_{JM}.json")
        if url.startswith(f"{registry.FILINGS}/api/entities/"):
            raise registry.NotFound(url)
        if url in self.packages:
            return self.packages[url]
        raise AssertionError(f"unexpected request: {url}")

    def size(self, url: str) -> int | None:
        self.calls.append("HEAD " + url)
        return 10_246_434


class SearchTest(unittest.TestCase):
    def test_a_name_gives_the_company_and_its_reports_most_recent_first(self):
        http = RecordedHttp()
        found = registry.search("Jeronimo Martins", http)
        self.assertEqual([(c.lei, c.name) for c in found], [(JM, "JERÓNIMO MARTINS SGPS SA")])
        reports = found[0].filings
        self.assertEqual([f.year for f in reports], [2025, 2024, 2023, 2022, 2021])
        latest = reports[0]
        self.assertEqual((latest.country, latest.period_end, latest.size), ("PT", "2025-12-31", 10_246_434))
        self.assertEqual(latest.url, f"https://filings.xbrl.org/{JM}/2025-12-31/ESEF/PT/0/000320-2025-12-31.zip")
        self.assertEqual(latest.sha256, "ba97d24735db035c3d947e263316f651e1bc783f54c78d23b0151010d624f911")
        self.assertIn("FY2025 (year end 2025-12-31) · filed in PT · 9.8 MB", latest.label)
        # one request asks filings.xbrl.org which of GLEIF's five candidates have reports (it rate-limits)
        self.assertEqual(sum("/api/entities?filter=" in c for c in http.calls), 1)
        self.assertEqual(sum(c.startswith("HEAD") for c in http.calls), 4)   # sizes of the 4 most recent only

    def test_a_lei_skips_gleif(self):
        http = RecordedHttp()
        found = registry.search(JM.lower(), http)
        self.assertEqual(found[0].lei, JM)
        self.assertFalse(any(c.startswith(registry.GLEIF) for c in http.calls))

    def test_no_report_on_filings_xbrl_org(self):
        gleif = json.dumps({"data": [{"attributes": {"value": "SIEMENS AKTIENGESELLSCHAFT"}, "relationships": {
            "lei-records": {"data": {"id": "W38RGI023J3WT1HWRP32"}}}}]}).encode()
        self.assertEqual(registry.search("Siemens", RecordedHttp(gleif=gleif)), [])
        self.assertEqual(registry.search("W38RGI023J3WT1HWRP32", RecordedHttp()), [])


class DownloadTest(unittest.TestCase):
    def setUp(self):
        self.zip = package()
        self.cache = Path(tempfile.mkdtemp())
        self.filing = registry.Filing(JM, "Acme Energia", "2025-12-31", "PT", "https://filings.xbrl.org/acme.zip",
                                      hashlib.sha256(self.zip).hexdigest())

    def test_downloaded_once_checked_against_the_published_hash(self):
        http = RecordedHttp({self.filing.url: self.zip})
        got = registry.download(self.filing, http, self.cache)
        self.assertEqual((got.matches_register, got.cached, got.sha256), (True, False, self.filing.sha256))
        self.assertEqual(got.path.parent, self.cache)
        again = registry.download(self.filing, http, self.cache)
        self.assertTrue(again.cached)
        self.assertEqual(http.calls.count(self.filing.url), 1)

    def test_a_different_file_is_refused(self):
        http = RecordedHttp({self.filing.url: self.zip + b"changed"})
        with self.assertRaisesRegex(registry.RegistryError, "not the report listed there"):
            registry.download(self.filing, http, self.cache)
        self.assertEqual(list(self.cache.iterdir()), [])

    def test_the_download_gives_today_s_numbers(self):
        got = registry.download(self.filing, RecordedHttp({self.filing.url: self.zip}), self.cache)
        ext = read_data_room([(got.path.name, got.path.read_bytes())])
        a = analyse(ext)
        self.assertEqual((a.data.v("vendas", 2025), a.data.v("opinc", 2025)), (10040, 1540))
        self.assertTrue(a.checks_ok)
        self.assertEqual(a.quality.headline, "Notes missing: borrowings, provisions, leases, related parties, "
                                             "other income, segments")

    def test_a_package_above_the_limit_is_not_downloaded(self):
        class Big(io.BytesIO):
            headers = {"Content-Length": str(registry.MAX_DOWNLOAD + 1)}

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        with mock.patch("urllib.request.urlopen", return_value=Big(b"x")):
            with self.assertRaisesRegex(registry.RegistryError, "above the 300 MB limit"):
                registry.Http().get("https://filings.xbrl.org/big.zip", limit=registry.MAX_DOWNLOAD)

    def test_too_many_requests_is_asked_again(self):
        busy = urllib.error.HTTPError("u", 429, "Too Many Requests", {"Retry-After": "1"}, None)
        with mock.patch.object(registry.Http, "_get", side_effect=[busy, b"{}"]), mock.patch("time.sleep") as wait:
            self.assertEqual(registry.Http().get("https://filings.xbrl.org/api/x"), b"{}")
        wait.assert_called_once_with(1)


if __name__ == "__main__":
    unittest.main()
