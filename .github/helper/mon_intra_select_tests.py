#!/usr/bin/env python3
"""Pick the ERPNext test modules that sit next to the files a change touches.

Mon-Intra CI only. Reads changed paths (one per line) on stdin and prints the
dotted test modules to run, one per line. Prints nothing when no test is near
the change; the workflow then runs only the install smoke test.

Rules, per changed path under ``erpnext/``:

1. A changed ``test_*.py`` file is run itself.
2. A file inside a unit folder (``<module>/doctype/<name>/``, ``report/<name>/``,
   ``page/<name>/`` ...) runs the test files of that unit folder, wherever in the
   folder the change is.
3. Any other file (e.g. ``erpnext/stock/stock_ledger.py``) runs
   ``test_<file name>.py`` from its folder or its ``tests/`` sub-folder if one
   exists, otherwise every test file in those two places.

Files directly in ``erpnext/`` (hooks.py, __init__.py ...) and outside the app
select nothing.
"""

import sys
from pathlib import Path

APP = "erpnext"
UNIT_KINDS = {
	"doctype",
	"report",
	"page",
	"print_format",
	"web_form",
	"dashboard_chart",
	"dashboard_chart_source",
	"number_card",
	"workspace",
}


def is_test_file(path: Path) -> bool:
	if not (path.is_file() and path.name.startswith("test_") and path.suffix == ".py"):
		return False
	return "def test_" in path.read_text(encoding="utf-8", errors="ignore")


def tests_in(folder: Path, recursive: bool = False) -> list[Path]:
	if not folder.is_dir():
		return []
	pattern = "**/test_*.py" if recursive else "test_*.py"
	return [p for p in sorted(folder.glob(pattern)) if is_test_file(p)]


def unit_folder(path: Path) -> Path | None:
	"""Return erpnext/<module>/<kind>/<name> if the path lies inside one."""
	parts = path.parts
	for i in range(2, len(parts) - 2):
		if parts[i] in UNIT_KINDS:
			return Path(*parts[: i + 2])
	return None


def select(path: Path) -> list[Path]:
	if path.parts[0] != APP or len(path.parts) < 3:
		return []
	if is_test_file(path):
		return [path]
	unit = unit_folder(path)
	if unit:
		return tests_in(unit, recursive=True)
	folder = path.parent
	for candidate in (folder / f"test_{path.stem}.py", folder / "tests" / f"test_{path.stem}.py"):
		if is_test_file(candidate):
			return [candidate]
	return tests_in(folder) + tests_in(folder / "tests")


def main() -> None:
	modules: list[str] = []
	for line in sys.stdin:
		line = line.strip()
		if not line:
			continue
		for test in select(Path(line)):
			module = ".".join(test.with_suffix("").parts)
			if module not in modules:
				modules.append(module)
	if modules:
		print("\n".join(modules))


if __name__ == "__main__":
	main()
