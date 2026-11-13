import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_worker_ts_with_node():
    r = subprocess.run(
        ["node", "--test", "worker.test.ts"],
        check=False,
        cwd=Path(__file__).parent,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stdout + r.stderr
