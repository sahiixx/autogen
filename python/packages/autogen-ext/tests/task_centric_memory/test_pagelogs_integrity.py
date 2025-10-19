import re
from pathlib import Path

BASE = Path(__file__).resolve().parent
DIRS = [
    BASE / "pagelogs" / "demonstration",
    BASE / "pagelogs" / "self_teaching",
    BASE / "pagelogs" / "teachability",
]

def _declared_count_from_hash(hash_file: Path) -> int:
    """Parse 'NN files' from the second line of hash.txt."""
    lines = hash_file.read_text(encoding="utf-8").splitlines()
    if len(lines) >= 2:
        m = re.search(r"(\d+)\s+files", lines[1])
        if m:
            return int(m.group(1))
    raise AssertionError(f"Unable to parse file count from {hash_file}")

def test_pagelogs_counts_match_hash():
    """hash.txt declared file counts should match on-disk counts."""
    for d in DIRS:
        assert d.exists(), f"Missing directory {d}"
        hash_file = d / "hash.txt"
        assert hash_file.exists(), f"Missing hash.txt in {d}"
        declared = _declared_count_from_hash(hash_file)
        # Count all files (recursively)
        actual = sum(1 for p in d.rglob("*") if p.is_file())
        assert actual == declared, f"Count mismatch in {d}: declared={declared}, actual={actual}"

def _find_call_tree(d: Path) -> Path:
    # Be robust about spacing in filename, e.g., '0  Call Tree.html'
    candidates = list(d.glob("*Call Tree.html"))
    if not candidates:
        raise AssertionError(f"No 'Call Tree.html' file found in {d}")
    # Prefer one starting with '0'
    for p in candidates:
        if p.name.startswith("0"):
            return p
    return candidates[0]

def test_call_tree_html_basic_structure():
    """Call Tree HTML should include title/header and links."""
    for d in DIRS:
        call_tree = _find_call_tree(d)
        text = call_tree.read_text(encoding="utf-8", errors="ignore")
        assert "<h3>" in text and "Call Tree" in text
        assert '<a href="' in text, "Expected links in call tree page"