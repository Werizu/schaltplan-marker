# Doppelklick-Starter (pythonw -> kein Konsolenfenster). Oeffnet die grafische Oberflaeche.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schaltplan_marker
schaltplan_marker.run_gui()
