import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import plan_vergleich as pv


def test_normalize():
    assert pv.normalize_name("AZ Musterstraße 9") == "musterstrasse 9"
    assert pv.normalize_name("MS Beispielhof 4") == "beispielhof 4"
    assert pv.normalize_name("Nordweg 12") == "nordweg 12"
    assert pv.normalize_name("Südstraße\n") == "suedstrasse"
    assert pv.normalize_name("TMU  Beispieldorf  24") == "beispieldorf 24"


print("Test normalize...")
test_normalize()
print("OK")
