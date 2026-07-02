"""Plan-Vergleich: Detailplan gegen Uebersicht abgleichen (Phase 1: Stationen)."""
from __future__ import annotations
import re
from pathlib import Path

import fitz  # PyMuPDF

# Praefixe, die keine Stationsidentitaet sind (Anlagentyp/Rolle).
_PREFIXES = {"az", "ms", "tmu", "nlw", "pv", "ua", "ss", "af", "ap", "km", "wg",
             "bl", "endmuffe", "endmast", "muffe"}

_UML = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss", "Ä": "ae", "Ö": "oe", "Ü": "ue"}


def normalize_name(s: str) -> str:
    """Vereinheitlicht einen Stationsnamen fuer den Vergleich."""
    s = s.replace("\n", " ")
    for k, v in _UML.items():
        s = s.replace(k, v)
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    toks = [t for t in s.split() if t not in _PREFIXES]
    return " ".join(toks)


# Titelblock-, Legenden- und Annotationstext, der keine Station ist.
_JUNK = re.compile(
    r"(\bsap\w*|\btel\b|\bgmbh\b|\bnepprj\b|\bnetzleitstelle\b|\bwestnetz\b"
    r"|\brev\b|\bdatum\b|\bname\b|\bbearb\b|\bgepr\b|\bletzte\b|\baenderung\w*"
    r"|\bstrecke\b|\bndsp\w*|\beeu\b|\bminor\b|\bmipak\b|\bfernsteuerbar\b"
    r"|\bvermietet\b|\bmagnefix\b|\bblatt\b|\bprojekt\w*)",
    re.IGNORECASE)


def _looks_like_station(text: str) -> bool:
    """Heuristik: Stationsname (Buchstaben) statt Kabel-/Trafo-/Stromwert oder Titelblock-Text."""
    t = text.strip()
    if len(t) < 3:
        return False
    if not re.search(r"[A-Za-zÄÖÜäöü]{3,}", t):
        return False
    if re.search(r"\b(kVA|MVA|CU|AL|kV|mm2|MW)\b", t):
        return False
    if re.fullmatch(r"[\d.,\s]+A?", t):
        return False
    if _JUNK.search(t.replace("ä", "ae").replace("Ä", "Ae")):
        return False
    return True


def extract_stations(pdf_path):
    """Liefert [(name, fitz.Rect)] der stationsartigen Textbloecke."""
    doc = fitz.open(pdf_path)
    out = []
    for page in doc:
        for b in page.get_text("blocks"):
            x0, y0, x1, y1, text = b[0], b[1], b[2], b[3], b[4]
            for line in text.splitlines():
                name = line.strip()
                if _looks_like_station(name):
                    out.append((name, fitz.Rect(x0, y0, x1, y1)))
    return out


def station_names(pdf_path):
    """Nur die normalisierten Namen (fuer die Uebersicht, ohne Position)."""
    return {normalize_name(n) for n, _ in extract_stations(pdf_path)}


def compare_stations(detail_stations, overview_names):
    """Detail-Stationen, deren normalisierter Name nicht in der Uebersicht vorkommt.
    Entdoppelt nach normalisiertem Namen (erste Position wird behalten)."""
    ov = set(overview_names)
    extra = []
    gesehen = set()
    for name, rect in detail_stations:
        key = normalize_name(name)
        if key in ov or key in gesehen:
            continue
        gesehen.add(key)
        extra.append((name, rect))
    return extra


def _write_report(csv_path, rows):
    import csv as _csv
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        wr = _csv.writer(f, delimiter=";")
        wr.writerow(["Typ", "Station", "Hinweis"])
        wr.writerows(rows)


def run_comparison(detail_pdf, overview_pdf=None, out_dir=None, overview_names=None):
    """Vergleicht Detailplan gegen Uebersicht (Phase 1). Gibt Ergebnis-Dict zurueck.

    overview_names: vorab berechnete Namensmenge (fuer Batch: Uebersicht nur EINMAL einlesen)."""
    detail_pdf = Path(detail_pdf)
    detail = extract_stations(detail_pdf)
    overview = overview_names if overview_names is not None else station_names(overview_pdf)
    extra = compare_stations(detail, overview)

    target = Path(out_dir) if out_dir else (
        Path.home() / "Downloads" / "Schaltplan-Marker" / "Vergleich" / detail_pdf.stem)
    target.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(detail_pdf)
    page = doc[0]
    sh = page.new_shape()
    for name, rect in extra:
        c = fitz.Point((rect.x0 + rect.x1) / 2, (rect.y0 + rect.y1) / 2)
        r = max(rect.width, rect.height) / 2 + 4
        sh.draw_circle(c, r)
    sh.finish(color=(1, 0, 0), width=1.2)
    sh.commit()
    out_pdf = target / f"{detail_pdf.stem}_geprueft.pdf"
    doc.save(out_pdf, deflate=True)

    csv_path = target / f"{detail_pdf.stem}_abweichungen.csv"
    rows = [["nicht in Übersicht", name, "im Detailplan, aber in der Übersicht nicht gefunden"]
            for name, _ in extra]
    _write_report(csv_path, rows)

    return {"pdf": out_pdf, "csv": csv_path, "dir": target,
            "gesamt": len(detail), "unbekannt": len(extra)}
