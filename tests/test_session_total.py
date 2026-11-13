import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location(
        "session_total", ROOT / "bench" / "session_total.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["session_total"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_totals_add_up_from_the_captured_build():
    out = _load().run()
    b = out["bytes_loaded_per_build"]
    assert b["before"] == sum(b["by_call_before"].values())
    assert b["after"] == sum(b["by_call_after"].values())
    assert b["before"] > b["after"] > b["after_for_clients_that_load_outputSchema"]
    assert b["by_call_after"]["export.out"] == 7510
    assert out["brief_to_first_verdict_s"] == {"before": 1180, "after": 177.6}
