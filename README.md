# Schaltplan-Marker

Automatische Markierung von **Stromkästen** in Mittelspannungs-Netz-Schaltplänen (Vektor-PDF).

Statt hunderte Kästen von Hand zu prüfen, findet das Tool die relevanten Fälle über **alle Farb-Layer** des Plans und zeichnet einen roten Kreis um jeden Treffer – als echte Vektor-Markierung in einer Kopie des PDFs (Original bleibt unverändert, beim Reinzoomen gestochen scharf).

## 🚀 Fertige Windows-Version (für Kollegen, ohne Installation)

Auf der **[Releases-Seite](../../releases/latest)** das ZIP **`Schaltplan-Marker-Windows.zip`** laden →
entpacken → **`Schaltplan-Marker starten.pyw`** doppelklicken. PyMuPDF ist bereits enthalten
(kein `pip`, kein Internet zum Laufen nötig; nur eine Python-Installation auf dem PC).
**Aktualisieren:** neuestes ZIP laden, Ordner ersetzen.

## Was wird erkannt & markiert

Symbole im Plan (je Netz-Layer in eigener Farbe):

| Symbol | Bedeutung |
|---|---|
| ⊠ Quadrat mit Diagonale(n) | **Stromkasten** |
| ◆ gefüllte Raute | Muffe / Knoten |
| kurzer dicker Balken an der Linie | **Verdickung** direkt vor dem Kasten |

Markiert werden Stromkästen in zwei Fällen (roter Kreis um den Kasten):

- **Fall A** – am Kasten liegt eine **Abzweig-Raute** an (≥ 2 Linienrichtungen laufen zusammen, T-/Kreuzungspunkt).
- **Fall B** – die Linie wird **kurz vor dem Kasten dicker** (ein- oder beidseitig).

## Zwei Werkzeuge unter einem Dach

Beim Start (Doppelklick / ohne Argument) erscheint ein **Startbildschirm** mit zwei Wegen:

- **🔵 Plan markieren** – Stromkästen (Fall A/B) im Plan einkreisen (siehe oben).
- **🔍 Pläne vergleichen** – einen **Detailplan** (z. B. eines Kreises/Ortes) gegen die große
  **Übersichts-PDF** abgleichen und Abweichungen finden.

### Pläne vergleichen (Phase 1: Stationen)
Detailplan(e) + Übersichts-PDF wählen → **Vergleich starten**. Das Tool matcht die **Stationsnamen**
(normalisiert: ß→ss, Umlaute, Präfixe wie AZ/MS) und markiert im Detailplan die Stationen, die es in der
Übersicht **nicht** findet – plus ein CSV-Bericht. Einzeln oder als **ganzer Ordner** (Batch; die
Übersicht wird dabei nur einmal eingelesen).

Ausgabe: `Downloads/Schaltplan-Marker/Vergleich/<Detailplan>/` (`…_geprueft.pdf` + `…_abweichungen.csv`).

> **Prüf-Assistent, kein Richter:** Die Extraktion trifft nicht 100 %; die Treffer sind Vorschläge zum
> Nachsehen. Attribute / Symbol-Art / Topologie folgen in späteren Phasen.

## Installation

Voraussetzung: **Python 3.9+**.

### macOS / Linux
```bash
cd ~/schaltplan-marker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Windows
```bat
cd %USERPROFILE%\schaltplan-marker
py -3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Bedienung ohne Kommandozeile (für Kollegen)

**Einfach die grafische Oberfläche starten:**

- **Windows:** Doppelklick auf **`Schaltplan-Marker starten.pyw`** (öffnet ein Fenster, **kein** schwarzes Konsolenfenster).
- **macOS/Linux:** `python3 schaltplan_marker.py` ohne Argumente → Fenster öffnet.

Im Fenster:
- **„Einzelne PDF(s) auswählen…"** — eine oder mehrere PDFs verarbeiten.
- **„Ganzen Ordner verarbeiten…"** — alle PDFs eines Ordners auf einmal (Stapel).
- Optionen: Fundliste (CSV) erzeugen, Fall A/B in zwei Farben.

**Das Ergebnis liegt immer gesammelt im Download-Ordner:**
```
Downloads/Schaltplan-Marker/<PDF-Name>/
    <PDF-Name>_markiert.pdf      # Plan mit roten Kreisen
    <PDF-Name>_fundliste.csv     # Liste, öffnet sauber in (deutschem) Excel
```
Der Knopf **„Ausgabeordner öffnen"** zeigt es direkt an.

## Nutzung per Kommandozeile (optional)

```bash
python schaltplan_marker.py plan.pdf                 # Ausgabe -> Downloads/Schaltplan-Marker/plan/
python schaltplan_marker.py plan.pdf --list          # zusätzlich Fundliste (CSV)
python schaltplan_marker.py plan.pdf --two-colors    # Fall A/B in zwei Farben
python schaltplan_marker.py plan.pdf -o ZIEL_ORDNER  # in einen eigenen Ordner
```

## Verteilung an gesperrte Arbeits-PCs (offline, ohne pip/Internet)

Auf einem PC **mit** Internet einmalig das Paket bauen:
```bash
python werkzeuge/bundle_windows.py pfad/zum/pymupdf-<version>-cpXY-abi3-win_amd64.whl
```
Erzeugt **`Export/Schaltplan-Marker/`** mit Skript, `.pyw`-Starter, `LIESMICH.txt` **und mitgeliefertem
PyMuPDF** (`fitz/`+`pymupdf/`). Diesen Ordner per USB kopieren — auf dem Ziel-PC genügt der Doppelklick
auf `Schaltplan-Marker starten.pyw`. **Keine Installation, kein Internet, kein `pip`, keine `.bat` nötig.**

Nach späteren Code-Änderungen den Export einfach **auf die aktuelle Version bringen** (PyMuPDF bleibt liegen):
```bash
python werkzeuge/bundle_windows.py        # ohne Argument = nur Code aktualisieren
```
Der `Export/`-Ordner ist die feste Arbeitsversion (bewusst nicht in Git, da große Binärdateien).

## Automatische Updates

Das Tool prüft beim Start (und per Knopf **„Nach Updates suchen"**) auf eine neuere
GitHub-Release-Version und bietet an, sich selbst zu aktualisieren – es lädt dann nur die
kleine Code-Datei `schaltplan_marker.py` (kein `pip`, PyMuPDF bleibt liegen). Schlägt die
Prüfung fehl (z. B. Proxy/Firewall), läuft das Tool normal weiter.

Neue Version veröffentlichen: `__version__` in `schaltplan_marker.py` erhöhen, nach `main`
pushen und ein **GitHub-Release** mit passendem Tag (z. B. `v1.2.0`) anlegen.

> Das passende PyMuPDF-Wheel (abi3, `win_amd64`) gibt es auf PyPI; ein abi3-Wheel läuft über alle
> Python-Versionen ab seiner Mindestversion (z. B. `cp310-abi3` → Python 3.10+).

### Für Entwickler (Mac)
`markiere.command` (Drag-and-drop) und `markiere.bat` (Windows) bleiben als schnelle Starter erhalten.

## Wie es funktioniert (kurz)

1. **Extraktion:** Die Seite wird mit PyMuPDF in Vektor-Primitive zerlegt und je Netzfarbe sortiert.
2. **Klassifikation:**
   - Stromkasten = blaues/farbiges Quadrat (`qu`) mit Diagonale.
   - Raute = gefüllte, **quadratische** Form; Verdickung = gefüllte, **langgestreckte** Form
     (Unterscheidung über das Seitenverhältnis der Bounding-Box, unabhängig von Orientierung).
3. **Analyse:** An jeder Raute werden die **Linienrichtungen gleicher Farbe** gezählt (≥ 2 = Abzweig).
   Verdickungen und Abzweig-Rauten werden dem **nächstgelegenen Kasten** zugeordnet.
4. **Markierung:** Roter Kreis um jeden Treffer, Speichern als neues PDF.

## Anpassen

Alle Schwellenwerte stehen gesammelt oben in `schaltplan_marker.py`:

- `NETWORK_COLORS` – Liste der Layer-Farben (weitere Farben hier ergänzen).
- `G[...]` – Geometrie-Schwellen (Symbolgrößen, Abzweig-Radius, Zuordnungs-Abstand).
- `CIRCLE_*`, `COLOR_*` – Stil der Markierung.

Die Werte sind auf das übliche CAD-Export-Format dieser Netzpläne abgestimmt. Kommt ein
Plan in anderer Skalierung, müssen die `G`-Größen entsprechend skaliert werden.

## Grenzen

Bei mehreren tausend Symbolen können vereinzelte Randfälle (exotisch gezeichnete Verdickungen)
übersehen werden. Die `--list`-Fundliste hilft beim gezielten Gegenprüfen.
Die Stationsnamen in der Fundliste sind *best effort* (nächstgelegene Textbausteine).
