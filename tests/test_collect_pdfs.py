import sys, pathlib, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import schaltplan_marker as sm
from pathlib import Path

def test_collect_pdfs_findet_nur_pdf():
    d = Path(tempfile.mkdtemp())
    (d/"a.pdf").write_bytes(b"%PDF")
    (d/"b.PDF").write_bytes(b"%PDF")
    (d/"c.txt").write_text("x")
    got = sorted(p.name for p in sm._collect_pdfs(d))
    assert got == ["a.pdf", "b.PDF"], got

print("Test collect_pdfs..."); test_collect_pdfs_findet_nur_pdf(); print("OK")
