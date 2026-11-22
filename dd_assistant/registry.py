"""Find a listed company and its ESEF annual reports, from two free public registers.

  - GLEIF (https://api.gleif.org): the company's name gives its LEI, the 20-character identifier every EU issuer has;
  - filings.xbrl.org (XBRL International): the LEI gives the company's ESEF report packages, most recent first,
    with the country, the financial year and the size of each package.
The package is downloaded only when the user says so, to output/esef_cache/ (outside git), and its SHA-256 is
compared with the one filings.xbrl.org publishes. It is then read like an uploaded one (esef.py), within the same
.zip limits. No API key and no cost; nothing about the user is sent (a generic User-Agent, the search words only).
"""
from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from .esef import MAX_EXPANDED

GLEIF = "https://api.gleif.org/api/v1"
FILINGS = "https://filings.xbrl.org"
CACHE = Path(__file__).resolve().parent.parent / "output" / "esef_cache"
MAX_DOWNLOAD = MAX_EXPANDED              # a package is never larger compressed than expanded
AGENT = "DD-Assistant/1.0 (ESEF reader)"
LEI = re.compile(r"[A-Z0-9]{18}[0-9]{2}")
HOSTS = {"api.gleif.org", "filings.xbrl.org"}   # the only places the reader asks or downloads from
PERIOD = re.compile(r"\d{4}-\d{2}-\d{2}")
PACKAGE = re.compile(r"[\w.-]+\.(?:zip|xbri)", re.I)


class RegistryError(Exception):
    """A register could not be reached or did not answer as expected."""


class NotFound(RegistryError):
    """The register has no such record (HTTP 404): for filings.xbrl.org, a LEI with no ESEF report."""


def checked(url: str) -> str:
    """Only https on the two registers: a URL from a register's answer (a package, the next page) or a redirect that
    points anywhere else (another host, http, file://) is refused."""
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in HOSTS or parts.username or parts.port not in (None, 443):
        raise RegistryError(f"Refused: {url} is not on {' or '.join(sorted(HOSTS))} over https.")
    return url


class _SameHosts(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        checked(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(_SameHosts)


class Http:
    """The internet, through urllib, limited to the two registers. Tests pass a recorded one instead
    (tests/test_registry.py)."""

    def get(self, url: str, limit: int | None = None) -> bytes:
        checked(url)
        for attempt in range(4):         # a register that says 'too many requests' is asked again, politely
            try:
                return self._get(url, limit)
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    raise NotFound(url) from None
                if e.code in (429, 503) and attempt < 3:
                    wait = e.headers.get("Retry-After", "")
                    time.sleep(min(int(wait), 30) if wait.isdigit() else 5 * (attempt + 1))
                    continue
                raise RegistryError(f"{urllib.parse.urlsplit(url).netloc} answered {e.code} {e.reason}.") from None
            except OSError as e:   # URLError, timeouts
                raise RegistryError(f"Could not reach {urllib.parse.urlsplit(url).netloc}: {e}") from None
        raise RegistryError(f"{urllib.parse.urlsplit(url).netloc} kept answering 'too many requests'.")

    @staticmethod
    def _get(url: str, limit: int | None) -> bytes:
        req = urllib.request.Request(url, headers={"User-Agent": AGENT, "Accept": "application/vnd.api+json, */*"})
        with _OPENER.open(req, timeout=120) as r:
            size = int(r.headers.get("Content-Length") or 0)
            if limit and size > limit:
                raise RegistryError(f"{url} is {size / 1024 ** 2:,.0f} MB, above the {limit // 1024 ** 2} MB "
                                    "limit. Not downloaded.")
            body = r.read(limit + 1 if limit else -1)
        if limit and len(body) > limit:
            raise RegistryError(f"{url} is above the {limit // 1024 ** 2} MB limit. Not downloaded.")
        return body

    def size(self, url: str) -> int | None:
        req = urllib.request.Request(checked(url), headers={"User-Agent": AGENT}, method="HEAD")
        try:
            with _OPENER.open(req, timeout=30) as r:
                return int(r.headers.get("Content-Length") or 0) or None
        except (OSError, ValueError, RegistryError):
            return None


@dataclass
class Filing:
    lei: str
    company: str
    period_end: str            # '2025-12-31'
    country: str               # where it was filed: 'PT'
    url: str                   # the report package (.zip)
    sha256: str = ""           # as published by filings.xbrl.org
    errors: int = 0            # validation messages counted by filings.xbrl.org
    warnings: int = 0
    inconsistencies: int = 0   # calculation inconsistencies (a sum that does not add up in the tags)
    size: int | None = None    # bytes, from the server

    @property
    def year(self) -> int:
        return int(self.period_end[:4])

    @property
    def file_name(self) -> str:
        return Path(urllib.parse.urlsplit(self.url).path).name

    @property
    def label(self) -> str:
        size = f"{self.size / 1024 ** 2:,.1f} MB" if self.size else "size unknown"
        return f"{self.company} · FY{self.year} (year end {self.period_end}) · filed in {self.country} · {size}"


@dataclass
class Company:
    lei: str
    name: str
    filings: list[Filing] = field(default_factory=list)


def _json(http: Http, url: str) -> dict:
    try:
        return json.loads(http.get(url))
    except ValueError:
        raise RegistryError(f"Unexpected answer from {urllib.parse.urlsplit(url).netloc}.") from None


def leis_for(name: str, http: Http, limit: int = 10) -> list[tuple[str, str]]:
    """GLEIF: the legal entities whose name is closest to the words, best first: [(LEI, legal name)]."""
    url = f"{GLEIF}/fuzzycompletions?field=entity.legalName&q={urllib.parse.quote(name)}"
    out = []
    for d in _json(http, url).get("data", []):
        lei = (d.get("relationships", {}).get("lei-records", {}).get("data") or {}).get("id")
        if lei and lei not in dict(out):
            out.append((lei, d.get("attributes", {}).get("value", lei)))
    return out[:limit]


def filings(lei: str, http: Http, name: str = "", sizes: bool = True) -> list[Filing]:
    """filings.xbrl.org: the ESEF report packages of one LEI, the most recent financial year first."""
    out, url = [], f"{FILINGS}/api/entities/{lei}/filings"
    while url:
        try:
            page = _json(http, url)
        except NotFound:                 # not on filings.xbrl.org: no ESEF report there
            break
        for d in page.get("data", []):
            a = d.get("attributes", {})
            if not a.get("package_url") or "/ESEF/" not in a["package_url"]:
                continue
            url_ = urllib.parse.urljoin(FILINGS, a["package_url"])
            try:                         # the register's answer is data: a package elsewhere is not listed
                checked(url_)
            except RegistryError:
                continue
            if not PERIOD.fullmatch(a.get("period_end") or "") or not PACKAGE.fullmatch(Path(
                    urllib.parse.urlsplit(url_).path).name):
                continue
            out.append(Filing(lei, name or lei, a.get("period_end", ""), a.get("country", ""), url_,
                              a.get("sha256") or "",
                              a.get("error_count") or 0, a.get("warning_count") or 0,
                              a.get("inconsistency_count") or 0))
        url = page.get("links", {}).get("next")
        if url:
            try:
                checked(url)
            except RegistryError:        # a next page elsewhere: stop at the pages already read
                url = None
    out.sort(key=lambda f: (f.period_end, f.url), reverse=True)
    if sizes:
        for f in out:
            f.size = http.size(f.url)
    return out


def with_reports(leis: list[str], http: Http) -> dict[str, str]:
    """filings.xbrl.org, in one request: which of these LEIs have reports there -> {LEI: name}."""
    query = json.dumps([{"name": "identifier", "op": "in_", "val": leis}])
    page = _json(http, f"{FILINGS}/api/entities?filter={urllib.parse.quote(query)}")
    return {d["attributes"]["identifier"]: d["attributes"].get("name", "") for d in page.get("data", [])}


def search(query: str, http: Http | None = None, limit: int = 3, shown: int = 4) -> list[Company]:
    """A name or a LEI -> the companies with ESEF reports on filings.xbrl.org, best match first, each with its
    reports (the `shown` most recent with their size: one HEAD request each)."""
    http = http or Http()
    query = query.strip()
    if LEI.fullmatch(query.upper()):
        candidates = [(query.upper(), "")]
    else:
        candidates = leis_for(query, http)
    if not candidates:
        return []
    known = with_reports([lei for lei, _ in candidates], http)
    out = []
    for lei, name in candidates:
        if lei not in known:
            continue
        found = filings(lei, http, known[lei] or name, sizes=False)
        for f in found[:shown]:
            f.size = http.size(f.url)
        if found:
            out.append(Company(lei, known[lei] or name, found))
        if len(out) >= limit:
            break
    return out


@dataclass
class Download:
    path: Path
    sha256: str
    matches_register: bool | None     # None: filings.xbrl.org published no hash to compare
    cached: bool

    @property
    def note(self) -> str:
        return ("SHA-256 equal to the one published by filings.xbrl.org" if self.matches_register else
                "no SHA-256 published by filings.xbrl.org to compare")


def download(f: Filing, http: Http | None = None, cache: Path = CACHE) -> Download:
    """Download a report package to the cache (reused when already there and unchanged). A file whose SHA-256 differs
    from the one filings.xbrl.org publishes is not the report it lists (broken or altered): it is refused."""
    http = http or Http()
    checked(f.url)
    if not (LEI.fullmatch(f.lei) and PERIOD.fullmatch(f.period_end) and PACKAGE.fullmatch(f.file_name)):
        raise RegistryError(f"Refused: unexpected LEI, date or file name ({f.lei}, {f.period_end}, {f.file_name}).")
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / f"{f.lei}_{f.period_end}_{f.file_name}"
    if path.resolve().parent != cache.resolve():
        raise RegistryError(f"Refused: {path} is outside the cache folder.")
    expected = f.sha256.lower()
    if path.exists():
        body = path.read_bytes()
        digest = hashlib.sha256(body).hexdigest()
        if not expected or digest == expected:
            return Download(path, digest, digest == expected if expected else None, True)
        path.unlink()                    # a stale or broken copy: downloaded again
    body = http.get(f.url, limit=MAX_DOWNLOAD)
    digest = hashlib.sha256(body).hexdigest()
    if expected and digest != expected:
        raise RegistryError(f"The file downloaded from {f.url} has SHA-256 {digest}, not the {expected} published by "
                            "filings.xbrl.org: it is not the report listed there. Not used.")
    path.write_bytes(body)
    return Download(path, digest, True if expected else None, False)
