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
