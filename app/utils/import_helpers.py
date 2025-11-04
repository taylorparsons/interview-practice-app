from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Tuple

SUPPORTED_IMPORT_SUFFIXES = {".txt", ".md", ".json", ".jsonl"}
_JSON_TEXT_KEYS = ("text", "content", "chunk")
_JSON_EXCLUDED_KEYS = set(_JSON_TEXT_KEYS) | {"metadata"}


def gather_import_files(path: Path, supported_suffixes: Iterable[str] = SUPPORTED_IMPORT_SUFFIXES) -> List[Path]:
    """Return supported files rooted at ``path`` sorted for deterministic ingest."""
    path = Path(path)
    suffixes = {suffix.lower() for suffix in supported_suffixes}
    if path.is_dir():
        return sorted(p for p in path.rglob("*") if p.suffix.lower() in suffixes)
    return [path] if path.suffix.lower() in suffixes else []


def read_import_file(file_path: Path) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Read a supported file and return parallel text/metadata lists."""
    suffix = file_path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return _read_text_document(file_path)
    if suffix == ".jsonl":
        return _read_jsonl_document(file_path)
    if suffix == ".json":
        return _read_json_document(file_path)
    return [], []


def _read_text_document(file_path: Path) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Return paragraph-separated chunks from a text or markdown file."""
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    chunks = [chunk.strip() for chunk in text.split("\n\n") if chunk.strip()]
    metas = [{"source": str(file_path)} for _ in chunks]
    return chunks, metas


def _read_jsonl_document(file_path: Path) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Parse newline-delimited JSON records into chunk/metadata pairs."""
    texts: List[str] = []
    metas: List[Dict[str, Any]] = []
    with file_path.open("r", encoding="utf-8", errors="ignore") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except Exception:
                continue
            for text, meta in _iter_json_chunks(record, str(file_path)):
                texts.append(text)
                metas.append(meta)
    return texts, metas


def _read_json_document(file_path: Path) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Parse a JSON payload containing chunked content into lists."""
    try:
        data = json.loads(file_path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return [], []
    texts: List[str] = []
    metas: List[Dict[str, Any]] = []
    for text, meta in _iter_json_chunks(data, str(file_path)):
        texts.append(text)
        metas.append(meta)
    return texts, metas


def _iter_json_chunks(data: Any, source: str) -> Iterator[Tuple[str, Dict[str, Any]]]:
    """Yield text + metadata pairs from supported JSON structures."""
    if isinstance(data, str):
        yield data, {"source": source}
        return

    if isinstance(data, list):
        for item in data:
            yield from _iter_json_chunks(item, source)
        return

    if isinstance(data, dict):
        chunks = data.get("chunks")
        if isinstance(chunks, list):
            for item in chunks:
                yield from _iter_json_chunks(item, source)
            return
        text = _select_text_field(data)
        if text:
            yield text, _build_metadata(data, source)


def _select_text_field(payload: Dict[str, Any]) -> str:
    """Return the first non-empty text field from a JSON chunk payload."""
    for key in _JSON_TEXT_KEYS:
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _build_metadata(payload: Dict[str, Any], source: str) -> Dict[str, Any]:
    """Derive metadata for a JSON chunk, ensuring the source path is attached."""
    raw_meta = payload.get("metadata")
    if isinstance(raw_meta, dict):
        metadata = dict(raw_meta)
    else:
        metadata = {key: value for key, value in payload.items() if key not in _JSON_EXCLUDED_KEYS}
    metadata["source"] = source
    return metadata
