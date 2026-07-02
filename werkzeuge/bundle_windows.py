"""Baut/aktualisiert den Export-Ordner: Skripte + mitgeliefertes PyMuPDF (fitz/ + pymupdf/).

Ergebnis: Export/Schaltplan-Marker/  (fertig zum Kopieren auf USB / Arbeits-PC).

Aufruf:
  python werkzeuge/bundle_windows.py <pymupdf-...-win_amd64.whl>   # kompletter (Neu-)Bau inkl. PyMuPDF
  python werkzeuge/bundle_windows.py                               # nur Code aktualisieren (PyMuPDF bleibt)

Die zweite Form ist der Alltag: nach Code-Änderungen die aktuellste Version in den Export
schieben, ohne das grosse PyMuPDF erneut zu entpacken.
"""
import sys, shutil, zipfile
from pathlib import Path

SCRIPTS = ["schaltplan_marker.py", "Schaltplan-Marker starten.pyw", "LIESMICH.txt"]


def export_dir(root: Path) -> Path:
    return root / "Export" / "Schaltplan-Marker"


def refresh_code(root: Path, out: Path):
    """Kopiert die aktuellen Skript-Dateien in den Export-Ordner."""
    out.mkdir(parents=True, exist_ok=True)
    for name in SCRIPTS:
        shutil.copy(root / name, out / name)


def extract_pymupdf(whl: str, out: Path):
    """Entpackt fitz/ und pymupdf/ aus dem Wheel in den Export-Ordner."""
    for pkg in ("fitz", "pymupdf"):
        shutil.rmtree(out / pkg, ignore_errors=True)
    with zipfile.ZipFile(whl) as z:
        for info in z.infolist():
            if info.filename.split("/")[0] in ("fitz", "pymupdf"):
                z.extract(info, out)


def main():
    root = Path(__file__).resolve().parent.parent
    out = export_dir(root)
    whl = sys.argv[1] if len(sys.argv) > 1 else None

    if whl:
        extract_pymupdf(whl, out)
    elif not (out / "fitz").exists() or not (out / "pymupdf").exists():
        sys.exit("PyMuPDF fehlt im Export. Erster Bau braucht das Wheel:\n"
                 "  python werkzeuge/bundle_windows.py <pymupdf-...-win_amd64.whl>")

    refresh_code(root, out)
    print("Export aktualisiert:", out)


if __name__ == "__main__":
    main()
