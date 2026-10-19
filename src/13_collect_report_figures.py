"""Step 13 (packaging): copy the report figures into report/figures_final and write a manifest.

Reads  : docs/REPORT_INPUTS.md ("Figure list" table: file, caption, report subsection)
Writes : report/figures_final/<same file names>, report/figures_final/MANIFEST.csv and MANIFEST.md
Figures are copied unchanged from the path listed (outputs/final/figures, or outputs/figures for the
src/05b validation figures). Fails if a listed file is missing or two files share a name.
Usage: python src/13_collect_report_figures.py
"""
import hashlib
import shutil
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as C  # noqa: E402

SRC_DOC = C.ROOT / "docs" / "REPORT_INPUTS.md"
DEST = C.ROOT / "report" / "figures_final"


def figure_table() -> pd.DataFrame:
    lines = SRC_DOC.read_text().splitlines()
    i = lines.index("## Figure list")
    rows = [l for l in lines[i + 1:] if l.startswith("|")]
    head = [c.strip() for c in rows[0].strip("|").split("|")]
    body = [[c.strip() for c in r.strip("|").split("|")] for r in rows[2:]]
    df = pd.DataFrame(body, columns=head)
    assert {"file", "caption", "report subsection"} <= set(df.columns), f"unexpected columns {head}"
    return df


def main() -> None:
    df = figure_table()
    names = df.file.map(lambda f: Path(f).name)
    assert not names.duplicated().any(), f"duplicate file names: {names[names.duplicated()].tolist()}"
    missing = [f for f in df.file if not (C.ROOT / f).exists()]
    assert not missing, f"listed figures missing: {missing}"
    if DEST.exists():
        for old in DEST.iterdir():          # only files this script wrote before
            if old.suffix in (".png", ".csv", ".md"):
                old.unlink()
    DEST.mkdir(parents=True, exist_ok=True)
    rows = []
    for r in df.itertuples():
        src = C.ROOT / r.file
        dst = DEST / src.name
        shutil.copy2(src, dst)
        h = hashlib.sha256(dst.read_bytes()).hexdigest()
        assert h == hashlib.sha256(src.read_bytes()).hexdigest()
        rows.append({"file": src.name, "report_subsection": getattr(r, "_3"), "caption": r.caption,
                     "copied_from": r.file, "sha256": h})
    man = pd.DataFrame(rows).sort_values(["report_subsection", "file"])
    man.to_csv(DEST / "MANIFEST.csv", index=False)
    md = ["# Report figures (copied unchanged by src/13_collect_report_figures.py from the paths in docs/REPORT_INPUTS.md)", "",
          "| subsection | file | caption | copied from |", "|---|---|---|---|"]
    md += [f"| {r.report_subsection} | {r.file} | {r.caption} | {r.copied_from} |" for r in man.itertuples()]
    (DEST / "MANIFEST.md").write_text("\n".join(md) + "\n")
    print(f"Copied {len(man)} figures to {DEST.relative_to(C.ROOT)}; manifest MANIFEST.csv / MANIFEST.md")
    print(man[["report_subsection", "file", "copied_from"]].to_string(index=False))


if __name__ == "__main__":
    main()
