"""Smoke tests for config and package layout."""

from rag_injection_lab import __version__
from rag_injection_lab.config import (
    APP_PORT,
    KB_CLEAN_DIR,
    PROJECT_ROOT,
    UPLOADS_DIR,
    ensure_runtime_dirs,
)


def test_version():
    assert __version__ == "0.1.0"


def test_project_root_looks_right():
    assert (PROJECT_ROOT / "pyproject.toml").is_file()
    assert (PROJECT_ROOT / "app" / "Home.py").is_file()
    assert (PROJECT_ROOT / "docs" / "design.md").is_file()
    assert (PROJECT_ROOT / "app" / "pages" / "1_Knowledge_Base.py").is_file()


def test_default_port_is_8505():
    assert APP_PORT == 8505


def test_uploads_dir_is_underscore_uploads():
    assert UPLOADS_DIR.name == "_uploads"


def test_ensure_runtime_dirs():
    ensure_runtime_dirs()
    from rag_injection_lab.config import (
        CORPORA_DIR,
        FINDINGS_DIR,
        KB_POISONED_DIR,
        META_DIR,
        SAMPLES_DIR,
        UPLOADS_DIR as uploads,
    )

    for path in (
        KB_CLEAN_DIR,
        KB_POISONED_DIR,
        CORPORA_DIR,
        FINDINGS_DIR,
        uploads,
        SAMPLES_DIR,
        META_DIR,
    ):
        assert path.is_dir()
