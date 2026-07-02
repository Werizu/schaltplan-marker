import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import schaltplan_marker as sm

def test_parse_version():
    assert sm._parse_version("v1.2.3") == (1, 2, 3)
    assert sm._parse_version("1.10.0") == (1, 10, 0)

def test_is_newer():
    assert sm._is_newer("v1.1.0", "1.0.0") is True
    assert sm._is_newer("v1.0.0", "1.0.0") is False
    assert sm._is_newer("v0.9.0", "1.0.0") is False
    assert sm._is_newer("v1.10.0", "1.9.0") is True   # numerisch, nicht alphabetisch

print("Test version...")
test_parse_version()
test_is_newer()
print("OK")
