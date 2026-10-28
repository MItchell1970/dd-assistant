"""The European market: the target's country, its accounting framework and its corporate tax rate.

The country is suggested from the company's legal form (S.G.P.S., Lda., S.L., SAS, GmbH, S.p.A., B.V.…),
its name and the language of the statements; the reviewer confirms it. It sets the statutory tax rate
for the effective tax rate test (R25) and tells the memo which accounting framework the figures follow.

Tax rates are headline rates for 2024, including the usual local surcharges, to test whether the
effective rate is plausible (a 10 pp tolerance); they are not a tax computation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .sectors import _norm


@dataclass(frozen=True)
class Country:
    code: str
    name: str
    framework: str
    tax_rate: float | None
    tax_note: str
    legal_forms: str = ""     # regex on the normalised company name
    words: tuple[str, ...] = ()   # words of the statements in the country's language


COUNTRIES = [
    Country("PT", "Portugal", "SNC (Sistema de Normalização Contabilística), or IFRS for listed groups", 0.225,
            "IRC 21% plus municipal surcharge up to 1.5% (IRC 20% from 2025; state surcharge on profits above €1.5m "
            "not included)", r"\bs g p s\b|\bsgps\b|\blda\b|\bunipessoal\b|\bportugal\b",
            ("vendas", "resultado liquido", "balanco", "fornecedores", "capital proprio", "exercicio")),
    Country("ES", "Spain", "PGC (Plan General de Contabilidad), or IFRS for listed groups", 0.25,
            "Impuesto sobre Sociedades 25%", r"\bs l\b|\bs l u\b|\bslu\b|\bespana\b|\bspain\b",
            ("ejercicio", "cifra de negocios", "patrimonio neto", "proveedores", "aprovisionamientos")),
    Country("FR", "France", "PCG (Plan Comptable Général), or IFRS for listed groups", 0.25,
            "Impôt sur les sociétés 25%", r"\bsas\b|\bsasu\b|\bsarl\b|\bsnc\b|\bfrance\b",
            ("chiffre d affaires", "capitaux propres", "fournisseurs", "exercice", "resultat d exploitation")),
    Country("DE", "Germany", "HGB (Handelsgesetzbuch), or IFRS for listed groups", 0.30,
            "Corporate income tax and solidarity surcharge 15.825% plus trade tax of about 14%",
            r"\bgmbh\b|\bag\b|\bkg\b|\bkgaa\b|\bdeutschland\b|\bgermany\b",
            ("umsatzerlose", "eigenkapital", "bilanz", "jahresuberschuss", "personalaufwand")),
    Country("IT", "Italy", "OIC (Codice civile, art. 2423 ff.), or IFRS for listed groups", 0.24,
            "IRES 24% (IRAP of 3.9% on a different base is not included)",
            r"\bs p a\b|\bspa\b|\bs r l\b|\bsrl\b|\bitalia\b|\bitaly\b",
            ("ricavi", "patrimonio netto", "esercizio", "fornitori", "conto economico")),
    Country("NL", "Netherlands", "Dutch GAAP (Titel 9 BW2), or IFRS for listed groups", 0.258,
            "Vennootschapsbelasting 25.8% (19% on the first €200k)", r"\bb v\b|\bbv\b|\bnederland\b|\bnetherlands\b",
            ("omzet", "eigen vermogen", "balans")),
    Country("BE", "Belgium", "Belgian GAAP, or IFRS for listed groups", 0.25, "Corporate income tax 25%",
            r"\bsprl\b|\bbvba\b|\bbelgique\b|\bbelgie\b|\bbelgium\b", ()),
    Country("IE", "Ireland", "FRS 102 (Irish GAAP), or IFRS", 0.125,
            "12.5% on trading income (15% minimum for large groups under Pillar Two)",
            r"\bdac\b|\bireland\b", ()),
    Country("AT", "Austria", "UGB (Unternehmensgesetzbuch), or IFRS for listed groups", 0.23, "Körperschaftsteuer 23%",
            r"\bges m b h\b|\bgesmbh\b|\bosterreich\b|\baustria\b", ()),
    Country("LU", "Luxembourg", "Lux GAAP, or IFRS", 0.2494,
            "Corporate income tax, solidarity surcharge and municipal business tax (Luxembourg City) 24.94%",
            r"\bs a r l\b|\bluxembourg\b", ()),
    Country("EU", "Other European country", "Local GAAP or IFRS", None, "No statutory rate set", "", ()),
]
COUNTRY_BY_CODE = {c.code: c for c in COUNTRIES}


def get(code: str | None) -> Country | None:
    return COUNTRY_BY_CODE.get(code or "")


def suggest(text: str, company: str = "") -> tuple[Country | None, str]:
    """The likely country of the target and why; None when nothing points to one. The reviewer confirms it."""
    name, body = f" {_norm(company)} ", f" {_norm(text)} "
    best, best_score, why = None, 0, ""
    for c in COUNTRIES:
        form = bool(c.legal_forms) and re.search(c.legal_forms, name)
        words = [w for w in c.words if f" {w} " in body]
        score = 3 * bool(form) + len(words)
        if score > best_score:
            reasons = ([f"legal form or name '{form.group(0).strip()}'"] if form else []) + \
                      ([f"statements in the local language ({', '.join(words[:3])})"] if words else [])
            best, best_score, why = c, score, "; ".join(reasons)
    return best, why
