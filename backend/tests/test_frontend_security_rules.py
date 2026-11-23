import os
import pytest

def test_frontend_src_has_no_hardcoded_credentials():
    """Verify in CI that AdminSecurePass and hardcoded credentials do not exist in frontend/src."""
    frontend_src = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/src"))
    assert os.path.exists(frontend_src), f"Directory {frontend_src} does not exist"

    forbidden = ["AdminSecurePass", "admin@alhilal-demo.ae"]

    for root, _, files in os.walk(frontend_src):
        for f in files:
            if f.endswith((".ts", ".tsx", ".js", ".jsx")):
                full_path = os.path.join(root, f)
                with open(full_path, "r", encoding="utf-8", errors="ignore") as file:
                    content = file.read()
                    for term in forbidden:
                        assert term not in content, f"Forbidden credential string '{term}' found in {full_path}"
