import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)


def _simple_tokenize(text: str) -> List[str]:
    """Very simple tokenizer: lowercase, split on non-alphanumerics, drop empties."""
    import re

    text = (text or "").lower()
    tokens = re.split(r"[^a-z0-9]+", text)
    return [t for t in tokens if t]


@dataclass
class LexicalDoc:
    """Stored lexical chunk with precomputed TF-IDF weights."""
    id: str
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    tfidf: Dict[str, float] = field(default_factory=dict)  # term -> weight
    length: float = 0.0  # L2 norm of tfidf vector


class LexicalVectorStore:
    """A lightweight, file-backed lexical vector store using TF-IDF-like weights.

    - Stores per-document TF and maintains global DF to compute IDF.
    - Persists to a single JSON file for simplicity.
    - Suitable for small-to-medium local knowledge bases without external deps.
    """

    def __init__(self, path: Path):
        """Initialise the lexical store backed by the provided JSON file."""
        self.path = Path(path)
        self.docs: List[LexicalDoc] = []
        # Global stats
        self.df: Dict[str, int] = {}  # doc freq per term
        self.doc_count: int = 0
        # Metadata
        self.meta: Dict[str, Any] = {
            "engine": "lexical",
            "version": 1,
        }
        if self.path.exists():
            try:
                self._load()
            except Exception:
                logger.exception("Failed to load vector store from %s; starting fresh", self.path)

    # ---------- Persistence ----------
    def _load(self) -> None:
        """Load persisted store metadata and documents from disk."""
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.meta = data.get("meta", {})
        self.doc_count = data.get("doc_count", 0)
        self.df = data.get("df", {})
        self.docs = []
        for d in data.get("docs", []):
            self.docs.append(
                LexicalDoc(
                    id=d["id"],
                    text=d.get("text", ""),
                    metadata=d.get("metadata", {}),
                    tfidf=d.get("tfidf", {}),
                    length=float(d.get("length", 0.0)),
                )
            )

    def _save(self) -> None:
        """Write the current store state to disk."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "meta": self.meta,
            "doc_count": self.doc_count,
            "df": self.df,
            "docs": [
                {
                    "id": d.id,
                    "text": d.text,
                    "metadata": d.metadata,
                    "tfidf": d.tfidf,
                    "length": d.length,
                }
                for d in self.docs
            ],
        }
        self.path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    # ---------- Core ops ----------
    def clear(self) -> None:
        """Remove all stored documents and reset counters."""
        self.docs = []
        self.df = {}
        self.doc_count = 0
        self._save()

    def _recompute_tfidf(self) -> None:
        """Recompute TF-IDF vectors and norms for all docs from current DF stats."""
        import math

        N = max(1, self.doc_count)
        idf: Dict[str, float] = {}
        for term, df in self.df.items():
            # Smooth idf to avoid div-by-zero; classic idf
            idf[term] = math.log((1 + N) / (1 + df)) + 1.0

        for d in self.docs:
            term_counts: Dict[str, int] = {}
            for tok in _simple_tokenize(d.text):
                term_counts[tok] = term_counts.get(tok, 0) + 1
            if not term_counts:
                d.tfidf = {}
                d.length = 0.0
                continue

            max_tf = max(term_counts.values())
            vec: Dict[str, float] = {}
            for term, tf in term_counts.items():
                # Augmented TF to reduce bias toward longer docs
                norm_tf = 0.5 + 0.5 * (tf / max_tf)
                vec[term] = norm_tf * idf.get(term, 1.0)

            # L2 norm
            norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
            d.tfidf = vec
            d.length = norm

    def add_texts(self, texts: Iterable[str], metadatas: Optional[Iterable[Dict[str, Any]]] = None) -> int:
        """Add multiple text chunks to the store. Returns number added."""
        if metadatas is None:
            metadatas = [{} for _ in texts]
        count = 0
        for idx, (text, meta) in enumerate(zip(texts, metadatas)):
            text = text or ""
            doc_id = f"d{self.doc_count + idx + 1}"
            # Update global DF with unique terms in this doc
            unique_terms = set(_simple_tokenize(text))
            for t in unique_terms:
                self.df[t] = self.df.get(t, 0) + 1
            self.docs.append(LexicalDoc(id=doc_id, text=text, metadata=dict(meta or {})))
            count += 1
        self.doc_count += count
        # Recompute TF-IDF for all docs (simple but fine for small stores)
        self._recompute_tfidf()
        self._save()
        return count

    def _cosine_sim(self, qv: Dict[str, float], qnorm: float, dv: Dict[str, float], dnorm: float) -> float:
        """Compute cosine similarity between query and document vectors."""
        if qnorm == 0.0 or dnorm == 0.0:
            return 0.0
        # Sparse dot product
        dot = 0.0
        for term, qw in qv.items():
            dvw = dv.get(term)
            if dvw is not None:
                dot += qw * dvw
        return dot / (qnorm * dnorm)

    def _tfidf_query(self, query: str) -> Tuple[Dict[str, float], float]:
        """Build a TF-IDF representation for the query string."""
        import math

        term_counts: Dict[str, int] = {}
        for tok in _simple_tokenize(query or ""):
            term_counts[tok] = term_counts.get(tok, 0) + 1
        if not term_counts:
            return {}, 0.0

        N = max(1, self.doc_count)
        idf: Dict[str, float] = {}
        for term, df in self.df.items():
            idf[term] = math.log((1 + N) / (1 + df)) + 1.0

        max_tf = max(term_counts.values())
        qv: Dict[str, float] = {}
        for term, tf in term_counts.items():
            norm_tf = 0.5 + 0.5 * (tf / max_tf)
            qv[term] = norm_tf * idf.get(term, 1.0)

        qnorm = math.sqrt(sum(v * v for v in qv.values())) or 1.0
        return qv, qnorm

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Return top-k matches with scores and metadata."""
        qv, qn = self._tfidf_query(query)
        scored: List[Tuple[float, LexicalDoc]] = []
        for d in self.docs:
            sim = self._cosine_sim(qv, qn, d.tfidf, d.length)
            if sim > 0:
                scored.append((sim, d))
        scored.sort(key=lambda x: x[0], reverse=True)
        results: List[Dict[str, Any]] = []
        for score, d in scored[: max(1, k)]:
            results.append({
                "id": d.id,
                "text": d.text,
                "metadata": d.metadata,
                "score": score,
            })
        return results

    # ---------- Import helpers ----------
    def import_path(self, path: Path) -> int:
        """Import supported file formats from the given path into the store."""
        """Import chunks from a directory or file.

        Supported:
        - .txt / .md: each blank-line separated paragraph as a chunk
        - .jsonl: each line is a JSON object; use 'text' or 'content' fields
        - .json: array of {text, metadata} or object with 'chunks': [...]
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(str(path))

        files: List[Path]
        if path.is_dir():
            files = sorted([p for p in path.rglob("*") if p.suffix.lower() in {".txt", ".md", ".json", ".jsonl"}])
        else:
            files = [path]

        total = 0
        for f in files:
            try:
                if f.suffix.lower() in {".txt", ".md"}:
                    text = f.read_text(encoding="utf-8", errors="ignore")
                    chunks = [c.strip() for c in text.split("\n\n") if c.strip()]
                    total += self.add_texts(chunks, metadatas=[{"source": str(f)} for _ in chunks])
                elif f.suffix.lower() == ".jsonl":
                    added = 0
                    with f.open("r", encoding="utf-8", errors="ignore") as fh:
                        for line in fh:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                obj = json.loads(line)
                                text = obj.get("text") or obj.get("content") or obj.get("chunk") or ""
                                meta = obj.get("metadata") or {k: v for k, v in obj.items() if k not in {"text", "content", "chunk"}}
                                if text:
                                    added += self.add_texts([text], metadatas=[{**meta, "source": str(f)}])
                            except Exception:
                                continue
                    total += added
                elif f.suffix.lower() == ".json":
                    data = json.loads(f.read_text(encoding="utf-8", errors="ignore"))
                    chunks: List[str] = []
                    metas: List[Dict[str, Any]] = []
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, str):
                                chunks.append(item)
                                metas.append({"source": str(f)})
                            elif isinstance(item, dict):
                                text = item.get("text") or item.get("content") or item.get("chunk") or ""
                                if text:
                                    chunks.append(text)
                                    meta = item.get("metadata") or {k: v for k, v in item.items() if k not in {"text", "content", "chunk", "metadata"}}
                                    meta["source"] = str(f)
                                    metas.append(meta)
                    elif isinstance(data, dict):
                        # look for 'chunks'
                        if isinstance(data.get("chunks"), list):
                            for c in data.get("chunks"):
                                if isinstance(c, str):
                                    chunks.append(c)
                                    metas.append({"source": str(f)})
                                elif isinstance(c, dict):
                                    txt = c.get("text") or c.get("content") or c.get("chunk") or ""
                                    if txt:
                                        chunks.append(txt)
                                        meta = c.get("metadata") or {k: v for k, v in c.items() if k not in {"text", "content", "chunk", "metadata"}}
                                        meta["source"] = str(f)
                                        metas.append(meta)
                    if chunks:
                        total += self.add_texts(chunks, metas)
            except Exception:
                logger.exception("Failed importing from %s", f)

        return total

    def stats(self) -> Dict[str, Any]:
        """Return summary statistics describing the lexical store."""
        return {
            "engine": self.meta.get("engine", "lexical"),
            "docs": self.doc_count,
            "path": str(self.path),
            "vocab_size": len(self.df),
        }


def get_work_history_store(path: Path) -> LexicalVectorStore:
    """Instantiate a lexical store that reads/writes to the supplied path."""
    return LexicalVectorStore(path)
