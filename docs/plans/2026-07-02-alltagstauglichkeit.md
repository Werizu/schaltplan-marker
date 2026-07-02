# Alltagstaugliche Bedienung – Implementierungsplan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** `schaltplan_marker.py` bekommt eine Doppelklick-GUI (Einzel- + Stapelverarbeitung), schreibt die Ausgabe gesammelt nach `Downloads/Schaltplan-Marker/<PDF>/`, erzeugt Deutsch-Excel-taugliche CSVs und wird als offline-Ordner an gesperrte Kollegen-PCs verteilbar.

**Architecture:** Eine Logik-Datei bleibt Kern (`extract/find_marks/draw_marks`). `process()` schreibt in einen festen Download-Unterordner. Neue `run_gui()` (tkinter, Bordmittel) ist der Doppelklick-Einstieg; `main()` verzweigt: Argumente → CLI, keine → GUI. Verteilung als Ordner mit mitgeliefertem PyMuPDF (`fitz/`+`pymupdf/`) und `.pyw`-Starter.

**Tech Stack:** Python 3.9+ (stdlib: `tkinter`, `csv`, `pathlib`, `argparse`), PyMuPDF (abi3-Wheel, offline mitgeliefert).

**Design:** siehe `docs/plans/2026-07-02-alltagstauglichkeit-design.md`.

**Testlauf-Referenz (Regression):** Beispiel-PDF muss weiterhin **1.501 Markierungen (129 A / 1.372 B)** ergeben.

**Konventionen:**
- Ausgeführt im Projektordner `~/Documents/01_Persönlich/05_Projekte/06_Schaltplan-Marker`.
- Python via `./.venv/bin/python` (Mac-Dev-Umgebung, PyMuPDF installiert).
- Tests sind eigenständige Assert-Skripte (kein pytest nötig), laufbar mit `./.venv/bin/python tests/<datei>.py`.
- Nach jeder Aufgabe committen. Entscheidungen ins Vault-`… – Entscheidungen.md` (separater Schritt am Ende).

---

## Task 1: Ausgabe-Ordner in Downloads

**Files:**
- Modify: `schaltplan_marker.py` (Funktion `process`, neue Helper `output_dir_for`)
- Test: `tests/test_output_dir.py`

**Step 1: Test schreiben** — `tests/test_output_dir.py`

```python
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from pathlib import Path
import schaltplan_marker as sm

def test_output_dir_liegt_in_downloads_unterordner():
    p = Path("/irgendwo/Plan Nord.pdf")
    d = sm.output_dir_for(p)
    assert d == Path.home() / "Downloads" / "Schaltplan-Marker" / "Plan Nord"

print("Test test_output_dir...")
test_output_dir_liegt_in_downloads_unterordner()
print("OK")
```

**Step 2: Test laufen lassen (muss scheitern)**

Run: `./.venv/bin/python tests/test_output_dir.py`
Expected: FAIL – `AttributeError: module 'schaltplan_marker' has no attribute 'output_dir_for'`

**Step 3: Implementieren** — in `schaltplan_marker.py` oberhalb von `process`:

```python
def output_dir_for(pdf_path: Path) -> Path:
    """Zielordner: ~/Downloads/Schaltplan-Marker/<PDF-Name>/ (wird angelegt)."""
    return Path.home() / "Downloads" / "Schaltplan-Marker" / pdf_path.stem
```

Und `process(...)` so anpassen, dass Ausgabe dorthin geht. Signatur:
`def process(inp, out_dir=None, two_colors=False, want_list=False):`
Kern:
```python
    inp = Path(inp)
    target = Path(out_dir) if out_dir else output_dir_for(inp)
    target.mkdir(parents=True, exist_ok=True)
    outp = target / f"{inp.stem}_markiert.pdf"
    ...
    doc.save(outp, deflate=True)
    ...
    csv_path = target / f"{inp.stem}_fundliste.csv"
```
`process` gibt am Ende ein Dict zurück: `return {"total": total, "pdf": outp, "csv": csv_path if want_list else None, "dir": target}`.
`main()` ruft `process(args.input, out_dir=args.output, ...)` (bei `-o` bekommt der User einen expliziten Ordner; sonst Downloads).

**Step 4: Test laufen lassen (muss bestehen)**

Run: `./.venv/bin/python tests/test_output_dir.py`
Expected: `OK`

**Step 5: Regression + Commit**

Run: `./.venv/bin/python schaltplan_marker.py ~/Downloads/plan.pdf --list`
Expected: `Gesamt 1501 Markierungen`, Ausgabe unter `~/Downloads/Schaltplan-Marker/plan/`
```bash
git add schaltplan_marker.py tests/test_output_dir.py
git commit -m "Ausgabe gesammelt nach Downloads/Schaltplan-Marker/<PDF>/"
```

---

## Task 2: CSV Deutsch-Excel-tauglich

**Files:**
- Modify: `schaltplan_marker.py` (CSV-Schreibteil in `process`)
- Test: `tests/test_csv_format.py`

**Step 1: Test schreiben** — `tests/test_csv_format.py`

```python
import sys, pathlib, tempfile, csv
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import schaltplan_marker as sm
from pathlib import Path

def test_csv_semikolon_bom_komma():
    rows = [(1, "A", 152.8, 85.4, "Goch Straße")]
    p = Path(tempfile.mktemp(suffix=".csv"))
    sm.write_fundliste(p, rows)
    raw = p.read_bytes()
    assert raw[:3] == b"\xef\xbb\xbf", "UTF-8 BOM fehlt"
    text = raw.decode("utf-8-sig")
    kopf, zeile = text.splitlines()[:2]
    assert kopf == "Seite;Fall;x;y;Station"
    assert zeile == "1;A;152,8;85,4;Goch Straße"

print("Test test_csv_format..."); test_csv_semikolon_bom_komma(); print("OK")
```

**Step 2: Test laufen lassen (muss scheitern)**

Run: `./.venv/bin/python tests/test_csv_format.py`
Expected: FAIL – `write_fundliste` existiert nicht.

**Step 3: Implementieren** — neue Funktion + Nutzung in `process`:

```python
def write_fundliste(csv_path, rows):
    """Schreibt die Fundliste Deutsch-Excel-tauglich: Semikolon, UTF-8-BOM, Dezimal-Komma."""
    import csv as _csv
    def de(v):
        return str(v).replace(".", ",") if isinstance(v, float) else v
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        wr = _csv.writer(f, delimiter=";")
        wr.writerow(["Seite", "Fall", "x", "y", "Station"])
        for seite, fall, x, y, station in rows:
            wr.writerow([seite, fall, de(x), de(y), station])
```
In `process` den bisherigen CSV-Block durch `write_fundliste(csv_path, list_rows)` ersetzen.
Sicherstellen, dass `x, y` als `float` in `list_rows` liegen (sind sie: `round(x,2)`).

**Step 4: Test laufen lassen (muss bestehen)**

Run: `./.venv/bin/python tests/test_csv_format.py`
Expected: `OK`

**Step 5: Commit**

```bash
git add schaltplan_marker.py tests/test_csv_format.py
git commit -m "CSV Deutsch-Excel-tauglich (Semikolon, UTF-8-BOM, Dezimal-Komma)"
```

---

## Task 3: GUI (run_gui) mit Einzel- und Ordnerauswahl

**Files:**
- Modify: `schaltplan_marker.py` (neue `run_gui`, Helper `_open_folder`, `_collect_pdfs`)
- Test: `tests/test_collect_pdfs.py` (nur die Logik, nicht das Fenster)

**Step 1: Test schreiben** — `tests/test_collect_pdfs.py`

```python
import sys, pathlib, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import schaltplan_marker as sm
from pathlib import Path

def test_collect_pdfs_findet_nur_pdf():
    d = Path(tempfile.mkdtemp())
    (d/"a.pdf").write_bytes(b"%PDF")
    (d/"b.PDF").write_bytes(b"%PDF")
    (d/"c.txt").write_text("x")
    got = sorted(p.name for p in sm._collect_pdfs(d))
    assert got == ["a.pdf", "b.PDF"], got

print("Test collect_pdfs..."); test_collect_pdfs_findet_nur_pdf(); print("OK")
```

**Step 2: Test laufen lassen (muss scheitern)**

Run: `./.venv/bin/python tests/test_collect_pdfs.py`
Expected: FAIL – `_collect_pdfs` fehlt.

**Step 3: Implementieren**

```python
def _collect_pdfs(folder):
    return [p for p in Path(folder).iterdir() if p.suffix.lower() == ".pdf"]

def _open_folder(path):
    import subprocess, os
    if sys.platform.startswith("win"):
        os.startfile(path)                       # noqa
    elif sys.platform == "darwin":
        subprocess.run(["open", str(path)])
    else:
        subprocess.run(["xdg-open", str(path)])

def run_gui():
    try:
        import tkinter as tk
        from tkinter import filedialog, ttk
    except Exception:
        print("Grafische Oberfläche (tkinter) nicht verfügbar.")
        print("Nutzung per Kommandozeile: python schaltplan_marker.py plan.pdf --list")
        input("Enter zum Schließen ...")
        return

    root = tk.Tk()
    root.title("Schaltplan-Marker")
    root.geometry("560x420")
    want_list = tk.BooleanVar(value=True)
    two_colors = tk.BooleanVar(value=False)
    last_dir = {"path": None}

    status = tk.Text(root, height=12, wrap="word")
    def log(msg):
        status.insert("end", msg + "\n"); status.see("end"); root.update_idletasks()

    def run_on(pdfs):
        pdfs = list(pdfs)
        if not pdfs:
            return
        for pdf in pdfs:
            try:
                res = process(pdf, two_colors=two_colors.get(), want_list=want_list.get())
                last_dir["path"] = res["dir"].parent
                log(f"{Path(pdf).name}  →  {res['total']} Kästen ✓")
            except Exception as e:
                log(f"{Path(pdf).name}  →  FEHLER: {e}")
        log("Fertig.")
        open_btn.configure(state="normal")

    def choose_files():
        files = filedialog.askopenfilenames(title="PDF(s) auswählen",
                                            filetypes=[("PDF", "*.pdf")])
        run_on(files)

    def choose_folder():
        folder = filedialog.askdirectory(title="Ordner mit PDFs wählen")
        if folder:
            run_on(_collect_pdfs(folder))

    ttk.Button(root, text="📄  Einzelne PDF(s) auswählen…", command=choose_files).pack(fill="x", padx=12, pady=(12, 4))
    ttk.Button(root, text="📁  Ganzen Ordner verarbeiten…", command=choose_folder).pack(fill="x", padx=12, pady=4)
    ttk.Checkbutton(root, text="Fundliste (CSV für Excel) erzeugen", variable=want_list).pack(anchor="w", padx=12)
    ttk.Checkbutton(root, text="Fall A / B in zwei Farben", variable=two_colors).pack(anchor="w", padx=12, pady=(0, 8))
    status.pack(fill="both", expand=True, padx=12, pady=4)
    open_btn = ttk.Button(root, text="Ausgabeordner öffnen", state="disabled",
                          command=lambda: last_dir["path"] and _open_folder(last_dir["path"]))
    open_btn.pack(fill="x", padx=12, pady=(4, 12))
    root.mainloop()
```

**Step 4: Test laufen lassen (muss bestehen)**

Run: `./.venv/bin/python tests/test_collect_pdfs.py`
Expected: `OK`

**Step 5: GUI manuell prüfen (Mac)**

Run: `./.venv/bin/python schaltplan_marker.py` (ohne Argumente)
Expected: Fenster öffnet; „Einzelne PDF(s)…" → Beispiel-PDF wählen → Statuszeile „…1501 Kästen ✓"; Ausgabe unter `~/Downloads/Schaltplan-Marker/plan/`; „Ausgabeordner öffnen" funktioniert.

**Step 6: Commit**

```bash
git add schaltplan_marker.py tests/test_collect_pdfs.py
git commit -m "GUI: Doppelklick-Fenster mit Einzel- und Ordnerauswahl"
```

---

## Task 4: main() – ohne Argumente die GUI starten

**Files:**
- Modify: `schaltplan_marker.py` (`main`)

**Step 1: Implementieren** — `main()` verzweigen:

```python
def main():
    if len(sys.argv) == 1:            # Doppelklick / ohne Parameter
        run_gui()
        return
    ap = argparse.ArgumentParser(description="Markiert Stromkästen in MS-Netz-Schaltplänen (Vektor-PDF).")
    ap.add_argument("input", type=Path)
    ap.add_argument("-o", "--output", type=Path, help="Ausgabe-ORDNER (Standard: Downloads/Schaltplan-Marker/<PDF>)")
    ap.add_argument("--two-colors", action="store_true")
    ap.add_argument("--list", action="store_true", dest="want_list")
    args = ap.parse_args()
    if not args.input.exists():
        sys.exit(f"Datei nicht gefunden: {args.input}")
    process(args.input, out_dir=args.output, two_colors=args.two_colors, want_list=args.want_list)
```

**Step 2: Prüfen (CLI unverändert, GUI bei Doppelklick)**

Run: `./.venv/bin/python schaltplan_marker.py ~/Downloads/plan.pdf --list`
Expected: `Gesamt 1501 Markierungen`
Run: `./.venv/bin/python schaltplan_marker.py`
Expected: Fenster öffnet.

**Step 3: Commit**

```bash
git add schaltplan_marker.py
git commit -m "main(): ohne Argumente GUI starten"
```

---

## Task 5: .pyw-Starter, LIESMICH, Verteil-Ordner (offline)

**Files:**
- Create: `Schaltplan-Marker starten.pyw`
- Create: `LIESMICH.txt`
- Create: `werkzeuge/bundle_windows.py` (baut den Verteil-Ordner aus einem Wheel)

**Step 1: `Schaltplan-Marker starten.pyw`**

```python
# Doppelklick-Starter (pythonw -> kein Konsolenfenster). Oeffnet die grafische Oberflaeche.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schaltplan_marker
schaltplan_marker.run_gui()
```

**Step 2: `LIESMICH.txt`**

```
Schaltplan-Marker
=================
Doppelklick auf "Schaltplan-Marker starten.pyw".
Im Fenster: PDF(s) oder einen Ordner waehlen.
Ergebnis erscheint in:  Downloads\Schaltplan-Marker\<PDF-Name>\
  - <PDF-Name>_markiert.pdf     (Plan mit roten Kreisen)
  - <PDF-Name>_fundliste.csv    (Liste, oeffnet in Excel)
Kein Internet, keine Installation noetig.
```

**Step 3: `werkzeuge/bundle_windows.py`** – erstellt den USB-fertigen Ordner:

```python
"""Baut den offline-Verteil-Ordner: Skripte + entpacktes PyMuPDF (fitz/ + pymupdf/).
Aufruf:  python werkzeuge/bundle_windows.py pfad/zum/pymupdf-...-win_amd64.whl
Ergebnis: dist/Schaltplan-Marker/ (auf USB kopierbar)."""
import sys, shutil, zipfile
from pathlib import Path

def main(whl):
    root = Path(__file__).resolve().parent.parent
    out = root / "dist" / "Schaltplan-Marker"
    if out.exists(): shutil.rmtree(out)
    out.mkdir(parents=True)
    for name in ["schaltplan_marker.py", "Schaltplan-Marker starten.pyw", "LIESMICH.txt"]:
        shutil.copy(root / name, out / name)
    with zipfile.ZipFile(whl) as z:
        for info in z.infolist():
            top = info.filename.split("/")[0]
            if top in ("fitz", "pymupdf"):
                z.extract(info, out)
    print("Fertig:", out)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Aufruf: python werkzeuge/bundle_windows.py <pymupdf-...-win_amd64.whl>")
    main(sys.argv[1])
```

**Step 4: Verteil-Ordner bauen und prüfen**

Run: `./.venv/bin/python werkzeuge/bundle_windows.py ~/Downloads/PyMuPDF_Windows_offline/pymupdf-1.28.0-cp310-abi3-win_amd64.whl`
Expected: `dist/Schaltplan-Marker/` enthält `schaltplan_marker.py`, `Schaltplan-Marker starten.pyw`, `LIESMICH.txt`, `fitz/`, `pymupdf/`.
Run: `ls dist/Schaltplan-Marker`

**Step 5: `.gitignore` um `dist/` ergänzen, dann Commit**

```bash
printf '\n# gebauter Verteil-Ordner\ndist/\n' >> .gitignore
git add "Schaltplan-Marker starten.pyw" LIESMICH.txt werkzeuge/bundle_windows.py .gitignore
git commit -m "Offline-Verteilung: .pyw-Starter + Bundle-Werkzeug + LIESMICH"
```

---

## Task 6: README aktualisieren, Abschluss-Regression, Doku/Memory

**Files:**
- Modify: `README.md`
- Modify (Vault): `projects/Schaltplan-Marker/Schaltplan-Marker – Entscheidungen.md`, `… – Code-Map.md`

**Step 1: README** – Abschnitt „Ohne Kommandozeile" ersetzen: GUI per Doppelklick (`.pyw`), Ausgabe in `Downloads/Schaltplan-Marker/<PDF>/`, Windows-Offline-Verteilung (Ordner kopieren, kein pip). Alte `.bat`/`.command`-Hinweise als „für Entwickler/Mac" kennzeichnen.

**Step 2: Abschluss-Regression**

Run: `./.venv/bin/python schaltplan_marker.py ~/Downloads/plan.pdf --list`
Expected: `Gesamt 1501 Markierungen`; CSV öffnet in Excel korrekt (Semikolon/Umlaute).
Run: alle Tests
```bash
for t in tests/test_*.py; do ./.venv/bin/python "$t"; done
```
Expected: jeweils `OK`.

**Step 3: Vault-Doku fortschreiben** – in `… – Entscheidungen.md` Eintrag 2026-07-02 (GUI + Downloads-Ausgabe + Excel-Fix + Offline-Verteilung, mit Warum). `… – Code-Map.md` um `run_gui`, `output_dir_for`, `write_fundliste`, `bundle_windows.py` ergänzen.

**Step 4: Commit**

```bash
git add README.md
git commit -m "README: GUI-Bedienung + Downloads-Ausgabe + Offline-Verteilung"
```

---

## Erledigt, wenn
- Doppelklick (Mac: `.venv`; Win: `.pyw`) öffnet das Fenster; Einzel- und Ordnerauswahl funktionieren.
- Ausgabe liegt unter `Downloads/Schaltplan-Marker/<PDF>/` (PDF + CSV).
- CSV öffnet in deutschem Excel sauber (Spalten, Umlaute).
- CLI-Regression: **1.501 Markierungen**; alle `tests/test_*.py` melden `OK`.
- `dist/Schaltplan-Marker/` ist offline lauffähig (mit `fitz/`+`pymupdf/`).
- Vault-Doku + Memory aktualisiert.
