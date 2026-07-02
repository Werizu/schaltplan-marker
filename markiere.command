#!/bin/bash
# Schaltplan-Marker – Doppelklick-Starter für macOS.
# Doppelklicken, dann die PDF-Datei ins Terminal-Fenster ziehen und Enter.
# (Alternativ:  ./markiere.command  pfad/zur/plan.pdf )

cd "$(dirname "$0")" || exit 1

# Virtuelle Umgebung beim ersten Start anlegen
if [ ! -x ".venv/bin/python" ]; then
  echo "[Setup] Erstelle Umgebung und installiere PyMuPDF ..."
  python3 -m venv .venv
  ./.venv/bin/pip install --quiet --upgrade pip
  ./.venv/bin/pip install --quiet -r requirements.txt
fi

PDF="$1"
if [ -z "$PDF" ]; then
  echo
  echo "PDF-Datei hierher ziehen und Enter druecken:"
  read -r PDF
  PDF="${PDF%\"}"; PDF="${PDF#\"}"   # umschliessende Anfuehrungszeichen entfernen
  PDF="${PDF//\\ / }"                 # per Drag escapte Leerzeichen zuruecksetzen
fi

if [ ! -f "$PDF" ]; then
  echo "Datei nicht gefunden: $PDF"
  read -r -p "Enter zum Schliessen ..."
  exit 1
fi

./.venv/bin/python schaltplan_marker.py "$PDF" --list
echo
echo "Fertig. Ergebnis liegt neben der Eingabe-PDF (..._markiert.pdf)."
read -r -p "Enter zum Schliessen ..."
