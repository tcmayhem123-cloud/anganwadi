"""
Automated test runner for ACGMS verification suite.
Runs unit tests for pure business rules and end-to-end integration tests.
"""
import subprocess
import sys
import os


def run_tests():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    backend_dir = os.path.join(project_root, "backend")

    print("Running ACGMS Automated Verification & Validation Suite...")
    env = os.environ.copy()
    existing_pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{backend_dir}{os.pathsep}{existing_pp}" if existing_pp else backend_dir

    cmd = [
        sys.executable,
        "-m", "pytest",
        os.path.join(backend_dir, "tests"),
        "-v"
    ]
    res = subprocess.run(cmd, cwd=project_root, env=env)
    sys.exit(res.returncode)


if __name__ == "__main__":
    run_tests()
