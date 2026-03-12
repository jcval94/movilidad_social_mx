from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional


def commit_if_changed(repo_dir: str, message: str, add_path: Optional[str] = None) -> bool:
    repo = Path(repo_dir)
    if add_path:
        subprocess.run(["git", "add", add_path], cwd=repo, check=True)

    status = subprocess.run(["git", "status", "--porcelain"], cwd=repo, check=True, capture_output=True, text=True)
    if not status.stdout.strip():
        return False

    subprocess.run(["git", "commit", "-m", message], cwd=repo, check=True)
    return True
