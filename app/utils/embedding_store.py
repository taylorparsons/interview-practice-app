import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np

from openai import OpenAI

logger = logging.getLogger(__name__)


def _read_legacy_lexical_json(path: Path) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Load legacy lexical store data for migration into FAISS."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        docs = data.get("docs") or []
        texts: List[str] = []
        metas: List[Dict[str, Any]] = []
        for d in docs:
            texts.append(d.get("text") or "")
            metas.append(d.get("metadata") or {})
        return texts, metas
    except Exception:
        return [], []


@dataclass
class FaissDoc:
    """Lightweight representation of a stored FAISS document."""
    id: str
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class FaissVectorStore:
    """Embeddings-based vector store backed by FAISS (cosine similarity).

    Persists FAISS index to `index_path` and document metadata to `meta_path`.
    """

    def __init__(self, index_path: Path, meta_path: Path, embedding_model: str, api_key: str, legacy_json: Optional[Path] = None):
        """Initialise the FAISS-backed store with persistence and embedding config."""
        self.index_path = Path(index_path)
        self.meta_path = Path(meta_path)
        self.embedding_model = embedding_model
        self.client = OpenAI(api_key=api_key) if api_key else None
        self.docs: List[FaissDoc] = []
        self.dim: Optional[int] = None
        self.count: int = 0
        self.meta: Dict[str, Any] = {
            "engine": "faiss",
            "version": 1,
            "embedding_model": embedding_model,
        }

        self._index = None  # type: ignore
        self._load_or_init(legacy_json)

    # ---------- Internal: persistence ----------
    def _load_or_init(self, legacy_json: Optional[Path]) -> None:
        """Load an existing FAISS index or bootstrap an empty store."""
        import faiss  # type: ignore

        if self.index_path.exists() and self.meta_path.exists():
            try:
                meta = json.loads(self.meta_path.read_text(encoding="utf-8"))
                self.meta = meta.get("meta", self.meta)
                self.dim = int(meta.get("dim")) if meta.get("dim") is not None else None
                doc_items = meta.get("docs", [])
                self.docs = [FaissDoc(id=d["id"], text=d.get("text", ""), metadata=d.get("metadata", {})) for d in doc_items]
                self.count = len(self.docs)
                self._index = faiss.read_index(str(self.index_path))
                return
            except Exception:
                logger.exception("Failed to load FAISS store; starting fresh")

        # Fresh index: try migration from legacy JSON if provided
        self._index = None
        self.docs = []
        self.count = 0
        self.dim = None
        if legacy_json and Path(legacy_json).exists():
            texts, metas = _read_legacy_lexical_json(legacy_json)
            if texts:
                logger.info("Migrating %s legacy chunks into FAISS", len(texts))
                self.add_texts(texts, metas)
                return

        # Otherwise, remain empty until first add

    def _save(self) -> None:
        """Persist the FAISS index and metadata to disk."""
        import faiss  # type: ignore

        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        if self._index is None:
            # empty index placeholder
            dim = self.dim or 0
            self._index = faiss.IndexFlatIP(dim) if dim > 0 else faiss.IndexFlatIP(1)
        faiss.write_index(self._index, str(self.index_path))
        payload = {
            "meta": self.meta,
            "dim": self.dim or 0,
            "docs": [{"id": d.id, "text": d.text, "metadata": d.metadata} for d in self.docs],
        }
        self.meta_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    # ---------- Embeddings helpers ----------
    def _embed(self, texts: List[str]) -> np.ndarray:
        """Compute normalised embeddings for the supplied text batch."""
        if not self.client:
            raise RuntimeError("OpenAI client not configured for embeddings")
        # OpenAI Embeddings API call
        resp = self.client.embeddings.create(model=self.embedding_model, input=texts)
        arr = np.array([d.embedding for d in resp.data], dtype=np.float32)
        # Normalize for cosine similarity via inner product
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        arr = arr / norms
        if self.dim is None:
            self.dim = int(arr.shape[1])
        return arr

    def _ensure_index(self) -> None:
        """Create the FAISS index if it has not yet been initialised."""
        import faiss  # type: ignore

        if self._index is None:
            dim = self.dim or 1536
            self._index = faiss.IndexFlatIP(dim)

    # ---------- Public API ----------
    def clear(self) -> None:
        """Remove all documents and reset the FAISS index."""
        import faiss  # type: ignore

        self.docs = []
        self.count = 0
        self.dim = None
        self._index = faiss.IndexFlatIP(1)
        self._save()

    def add_texts(self, texts: Iterable[str], metadatas: Optional[Iterable[Dict[str, Any]]] = None) -> int:
        """Add text chunks plus metadata to the index, returning the count stored."""
        texts = list(texts)
        if not texts:
            return 0
        metas = list(metadatas) if metadatas is not None else [{} for _ in texts]
        self._ensure_index()
        added = 0
        start = self.count
        B = 64  # batch size
        for off in range(0, len(texts), B):
            batch_t = texts[off: off + B]
            batch_m = metas[off: off + B]
            vecs = self._embed(batch_t)
            # IDs + docs
            for i, (t, m) in enumerate(zip(batch_t, batch_m)):
                self.docs.append(FaissDoc(id=f"d{start + added + i + 1}", text=t or "", metadata=dict(m or {})))
            self._index.add(vecs)
            added += len(batch_t)
        self.count = len(self.docs)
        self._save()
        return added

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve the top-k matching documents for a query string."""
        if not self.docs or self._index is None:
            return []
        q = (query or "").strip()
        if not q:
            return []
        qv = self._embed([q])
        D, I = self._index.search(qv, max(1, k))
        results: List[Dict[str, Any]] = []
        scores = D[0].tolist() if len(D) else []
        inds = I[0].tolist() if len(I) else []
        for score, idx in zip(scores, inds):
            if idx < 0 or idx >= len(self.docs):
                continue
            d = self.docs[idx]
            results.append({
                "id": d.id,
                "text": d.text,
                "metadata": d.metadata,
                "score": float(score),
            })
        return results

    # Import chunked content from filesystem
    def import_path(self, path: Path) -> int:
        """Import supported file types from a directory or file into the store."""
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
                    batch_texts: List[str] = []
                    batch_meta: List[Dict[str, Any]] = []
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
                                    batch_texts.append(text)
                                    batch_meta.append({**meta, "source": str(f)})
                            except Exception:
                                continue
                    if batch_texts:
                        total += self.add_texts(batch_texts, batch_meta)
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
        """Return diagnostic information about the current FAISS store."""
        return {
            "engine": self.meta.get("engine", "faiss"),
            "docs": self.count,
            "path": str(self.index_path),
            "meta": str(self.meta_path),
            "dim": self.dim or 0,
            "model": self.meta.get("embedding_model"),
        }


def get_work_history_store(legacy_json_path: Path) -> FaissVectorStore:
    """Factory that returns a FAISS store rooted beside the legacy JSON file."""
    base = Path(legacy_json_path).parent
    stem = Path(legacy_json_path).stem
    index_path = base / f"{stem}.faiss"
    meta_path = base / f"{stem}_meta.json"

    # Late import to avoid circular import to config
    from app.config import OPENAI_EMBEDDING_MODEL, OPENAI_API_KEY

    store = FaissVectorStore(index_path=index_path, meta_path=meta_path,
                             embedding_model=OPENAI_EMBEDDING_MODEL, api_key=OPENAI_API_KEY,
                             legacy_json=legacy_json_path)
    return store
