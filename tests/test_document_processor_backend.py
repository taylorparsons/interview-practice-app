import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import app.utils.document_processor as docproc  # noqa: E402


def test_document_processor_uses_pypdf_reader():
    assert hasattr(docproc, "PdfReader")
    assert docproc.PdfReader.__module__.startswith("pypdf")
