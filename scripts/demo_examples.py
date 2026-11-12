"""Regenerate the stored outputs of the demo: for each company, the databook (recalculated by Excel when this PC has
it) and the result of the memo check, in docs/examples/<company>/. The memos themselves are written by Claude Code
(the due-diligence skill, no API) and are not touched here.

Run from the project folder:  python scripts\\demo_examples.py
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dd_assistant.__main__ import main  # noqa: E402
from dd_assistant.demo import CASES  # noqa: E402


def slides(case) -> None:
    """The Red Flag Report in PowerPoint, and its PDF when this PC has PowerPoint."""
    import subprocess

    from dd_assistant import demo
    from dd_assistant.slides import write_slides
    write_slides(demo.analysis(case), case.slides_path, case.company, case.pages)
    try:
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                        str(ROOT / "scripts" / "slides_export.ps1"), str(case.slides_path)], check=True, timeout=300,
                       capture_output=True)
        print(f"Slides: {case.slides_path.name} and PDF")
    except (OSError, subprocess.SubprocessError):
        print(f"Slides: {case.slides_path.name} (no PDF: PowerPoint not available)")


def run() -> int:
    worst = 0
    for case in CASES:
        print(f"\n=== {case.company}")
        with tempfile.TemporaryDirectory() as tmp:
            args = [str(case.path), "--country", case.country, "--sector", case.sector, "--purpose", case.purpose,
                    "--databook", "--out", tmp]
            if case.prior:
                args += ["--prior", str(case.path.parent / case.prior)]
            if case.notes and (case.path.parent / "notes" / case.notes).exists():
                args += ["--notes", str(case.path.parent / "notes" / case.notes)]
            if case.memo_path.exists():
                args += ["--check-memo", str(case.memo_path)]
            rc = main(args)
            worst = max(worst, rc)
            case.folder.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(Path(tmp) / f"{case.path.stem}_databook.xlsx", case.databook_path)
            if case.memo_path.exists():
                shutil.copyfile(Path(tmp) / f"{case.memo_path.stem}_check.md", case.check_path)
        slides(case)
    return worst


if __name__ == "__main__":
    sys.exit(run())
