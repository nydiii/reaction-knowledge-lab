"""Execute the four classroom notebooks in order, using this Python environment.

No API calls are made. A temporary kernelspec avoids changing global Jupyter
configuration or accidentally selecting another environment's python3 kernel.
"""

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = ("01_extraction.ipynb", "02_alignment.ipynb", "03_validation_update.ipynb", "04_cross_paper_batch.ipynb")


def resolve_path(value):
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workdir", default="runs/notebook-lab", help="New, empty directory for lesson results.")
    parser.add_argument("--output-dir", default="runs/notebook-executed", help="Directory for executed notebook copies.")
    args = parser.parse_args()
    workdir, output_dir = resolve_path(args.workdir), resolve_path(args.output_dir)
    if workdir.exists() and (not workdir.is_dir() or any(workdir.iterdir())):
        parser.exit(2, f"工作目录已有结果，拒绝覆盖数据库或实验记录：{workdir}\n请指定新的 --workdir。\n")
    if workdir == output_dir or workdir in output_dir.parents or output_dir in workdir.parents:
        parser.exit(2, "--workdir 和 --output-dir 应为互不包含的两个目录。\n")
    output_dir.mkdir(parents=True, exist_ok=True)
    if any((output_dir / name).exists() for name in NOTEBOOKS):
        parser.exit(2, "输出目录已有执行后的 Notebook，请指定新的 --output-dir。\n")
    workdir.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["RKL_NOTEBOOK_RUN_DIR"] = str(workdir)
    with tempfile.TemporaryDirectory(prefix="rkl-kernel-") as directory:
        env["IPYTHONDIR"] = str(Path(directory) / "ipython")
        env["JUPYTER_RUNTIME_DIR"] = str(Path(directory) / "runtime")
        kernels_root = Path(directory) / "kernels"
        specification = kernels_root / "rkl-course"
        specification.mkdir(parents=True)
        (specification / "kernel.json").write_text(json.dumps({
            "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
            "display_name": "Reaction Knowledge Lab (current Python)",
            "language": "python",
        }), encoding="utf-8")
        for name in NOTEBOOKS:
            notebook = nbformat.read(ROOT / "notebooks" / name, as_version=4)
            manager = KernelManager(
                kernel_name="rkl-course",
                connection_file=str(Path(directory) / f"{Path(name).stem}-connection.json"),
                kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(kernels_root)], ensure_native_kernel=False),
            )
            client = NotebookClient(notebook, km=manager, timeout=180, allow_errors=False,
                                    resources={"metadata": {"path": str(ROOT)}})
            print(f"执行 {name}；Python: {sys.executable}", flush=True)
            try:
                client.execute(env=env, cleanup_kc=True)
            finally:
                nbformat.write(notebook, output_dir / name)
            print(f"完成 {name}", flush=True)
    print(json.dumps({"status": "complete", "api_calls": 0, "workdir": str(workdir),
                      "executed_notebooks": str(output_dir)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
