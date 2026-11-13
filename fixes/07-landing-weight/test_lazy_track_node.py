import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_lazy_track_ts_with_node():
    r = subprocess.run(
        ["node", "--test", "lazy-track.test.ts"],
        cwd=Path(__file__).parent,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr
