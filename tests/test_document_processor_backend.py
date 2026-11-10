import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import app.utils.document_processor as docproc  # noqa: E402


def test_document_processor_uses_pypdf_reader():
    assert hasattr(docproc, "PdfReader")
    assert docproc.PdfReader.__module__.startswith("pypdf")


def test_extract_text_from_pdf_retries_non_strict(monkeypatch, tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%EOF")

    calls = []

    class FakeReader:
        def __init__(self, file_obj, strict=False):
            calls.append(strict)
            if strict:
                file_obj.read(1)
                raise ValueError("strict mode failed")
            if file_obj.tell() != 0:
                raise AssertionError("file was not rewound before fallback")
            self.pages = []

    monkeypatch.setattr(docproc, "PdfReader", FakeReader)

    result = docproc.extract_text_from_pdf(str(pdf_path))

    assert result == ""
    assert calls == [True, False]
