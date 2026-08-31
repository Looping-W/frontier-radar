from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = PROJECT_ROOT / "scripts" / "install-fradar-completion.ps1"


def test_installer_defaults_to_local_application_data() -> None:
    """Catches a machine-specific default completion location."""
    content = INSTALLER.read_text(encoding="utf-8")

    assert (
        '[string]$CompletionDirectory = (Join-Path $env:LOCALAPPDATA "FrontierRadar")'
        in content
    )


@pytest.mark.skipif(shutil.which("powershell") is None, reason="requires PowerShell")
def test_installer_writes_completion_script_and_profile_loader(tmp_path: Path) -> None:
    completion_dir = tmp_path / "completion"
    profile_path = tmp_path / "Microsoft.PowerShell_profile.ps1"
    fradar_command = Path(sys.executable).with_name("fradar.exe")

    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(INSTALLER),
            "-CompletionDirectory",
            str(completion_dir),
            "-ProfilePath",
            str(profile_path),
            "-FradarCommand",
            str(fradar_command),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert (completion_dir / "fradar-completion.ps1").is_file()
    assert "# Frontier Radar completion" in profile_path.read_text(encoding="utf-8-sig")
