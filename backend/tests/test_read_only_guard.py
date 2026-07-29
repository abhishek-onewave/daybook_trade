import re
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1] / "app"

FORBIDDEN_PATTERNS = (
    re.compile(r"""(?:post|put|patch|delete)\s*\(\s*["'][^"']*/orders?""", re.IGNORECASE),
    re.compile(
        r"""(?:client|httpx|requests)\.(?:post|put|patch|delete)\s*\([^)]*tastytrade""",
        re.IGNORECASE | re.DOTALL,
    ),
)


def test_tastytrade_has_no_order_mutation_calls() -> None:
    violations: list[str] = []
    for path in APP_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_PATTERNS:
            if pattern.search(source):
                violations.append(f"{path.relative_to(APP_ROOT)} matched {pattern.pattern}")

    assert violations == [], "Read-only brokerage guard failed:\n" + "\n".join(violations)

