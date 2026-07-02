import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import plan_vergleich as pv
import fitz


def test_compare_findet_unbekannte():
    detail = [("Musterstraße 12", fitz.Rect(0, 0, 1, 1)),
              ("Gibtsnicht 99", fitz.Rect(2, 2, 3, 3))]
    overview = {"musterstrasse 12", "beispielhof 4"}
    extra = pv.compare_stations(detail, overview)
    namen = [n for n, r in extra]
    assert namen == ["Gibtsnicht 99"], namen


def test_compare_dedupe():
    # gleiche Station doppelt -> nur EINMAL im Ergebnis, erste Position bleibt
    detail = [("Gibtsnicht 99", fitz.Rect(0, 0, 1, 1)),
              ("Gibtsnicht 99", fitz.Rect(5, 5, 6, 6)),
              ("AZ Gibtsnicht 99", fitz.Rect(7, 7, 8, 8))]
    extra = pv.compare_stations(detail, set())
    assert len(extra) == 1, extra
    assert extra[0][1] == fitz.Rect(0, 0, 1, 1)


print("Test compare...")
test_compare_findet_unbekannte()
test_compare_dedupe()
print("OK")
