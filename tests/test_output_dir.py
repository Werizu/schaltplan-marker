import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from pathlib import Path
import schaltplan_marker as sm

def test_output_dir_liegt_in_downloads_unterordner():
    p = Path("/irgendwo/Plan Nord.pdf")
    d = sm.output_dir_for(p)
    assert d == Path.home() / "Downloads" / "Schaltplan-Marker" / "Plan Nord"

print("Test test_output_dir...")
test_output_dir_liegt_in_downloads_unterordner()
print("OK")
