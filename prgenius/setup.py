"""Build hook: ship the decision-relevant knowledge corpus inside the wheel.

Why this file exists (issue #116): the corpus lives at the repository root
(``anti-patterns/``, ``profiles/``, …) because the npm/DSH package and
``validate.py`` read it there.  A wheel built from ``prgenius/`` therefore
contained code only — ``pip install prgenius-core`` produced an amnesiac
dashboard that had to be pointed at a git clone before it knew anything.

What it does: at build time it copies the subset that actually drives scoring
decisions into ``prgenius/data/`` **inside the build artifacts** (the wheel's
``build_lib`` and the sdist's release tree), so the installed package carries
its own memory and ``utils._find_repo_root()`` resolves it as
``package-data``.  The working checkout is never written to — a generated
copy under ``prgenius/`` would double every corpus count in ``validate.py``.

What it deliberately does not ship: ``success-patterns/`` (~2.7 MB / 693
files).  ``evaluator.load_success_patterns()`` documents that corpus as
retrieval/reference only — it is never consulted by the scorer and 0/692 of
its entries carry ``trigger_keywords`` — so shipping it would nearly triple
the wheel without changing a single decision.  Its loader already degrades
quietly when the directory is absent, and ``prgenius doctor`` reports
``success_patterns_installed: false`` instead of pretending.

Source-of-truth rules:
  * Built from a pr-genius checkout → read the repository root (live corpus).
  * Built from an sdist (``python -m build`` does sdist → wheel) → the sdist
    tree already carries ``data/`` (injected by :class:`Sdist`); read that.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py
from setuptools.command.sdist import sdist

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
SDIST_DATA = HERE / "data"  # present only inside an unpacked sdist

# Decision-relevant subset.  Relative to the knowledge root, mirrored under
# data/ so every consumer's ``root / "anti-patterns"`` lookup keeps working.
CORPUS_DIRS = (
    "anti-patterns",
    "profiles",
    "pr-observations",
    "docs/policies",
    "locale",
)


def _copy_corpus(dst: Path) -> Path:
    """Copy the corpus subset into *dst* (``.../prgenius/data`` semantics)."""
    if dst.exists():
        shutil.rmtree(dst)
    for rel in CORPUS_DIRS:
        src = REPO_ROOT / rel
        if not src.is_dir():
            raise SystemExit(
                f"prgenius-core build: corpus dir missing in checkout: {src}"
            )
        shutil.copytree(src, dst / rel)
    return dst


def _corpus_source() -> Path:
    """Directory holding the corpus subset for this build.

    A checkout reads the live repository root; a wheel built from an sdist
    reads the ``data/`` the sdist carried along.
    """
    if (REPO_ROOT / "anti-patterns").is_dir():
        return REPO_ROOT
    if (SDIST_DATA / "anti-patterns").is_dir():
        return SDIST_DATA
    raise SystemExit(
        "prgenius-core build: no knowledge corpus found. Build from a "
        "pr-genius checkout (…/pr-genius/prgenius) or from an sdist that "
        "already contains data/ — a wheel without the corpus is the amnesiac "
        "install issue #116 fixed."
    )


def _copy_corpus_from_source(dst: Path) -> Path:
    src = _corpus_source()
    if src is SDIST_DATA:
        # Already the right tree shape; just copy it into the artifact.
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(SDIST_DATA, dst)
        return dst
    return _copy_corpus(dst)


class BuildPy(build_py):
    def run(self) -> None:
        super().run()
        # install_lib copies build_lib wholesale into the wheel, so files
        # placed here are packaged without package-data glob gymnastics.
        _copy_corpus_from_source(Path(self.build_lib) / "prgenius" / "data")


class Sdist(sdist):
    def make_release_tree(self, base_dir: str, files: list) -> None:
        super().make_release_tree(base_dir, files)
        # Inject the corpus into the release tree so the wheel that
        # `python -m build` builds from this sdist also carries it. The
        # checkout itself is left untouched (validate.py would double-count).
        _copy_corpus(Path(base_dir) / "data")


setup(cmdclass={"build_py": BuildPy, "sdist": Sdist})
