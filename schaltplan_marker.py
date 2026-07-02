#!/usr/bin/env python3
"""
schaltplan_marker.py — Automatische Markierung von Stromkästen in MS-Netz-Schaltplänen (Vektor-PDF).

Erkennt in einem Netz-Schaltplan (Vektor-PDF, z. B. 10-kV-Mittelspannung) über alle Farb-Layer:
  - Stromkasten   = kleines Quadrat mit Diagonale(n)  (⊠)
  - Raute         = gefülltes Diamant-Symbol          (◆)
  - Verdickung    = kurzer dicker Balken auf der Linie direkt am Kasten
  - Abzweig-Raute = Raute, an der >=2 Linienrichtungen zusammenlaufen (T-/Kreuzungspunkt)

Markiert (roter Kreis um den Stromkasten):
  Fall A  – Kasten mit direkt anliegender Abzweig-Raute (2 Linien)
  Fall B  – Kasten, bei dem die Linie kurz davor dicker wird (ein- oder beidseitig)

Nutzung:
  python schaltplan_marker.py input.pdf                     -> input_markiert.pdf
  python schaltplan_marker.py input.pdf -o out.pdf --list   -> zusätzlich Fundliste (CSV)
  python schaltplan_marker.py input.pdf --two-colors        -> Fall A / Fall B in zwei Farben
"""
from __future__ import annotations
import argparse, json, math, sys, collections
from pathlib import Path

__version__ = "1.2.0"

# GitHub-Repo für Update-Prüfung (nur lesende HTTPS-Zugriffe, kein pip nötig).
GITHUB_REPO = "Werizu/schaltplan-marker"
UPDATE_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
UPDATE_RAW_BASE = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/"
UPDATE_FILES = ["schaltplan_marker.py", "plan_vergleich.py"]   # Auto-Update holt beide

# UTF-8-Ausgabe erzwingen, damit Umlaute auch in der Windows-Konsole (cp1252) funktionieren.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    import fitz  # PyMuPDF
except ImportError:
    sys.exit("PyMuPDF fehlt. Installieren mit:  pip install pymupdf")


# --------------------------------------------------------------------------- #
# Konfiguration – auf das CAD-Export-Format dieser Netzpläne abgestimmt.
# Bei anderer Zeichnungs-Skalierung ggf. GEOM_* über die Skalierung anpassen.
# --------------------------------------------------------------------------- #

# Gesättigte Netz-Layer-Farben (RGB 0..1). Weiß/Grau werden bewusst ignoriert
# (Hintergrund-Rechtecke, keine Symbole).
NETWORK_COLORS = [
    (0.00, 0.00, 1.00),   # blau
    (0.00, 1.00, 1.00),   # cyan
    (0.86, 0.59, 0.20),   # ocker
    (1.00, 0.00, 0.50),   # magenta
    (0.25, 0.56, 1.00),   # hellblau
    (1.00, 0.47, 0.00),   # orange
    (0.00, 1.00, 0.00),   # grün
    (0.79, 0.00, 0.90),   # lila
    (0.00, 0.54, 0.38),   # dunkelgrün
    (1.00, 0.00, 0.00),   # rot
    (0.05, 0.05, 0.05),   # fast schwarz
    (0.00, 0.00, 0.00),   # schwarz
    (0.80, 0.80, 0.00),   # oliv
]
COLOR_TOL = 0.12          # max. Farbabstand für Layer-Zuordnung

# Geometrie-Schwellen (Punkte) – gelten für das übliche Export-Format.
G = dict(
    box_min=0.07, box_max=0.20,        # Kantenlänge Stromkasten-Quadrat
    raute_min=0.08, raute_max=0.22,    # Raute (quadratische Bounding-Box)
    raute_aspect=1.5,                  # max. Seitenverhältnis für "quadratisch"
    bar_max=0.22, bar_thin_min=0.012,  # Verdickungs-Balken (langgestreckt)
    bar_thin_max=0.06, bar_aspect=1.8, # min. Seitenverhältnis für "langgestreckt"
    dedup=0.02,                        # Zusammenfassen fast gleicher Punkte
    branch_radius=0.06,                # Suchradius Linien an einer Raute
    branch_angle_tol=20.0,             # Winkel-Toleranz für gleiche Richtung (Grad)
    assoc_radius=0.35,                 # max. Abstand Symbol -> Stromkasten
)

# Markierungs-Stil
CIRCLE_RADIUS = 0.33
CIRCLE_WIDTH = 0.055
COLOR_BOTH = (1, 0, 0)        # rot – beide Fälle
COLOR_A = (1, 0, 0)           # bei --two-colors: Fall A
COLOR_B = (0, 0.5, 1)         # bei --two-colors: Fall B


# --------------------------------------------------------------------------- #
# Geometrie-Helfer
# --------------------------------------------------------------------------- #
def _dist_point_seg(px, py, x0, y0, x1, y1):
    dx, dy = x1 - x0, y1 - y0
    l2 = dx * dx + dy * dy
    if l2 == 0:
        return math.hypot(px - x0, py - y0)
    t = max(0.0, min(1.0, ((px - x0) * dx + (py - y0) * dy) / l2))
    return math.hypot(px - (x0 + t * dx), py - (y0 + t * dy))


def _dedup(points, tol):
    out = []
    for c in points:
        if not any(abs(c[0] - o[0]) < tol and abs(c[1] - o[1]) < tol for o in out):
            out.append(c)
    return out


class _Grid:
    """Einfaches räumliches Raster für schnelle Nachbarschaftssuche."""
    def __init__(self, cell=0.5):
        self.cell = cell
        self.d = collections.defaultdict(list)

    def add_seg(self, seg):
        x0, y0, x1, y1 = seg
        keys = {(int(x0 / self.cell), int(y0 / self.cell)),
                (int(x1 / self.cell), int(y1 / self.cell)),
                (int((x0 + x1) / 2 / self.cell), int((y0 + y1) / 2 / self.cell))}
        for k in keys:
            self.d[k].append(seg)

    def add_point(self, idx, pt):
        self.d[(int(pt[0] / self.cell), int(pt[1] / self.cell))].append(idx)

    def around(self, px, py):
        ci, cj = int(px / self.cell), int(py / self.cell)
        for a in range(ci - 1, ci + 2):
            for b in range(cj - 1, cj + 2):
                yield from self.d[(a, b)]


# --------------------------------------------------------------------------- #
# Extraktion
# --------------------------------------------------------------------------- #
def _classify_color(c):
    if c is None:
        return None
    best, bd = None, COLOR_TOL
    for i, n in enumerate(NETWORK_COLORS):
        dd = math.sqrt(sum((c[k] - n[k]) ** 2 for k in range(3)))
        if dd < bd:
            bd, best = dd, i
    return best


def extract(page):
    """Zerlegt die Seite je Farb-Layer in boxes / rauten / verdickungen / segmente."""
    n = len(NETWORK_COLORS)
    boxes = [[] for _ in range(n)]
    rauten = [[] for _ in range(n)]
    thick = [[] for _ in range(n)]
    segs = [[] for _ in range(n)]

    for path in page.get_drawings():
        items, bb, t = path["items"], path["rect"], path["type"]
        w, h = bb.width, bb.height
        mx, mn = max(w, h), min(w, h)

        if t == "s":
            ci = _classify_color(path.get("color"))
            if ci is None:
                continue
            is_box = (any(it[0] == "qu" for it in items)
                      and G["box_min"] < w < G["box_max"]
                      and G["box_min"] < h < G["box_max"])
            if is_box:
                boxes[ci].append((bb.x0 + w / 2, bb.y0 + h / 2))
            else:
                for it in items:                       # Kabel-Linien einsammeln
                    if it[0] == "l":
                        segs[ci].append((it[1].x, it[1].y, it[2].x, it[2].y))
                    elif it[0] == "qu":
                        q = it[1]
                        pts = [q.ul, q.ur, q.lr, q.ll]
                        for i in range(4):
                            a, b = pts[i], pts[(i + 1) % 4]
                            segs[ci].append((a.x, a.y, b.x, b.y))

        elif t == "f":
            ci = _classify_color(path.get("fill"))
            if ci is None:
                continue
            if G["raute_min"] < mn and mx < G["raute_max"] and mx / mn < G["raute_aspect"]:
                rauten[ci].append((bb.x0 + w / 2, bb.y0 + h / 2))          # quadratisch = Raute
            elif (G["bar_thin_min"] < mn < G["bar_thin_max"]
                  and 0.06 < mx < G["bar_max"] and mx / mn >= G["bar_aspect"]):
                thick[ci].append((bb.x0 + w / 2, bb.y0 + h / 2))           # langgestreckt = Verdickung

    for ci in range(n):
        boxes[ci] = _dedup(boxes[ci], G["dedup"])
        rauten[ci] = _dedup(rauten[ci], G["dedup"])
        thick[ci] = _dedup(thick[ci], G["dedup"])
    return boxes, rauten, thick, segs


# --------------------------------------------------------------------------- #
# Analyse
# --------------------------------------------------------------------------- #
def _direction_count(grid, px, py):
    """Anzahl unterschiedlicher Linienrichtungen an einem Punkt (1 = durchlaufend, >=2 = Abzweig)."""
    angles = []
    seen = set()
    for seg in grid.around(px, py):
        if seg in seen:
            continue
        seen.add(seg)
        if _dist_point_seg(px, py, *seg) < G["branch_radius"]:
            x0, y0, x1, y1 = seg
            if math.hypot(x1 - x0, y1 - y0) < 0.02:
                continue
            angles.append(math.degrees(math.atan2(y1 - y0, x1 - x0)) % 180)
    clusters = []
    for a in sorted(angles):
        if not any(min(abs(a - c), 180 - abs(a - c)) < G["branch_angle_tol"] for c in clusters):
            clusters.append(a)
    return len(clusters)


def _nearest_box(bgrid, boxes, px, py):
    best, bd = None, G["assoc_radius"]
    for i in bgrid.around(px, py):
        d = math.hypot(px - boxes[i][0], py - boxes[i][1])
        if d < bd:
            bd, best = d, i
    return best


def find_marks(boxes, rauten, thick, segs):
    """Liefert Listen von (x,y)-Kästen für Fall A und Fall B (über alle Layer)."""
    caseA, caseB = [], []
    for ci in range(len(NETWORK_COLORS)):
        if not boxes[ci]:
            continue
        seg_grid = _Grid()
        for s in segs[ci]:
            seg_grid.add_seg(tuple(s))
        box_grid = _Grid()
        for i, b in enumerate(boxes[ci]):
            box_grid.add_point(i, b)

        markedA, markedB = set(), set()
        for (x, y) in rauten[ci]:                     # Fall A: Abzweig-Raute am Kasten
            if _direction_count(seg_grid, x, y) >= 2:
                bi = _nearest_box(box_grid, boxes[ci], x, y)
                if bi is not None:
                    markedA.add(bi)
        for (x, y) in thick[ci]:                      # Fall B: Verdickung am Kasten
            bi = _nearest_box(box_grid, boxes[ci], x, y)
            if bi is not None:
                markedB.add(bi)

        caseA += [boxes[ci][i] for i in markedA]
        caseB += [boxes[ci][i] for i in markedB - markedA]
    return caseA, caseB


# --------------------------------------------------------------------------- #
# Ausgabe
# --------------------------------------------------------------------------- #
def draw_marks(page, caseA, caseB, two_colors):
    if two_colors:
        for pts, col in ((caseA, COLOR_A), (caseB, COLOR_B)):
            sh = page.new_shape()
            for (x, y) in pts:
                sh.draw_circle(fitz.Point(x, y), CIRCLE_RADIUS)
            sh.finish(color=col, width=CIRCLE_WIDTH)
            sh.commit()
    else:
        sh = page.new_shape()
        for (x, y) in caseA + caseB:
            sh.draw_circle(fitz.Point(x, y), CIRCLE_RADIUS)
        sh.finish(color=COLOR_BOTH, width=CIRCLE_WIDTH)
        sh.commit()


def nearest_label(words, x, y, max_dx=4.0, max_dy=1.2):
    """Best-effort-Stationsname: Wörter nahe des Kastens zu einer Zeile zusammenfassen."""
    near = [w for w in words
            if -0.5 < (w[0] + w[2]) / 2 - x < max_dx and abs((w[1] + w[3]) / 2 - y) < max_dy]
    near.sort(key=lambda w: (round(w[1], 1), w[0]))
    return " ".join(w[4] for w in near).strip()


# --------------------------------------------------------------------------- #
def output_dir_for(pdf_path: Path) -> Path:
    """Zielordner: ~/Downloads/Schaltplan-Marker/<PDF-Name>/ (wird angelegt)."""
    return Path.home() / "Downloads" / "Schaltplan-Marker" / pdf_path.stem


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


def process(inp, out_dir=None, two_colors=False, want_list=False):
    inp = Path(inp)
    target = Path(out_dir) if out_dir else output_dir_for(inp)
    target.mkdir(parents=True, exist_ok=True)
    outp = target / f"{inp.stem}_markiert.pdf"

    doc = fitz.open(inp)
    total = 0
    list_rows = []
    for pno, page in enumerate(doc):
        boxes, rauten, thick, segs = extract(page)
        caseA, caseB = find_marks(boxes, rauten, thick, segs)
        draw_marks(page, caseA, caseB, two_colors)
        total += len(caseA) + len(caseB)
        if want_list:
            words = page.get_text("words")
            for (x, y), fall in [(p, "A") for p in caseA] + [(p, "B") for p in caseB]:
                list_rows.append((pno + 1, fall, round(x, 2), round(y, 2),
                                  nearest_label(words, x, y)))
        print(f"Seite {pno + 1}: Fall A {len(caseA)}, Fall B {len(caseB)}")
    doc.save(outp, deflate=True)
    print(f"\nGesamt {total} Markierungen  ->  {outp}")

    csv_path = target / f"{inp.stem}_fundliste.csv"
    if want_list:
        write_fundliste(csv_path, list_rows)
        print(f"Fundliste            ->  {csv_path}")

    return {"total": total, "pdf": outp, "csv": csv_path if want_list else None, "dir": target}


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


def _parse_version(v):
    """'v1.2.3' / '1.2.3' -> (1, 2, 3); nicht-numerische Teile werden zu 0."""
    nums = []
    for part in str(v).lstrip("vV").split("."):
        digits = "".join(ch for ch in part if ch.isdigit())
        nums.append(int(digits) if digits else 0)
    return tuple(nums)


def _is_newer(remote, local):
    """True, wenn remote eine höhere Version als local ist."""
    return _parse_version(remote) > _parse_version(local)


def latest_release_version(timeout=15):
    """Neueste Release-Version auf GitHub abfragen. Tag-String oder None (bei Fehler/kein Netz)."""
    import urllib.request
    try:
        req = urllib.request.Request(UPDATE_API, headers={"User-Agent": "Schaltplan-Marker"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read()).get("tag_name")
    except Exception:
        return None


def apply_update(timeout=30):
    """Lädt die neuesten Programmdateien (UPDATE_FILES) und ersetzt sie. Gibt (ok, meldung)."""
    import urllib.request, os, tempfile
    folder = Path(__file__).resolve().parent
    try:
        # erst alles herunterladen + prüfen, dann erst schreiben (kein halber Stand)
        payloads = {}
        for fn in UPDATE_FILES:
            req = urllib.request.Request(UPDATE_RAW_BASE + fn, headers={"User-Agent": "Schaltplan-Marker"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = r.read()
            if len(data) < 300 or (fn == "schaltplan_marker.py" and b"__version__" not in data):
                return False, f"Datei {fn} sieht ungültig aus – Update abgebrochen."
            payloads[fn] = data
        for fn, data in payloads.items():
            target = folder / fn
            fd, tmp = tempfile.mkstemp(dir=str(folder), suffix=".py")
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            os.replace(tmp, target)   # atomarer Austausch je Datei
        return True, "Update installiert. Bitte das Programm neu starten."
    except Exception as e:
        return False, f"Update fehlgeschlagen: {type(e).__name__}: {e}"


def run_gui():
    import threading
    try:
        import tkinter as tk
        from tkinter import filedialog, ttk, messagebox
    except Exception:
        print("Grafische Oberfläche (tkinter) nicht verfügbar.")
        print("Nutzung per Kommandozeile: python schaltplan_marker.py plan.pdf --list")
        input("Enter zum Schließen ...")
        return

    root = tk.Tk()
    root.title(f"Schaltplan-Marker  v{__version__}")
    root.geometry("620x520")
    container = ttk.Frame(root)
    container.pack(fill="both", expand=True)

    def clear():
        for w in container.winfo_children():
            w.destroy()

    def check_updates(manual):
        def worker():
            latest = latest_release_version()
            def show():
                if latest is None:
                    if manual:
                        messagebox.showwarning("Update", "Keine Verbindung zu GitHub (Proxy/Firewall?).")
                elif _is_newer(latest, __version__):
                    if messagebox.askyesno("Update",
                            f"Neue Version {latest} verfügbar (installiert: v{__version__}).\n\nJetzt aktualisieren?"):
                        ok, msg = apply_update()
                        (messagebox.showinfo if ok else messagebox.showerror)("Update", msg)
                elif manual:
                    messagebox.showinfo("Update", f"Du hast bereits die neueste Version (v{__version__}).")
            root.after(0, show)
        threading.Thread(target=worker, daemon=True).start()

    # ---- Startbildschirm ---------------------------------------------------
    def show_home():
        clear()
        ttk.Label(container, text="Was möchtest du tun?", font=("", 15)).pack(pady=(50, 25))
        ttk.Button(container, text="🔵   Plan markieren", command=show_mark).pack(padx=60, pady=8, ipady=12, fill="x")
        ttk.Button(container, text="🔍   Pläne vergleichen", command=show_compare).pack(padx=60, pady=8, ipady=12, fill="x")
        ttk.Button(container, text="Nach Updates suchen", command=lambda: check_updates(True)).pack(side="bottom", pady=6)
        ttk.Label(container, text=f"v{__version__}", foreground="#888").pack(side="bottom")

    # ---- Ansicht: Markieren ------------------------------------------------
    def show_mark():
        clear()
        ttk.Button(container, text="← Zurück", command=show_home).pack(anchor="w", padx=8, pady=6)
        want_list = tk.BooleanVar(value=True)
        two_colors = tk.BooleanVar(value=False)
        last_dir = {"path": None}
        status = tk.Text(container, height=11, wrap="word")

        def log(msg):
            status.insert("end", msg + "\n"); status.see("end"); root.update_idletasks()

        def run_on(pdfs):
            pdfs = list(pdfs)
            if not pdfs:
                return
            files_btn.configure(state="disabled"); folder_btn.configure(state="disabled")
            open_btn.configure(state="disabled")

            def worker():
                for pdf in pdfs:
                    root.after(0, log, f"Verarbeite {Path(pdf).name} …")
                    try:
                        res = process(pdf, two_colors=two_colors.get(), want_list=want_list.get())
                        root.after(0, log, f"   →  {res['total']} Kästen ✓")
                        root.after(0, last_dir.__setitem__, "path", res["dir"].parent)
                    except Exception as e:
                        root.after(0, log, f"   →  FEHLER: {e}")

                def done():
                    log("Fertig.")
                    files_btn.configure(state="normal"); folder_btn.configure(state="normal")
                    if last_dir["path"]:
                        open_btn.configure(state="normal")
                root.after(0, done)
            threading.Thread(target=worker, daemon=True).start()

        def choose_files():
            run_on(filedialog.askopenfilenames(title="PDF(s) auswählen", filetypes=[("PDF", "*.pdf")]))

        def choose_folder():
            folder = filedialog.askdirectory(title="Ordner mit PDFs wählen")
            if folder:
                run_on(_collect_pdfs(folder))

        files_btn = ttk.Button(container, text="📄  Einzelne PDF(s) auswählen…", command=choose_files)
        files_btn.pack(fill="x", padx=12, pady=(6, 4))
        folder_btn = ttk.Button(container, text="📁  Ganzen Ordner verarbeiten…", command=choose_folder)
        folder_btn.pack(fill="x", padx=12, pady=4)
        ttk.Checkbutton(container, text="Fundliste (CSV für Excel) erzeugen", variable=want_list).pack(anchor="w", padx=12)
        ttk.Checkbutton(container, text="Fall A / B in zwei Farben (A = rot, B = blau)", variable=two_colors).pack(anchor="w", padx=12, pady=(0, 8))
        status.pack(fill="both", expand=True, padx=12, pady=4)
        open_btn = ttk.Button(container, text="Ausgabeordner öffnen", state="disabled",
                              command=lambda: last_dir["path"] and _open_folder(last_dir["path"]))
        open_btn.pack(fill="x", padx=12, pady=(4, 12))
        log(f"Bereit. Ausgabe in Downloads/Schaltplan-Marker/<PDF>/")

    # ---- Ansicht: Vergleichen ----------------------------------------------
    def show_compare():
        clear()
        ttk.Button(container, text="← Zurück", command=show_home).pack(anchor="w", padx=8, pady=6)
        try:
            import plan_vergleich as pv
        except Exception:
            ttk.Label(container, justify="left", padding=20, text=(
                "Der Plan-Vergleich braucht die Datei 'plan_vergleich.py',\n"
                "die in dieser Installation fehlt.\n\n"
                "Bitte die neueste Version als ZIP von GitHub laden\n"
                "(Releases-Seite) und den Ordner ersetzen.")).pack()
            return
        detail = {"paths": []}
        overview = {"path": None}
        last_dir = {"path": None}

        detail_lbl = tk.StringVar(value="Detailplan(e): –")
        overview_lbl = tk.StringVar(value="Übersicht: –")
        status = tk.Text(container, height=9, wrap="word")

        def log(msg):
            status.insert("end", msg + "\n"); status.see("end"); root.update_idletasks()

        def pick_detail_files():
            fs = filedialog.askopenfilenames(title="Detailplan(e) wählen", filetypes=[("PDF", "*.pdf")])
            if fs:
                detail["paths"] = list(fs)
                detail_lbl.set(f"Detailplan(e): {len(fs)} Datei(en)")

        def pick_detail_folder():
            folder = filedialog.askdirectory(title="Ordner mit Detailplänen wählen")
            if folder:
                detail["paths"] = [str(p) for p in _collect_pdfs(folder)]
                detail_lbl.set(f"Detailplan(e): ganzer Ordner ({len(detail['paths'])})")

        def pick_overview():
            f = filedialog.askopenfilename(title="Übersichts-PDF wählen", filetypes=[("PDF", "*.pdf")])
            if f:
                overview["path"] = f
                overview_lbl.set(f"Übersicht: {Path(f).name}")

        def start():
            if not detail["paths"] or not overview["path"]:
                messagebox.showwarning("Fehlt", "Bitte Detailplan(e) UND die Übersichts-PDF wählen.")
                return
            start_btn.configure(state="disabled"); open_btn.configure(state="disabled")

            def worker():
                root.after(0, log, "Übersicht einlesen …")
                names = pv.station_names(overview["path"])   # nur EINMAL
                for pdf in detail["paths"]:
                    root.after(0, log, f"Vergleiche {Path(pdf).name} …")
                    try:
                        res = pv.run_comparison(pdf, overview_names=names)
                        root.after(0, log, f"   →  {res['unbekannt']} unbekannte Stationen (von {res['gesamt']}) markiert ✓")
                        root.after(0, last_dir.__setitem__, "path", res["dir"].parent)
                    except Exception as e:
                        root.after(0, log, f"   →  FEHLER: {e}")

                def done():
                    log("Fertig.")
                    start_btn.configure(state="normal")
                    if last_dir["path"]:
                        open_btn.configure(state="normal")
                root.after(0, done)
            threading.Thread(target=worker, daemon=True).start()

        ttk.Label(container, text="Detailplan  ⟷  Übersicht vergleichen", font=("", 12, "bold")).pack(anchor="w", padx=12)
        ttk.Label(container, textvariable=detail_lbl).pack(anchor="w", padx=12, pady=(6, 0))
        row = ttk.Frame(container); row.pack(fill="x", padx=12)
        ttk.Button(row, text="Einzelne(n) wählen…", command=pick_detail_files).pack(side="left", pady=2)
        ttk.Button(row, text="Ganzen Ordner…", command=pick_detail_folder).pack(side="left", padx=6)
        ttk.Label(container, textvariable=overview_lbl).pack(anchor="w", padx=12, pady=(8, 0))
        ttk.Button(container, text="Übersichts-PDF wählen…", command=pick_overview).pack(anchor="w", padx=12, pady=2)

        ttk.Label(container, text="Was soll geprüft werden?").pack(anchor="w", padx=12, pady=(10, 0))
        ttk.Checkbutton(container, text="Fehlende / zusätzliche Stationen", variable=tk.BooleanVar(value=True),
                        state="disabled").pack(anchor="w", padx=24)
        for t in ("Attribute (Kabel, Trafo)", "Symbol-Art", "Verbindungen (Topologie)"):
            ttk.Checkbutton(container, text=f"{t}   (kommt später)", state="disabled").pack(anchor="w", padx=24)

        start_btn = ttk.Button(container, text="Vergleich starten", command=start)
        start_btn.pack(fill="x", padx=12, pady=(10, 4))
        status.pack(fill="both", expand=True, padx=12, pady=4)
        open_btn = ttk.Button(container, text="Ergebnis öffnen", state="disabled",
                              command=lambda: last_dir["path"] and _open_folder(last_dir["path"]))
        open_btn.pack(fill="x", padx=12, pady=(4, 12))

    show_home()
    root.after(600, lambda: check_updates(manual=False))
    root.mainloop()


def main():
    if len(sys.argv) == 1:            # Doppelklick / ohne Parameter -> grafische Oberfläche
        run_gui()
        return
    ap = argparse.ArgumentParser(description="Markiert Stromkästen in MS-Netz-Schaltplänen (Vektor-PDF).")
    ap.add_argument("input", type=Path, help="Eingabe-PDF")
    ap.add_argument("-o", "--output", type=Path,
                    help="Ausgabe-ORDNER (Standard: ~/Downloads/Schaltplan-Marker/<PDF-Name>/)")
    ap.add_argument("--two-colors", action="store_true", help="Fall A / Fall B in zwei Farben")
    ap.add_argument("--list", action="store_true", dest="want_list", help="Fundliste als CSV exportieren")
    args = ap.parse_args()

    if not args.input.exists():
        sys.exit(f"Datei nicht gefunden: {args.input}")
    process(args.input, out_dir=args.output, two_colors=args.two_colors, want_list=args.want_list)


if __name__ == "__main__":
    main()
