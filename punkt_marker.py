"""Markiert Stromkästen nach ihrem Punkt-Typ: Anzahl Punkte × Kabelführung.

  Anzahl Punkte:   1 (Kasten ohne Raute) / 2 (Kasten + Raute daneben)
  Kabelführung:    Ende / durch (fortlaufend) / Abzweig

Der Nutzer wählt gewünschte Kombinationen; nur diese Kästen werden eingekreist.
Läuft auf der grossen Übersichts-PDF (Kästen sitzen dort sauber auf der Linie).
"""
from __future__ import annotations
import math
import collections
from pathlib import Path

import fitz  # PyMuPDF

from schaltplan_marker import NETWORK_COLORS, _classify_color  # gemeinsame Farb-Logik

TOPOS = ("Ende", "durch", "Abzweig")

# Geometrie-Schwellen (Punkte) – auf das Export-Format der Übersicht abgestimmt.
G = dict(
    box_min=0.07, box_max=0.20,
    raute_min=0.08, raute_max=0.22, raute_aspect=1.5,
    dedup=0.02,
    raute_radius=0.28,      # Raute zählt zum Kasten, wenn so nah
    box_inner=0.11,         # Segmente ganz in der Box (Diagonalen) ausschliessen
    near=0.06,              # Segment gehört zum Kasten, wenn so nah
    cluster_len=0.05,       # Mindest-Gesamtlänge, damit eine Richtung zählt
    both_sides=0.03,        # Kabel auf beiden Seiten -> durchlaufend
    angle_tol=20.0,
)


def _seg_len(a, b):
    return math.hypot(b.x - a.x, b.y - a.y)


def _extract(page):
    """Je Farb-Layer: Kästen, Rauten, Kabelsegmente."""
    n = len(NETWORK_COLORS)
    boxes = [[] for _ in range(n)]
    rautes = [[] for _ in range(n)]
    segs = [[] for _ in range(n)]
    for path in page.get_drawings():
        items, bb, t = path["items"], path["rect"], path["type"]
        w, h = bb.width, bb.height
        mx, mn = max(w, h), min(w, h)
        if t == "s":
            ci = _classify_color(path.get("color"))
            if ci is None:
                continue
            if any(it[0] == "qu" for it in items) and G["box_min"] < w < G["box_max"] and G["box_min"] < h < G["box_max"]:
                boxes[ci].append((bb.x0 + w / 2, bb.y0 + h / 2))
            else:
                for it in items:
                    if it[0] == "l":
                        segs[ci].append((it[1].x, it[1].y, it[2].x, it[2].y, _seg_len(it[1], it[2])))
        elif t == "f":
            ci = _classify_color(path.get("fill"))
            if ci is None:
                continue
            if sum(1 for it in items if it[0] == "l") >= 4 and G["raute_min"] < mn and mx < G["raute_max"] and mx / mn < G["raute_aspect"]:
                rautes[ci].append((bb.x0 + w / 2, bb.y0 + h / 2))
    return boxes, rautes, segs


def _dedup(points):
    out = []
    for c in points:
        if not any(abs(c[0] - o[0]) < G["dedup"] and abs(c[1] - o[1]) < G["dedup"] for o in out):
            out.append(c)
    return out


def _dist_point_seg(px, py, s):
    x0, y0, x1, y1 = s[:4]
    dx, dy = x1 - x0, y1 - y0
    L = dx * dx + dy * dy
    if L == 0:
        return math.hypot(px - x0, py - y0)
    t = max(0, min(1, ((px - x0) * dx + (py - y0) * dy) / L))
    return math.hypot(px - (x0 + t * dx), py - (y0 + t * dy))


def _topology(bx, by, grid):
    """Ende / durch / Abzweig anhand der Kabelrichtungen am Kasten."""
    gi, gj = int(bx / 0.5), int(by / 0.5)
    clusters = collections.defaultdict(lambda: [0.0, []])
    seen = set()
    for a in range(gi - 1, gi + 2):
        for b in range(gj - 1, gj + 2):
            for s in grid[(a, b)]:
                if s in seen:
                    continue
                seen.add(s)
                if math.hypot(s[0] - bx, s[1] - by) < G["box_inner"] and math.hypot(s[2] - bx, s[3] - by) < G["box_inner"]:
                    continue  # Box-Diagonale
                if _dist_point_seg(bx, by, s) < G["near"]:
                    ang = math.degrees(math.atan2(s[3] - s[1], s[2] - s[0])) % 180
                    key = next((k for k in clusters if min(abs(ang - k), 180 - abs(ang - k)) < G["angle_tol"]), ang)
                    clusters[key][0] += s[4]
                    clusters[key][1] += [(s[0] - bx, s[1] - by), (s[2] - bx, s[3] - by)]
    sig = [(k, v) for k, v in clusters.items() if v[0] > G["cluster_len"]]
    if len(sig) >= 2:
        return "Abzweig"
    if len(sig) == 1:
        k, v = sig[0]
        a = math.radians(k)
        proj = [ox * math.cos(a) + oy * math.sin(a) for ox, oy in v[1]]
        return "durch" if (min(proj) < -G["both_sides"] and max(proj) > G["both_sides"]) else "Ende"
    return "Ende"   # kein Kabel gefunden -> als Ende werten


def classify_boxes(page):
    """Liefert Liste (x, y, punkte, topo) für alle Kästen der Seite."""
    boxes, rautes, segs = _extract(page)
    out = []
    for ci in range(len(NETWORK_COLORS)):
        bx = _dedup(boxes[ci])
        rx = _dedup(rautes[ci])
        grid = collections.defaultdict(list)
        for s in segs[ci]:
            for gx, gy in {(int(s[0] / 0.5), int(s[1] / 0.5)), (int(s[2] / 0.5), int(s[3] / 0.5)),
                           (int((s[0] + s[2]) / 2 / 0.5), int((s[1] + s[3]) / 2 / 0.5))}:
                grid[(gx, gy)].append(s)
        for (x, y) in bx:
            nr = sum(1 for r in rx if math.hypot(r[0] - x, r[1] - y) < G["raute_radius"])
            punkte = 1 + min(nr, 1)
            out.append((x, y, punkte, _topology(x, y, grid)))
    return out


def mark_by_type(pdf, selection, out_dir=None, color=(1, 0, 0)):
    """Kreist Kästen ein, deren (punkte, topo) in `selection` (Menge von Tupeln) liegt.

    selection: z. B. {(1, "Ende"), (2, "durch")}. Gibt Ergebnis-Dict zurück."""
    pdf = Path(pdf)
    doc = fitz.open(pdf)
    total = 0
    hits = collections.Counter()
    sel = set(selection)
    for page in doc:
        cls = classify_boxes(page)
        sh = page.new_shape()
        for (x, y, punkte, topo) in cls:
            if (punkte, topo) in sel:
                sh.draw_circle(fitz.Point(x, y), 0.33)
                total += 1
                hits[(punkte, topo)] += 1
        sh.finish(color=color, width=0.055)
        sh.commit()

    target = Path(out_dir) if out_dir else (Path.home() / "Downloads" / "Schaltplan-Marker" / pdf.stem)
    target.mkdir(parents=True, exist_ok=True)
    out_pdf = target / f"{pdf.stem}_punkt-typ.pdf"
    doc.save(out_pdf, deflate=True)
    return {"pdf": out_pdf, "dir": target, "total": total, "hits": dict(hits)}
