# Design: Alltagstaugliche Bedienung für Kollegen

**Datum:** 2026-07-02
**Status:** freigegeben

## Ausgangslage / Problem

Das Tool `schaltplan_marker.py` funktioniert, wird aber bisher über die Kommandozeile
bzw. `.bat`/`.command` gestartet. Für den Alltag der Kollegen muss es **ohne Befehle tippen**
laufen — und zwar auf **gesperrten Arbeits-PCs** mit folgenden Rahmenbedingungen:

- Python ist vorhanden (Doppelklick auf `.py` **führt aus**, Fenster schließt nur sofort mangels Parameter).
- **Kein `pip`, kein Internet** → Abhängigkeiten müssen mitgeliefert werden.
- **`.bat` ist blockiert.**

Zusätzlich: Die erzeugte CSV („Fundliste") öffnet in deutschem Excel fehlerhaft.

## Ziele

1. Bedienung per **Doppelklick + Klicken**, kein Tippen, keine IT-Freigabe nötig.
2. Einzel- **und** Stapelverarbeitung (mehrere PDFs / ganzer Ordner).
3. Ausgabe gesammelt im **Download-Ordner**.
4. CSV **Deutsch-Excel-tauglich**.
5. Verteilbar als **ein kopierbarer Ordner**, komplett offline.

## Gewählter Ansatz: A + B (GUI + Stapel), in einer Datei

### Betriebsarten
- **Mit CLI-Parametern** → bisheriges Verhalten (CLI, Automatisierung).
- **Ohne Parameter (Doppelklick)** → öffnet ein **tkinter-Fenster** (Python-Bordmittel, kein pip):

```
┌────────── Schaltplan-Marker ──────────┐
│  [ 📄 Einzelne PDF(s) auswählen… ]     │
│  [ 📁 Ganzen Ordner verarbeiten… ]     │
│  ☑ Fundliste (CSV für Excel)           │
│  ☐ Fall A / B in zwei Farben           │
│  ───────────────────────────────────   │
│  plan_nord.pdf  → 1.501 Kästen ✓       │
│  plan_sued.pdf  → 943 Kästen ✓         │
│  Fertig. [ Ausgabeordner öffnen ]      │
└────────────────────────────────────────┘
```

- **Knopf 1 (Fall A):** Dateiauswahl-Dialog, Mehrfachauswahl möglich.
- **Knopf 2 (Fall B):** Ordner wählen → **alle PDFs darin** werden verarbeitet.
- **Optionen:** CSV-Fundliste (Standard an), Zwei-Farben-Modus (Standard aus).
- **Statusliste:** je Datei Erfolg/Fehler; Fehler brechen den Stapel **nicht** ab.
- **„Ausgabeordner öffnen"** zeigt das Ergebnis direkt.

### Ausgabe-Struktur (immer im Download-Ordner)
```
Downloads/Schaltplan-Marker/<PDF-Name>/
    <PDF-Name>_markiert.pdf
    <PDF-Name>_fundliste.csv
```
- Pfad plattformunabhängig via `Path.home()/"Downloads"`.
- Erneuter Lauf derselben PDF → deren Unterordner wird überschrieben (vorhersehbar).

## CSV-/Excel-Fix

- Trennzeichen **Semikolon** (`;`) statt Komma.
- Kodierung **UTF-8 mit BOM** (`utf-8-sig`) → korrekte Umlaute.
- Koordinaten mit **Dezimal-Komma** (`152,8`).
- Ergebnis: öffnet per Doppelklick sauber in Spalten, ohne Import-Assistent.
- *Nicht Teil dieses Designs (optional später):* Qualität der Stationsnamen
  (aktuell teils mit Nachbar-Labels vermischt).

## Verteilung an Kollegen (offline, gesperrter PC)

Ein kopierfertiger Ordner (USB/Netzlaufwerk):
```
Schaltplan-Marker/
├─ Schaltplan-Marker starten.pyw   # Doppelklick-Start via pythonw → KEIN Konsolenfenster
├─ schaltplan_marker.py            # Logik + CLI + GUI
├─ fitz/  +  pymupdf/              # PyMuPDF mitgeliefert (aus abi3-Wheel entpackt)
└─ LIESMICH.txt                    # Kurzanleitung
```
- `.pyw` → Start über `pythonw`, sauberes Fenster ohne schwarze Konsole.
- Komplett ohne Installation/Internet.

## Fehlerbehandlung

- Keine/kaputte/keine-PDF-Datei → Meldung in der Statusliste, Stapel läuft weiter.
- Ergebnis-PDF ist geöffnet/gesperrt → klare Meldung (Datei schließen und erneut).
- `tkinter` nicht vorhanden (sehr selten) → verständlicher Hinweistext (Fallback CLI).
- Keine Auswahl getroffen → nichts passiert.

## Architektur / Komponenten

- **Eine Logik-Datei** `schaltplan_marker.py`:
  - Kernfunktionen unverändert (`extract`, `find_marks`, `draw_marks`, `process`).
  - `process()` erhält festes Ausgabeziel (Downloads-Unterordner) statt „neben Eingabe".
  - CSV-Schreiben angepasst (Semikolon, BOM, Dezimal-Komma).
  - `main()`: ohne Argumente → `run_gui()`, mit Argumenten → CLI wie bisher.
- **`run_gui()`** (tkinter): Fenster, zwei Auswahl-Knöpfe, Optionen, Statusliste, „Ordner öffnen".
- **`.pyw`-Starter**: ruft nur die GUI auf (sauberer Doppelklick-Einstieg).

## Testkriterien

- CLI-Regression: Beispiel-PDF ergibt weiterhin **1.501 Markierungen (129 A / 1.372 B)**.
- CSV öffnet in (deutschem) Excel korrekt in Spalten, Umlaute intakt.
- GUI: Einzel- und Ordner-Auswahl erzeugen die Ausgabe unter `Downloads/Schaltplan-Marker/…`.
- Fehlerfall (kaputte PDF im Stapel) unterbricht den Lauf nicht.

## Bewusst NICHT im Scope (YAGNI)

- Keine `.exe`/PyInstaller (Blockade-Risiko auf gesperrten PCs).
- Kein Drag-&-Drop aus dem Explorer ins Fenster (bräuchte Fremd-Paket `tkinterdnd2`).
- Keine fixen `Eingang/Ausgang`-Ordner (Ordner-Dialog ist flexibler).
