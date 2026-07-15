"""
BM25 sparse encoder for hybrid dense+sparse search in Qdrant.

Fits on the full corpus at ingestion time, saves vocabulary+IDF to disk,
and at query time transforms a text into a sparse vector (indices, values)
compatible with Qdrant's SparseVector format.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from rank_bm25 import BM25Okapi
    _BM25_AVAILABLE = True
except ImportError:
    BM25Okapi = None  # type: ignore[assignment,misc]
    _BM25_AVAILABLE = False


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-zA-ZÀ-ÿА-яёЁĀ-ɏ]+", text.lower())


class BM25Encoder:
    """Sparse BM25 encoder — fit on corpus, encode individual docs/queries."""

    def __init__(self) -> None:
        self._bm25: Optional[BM25Okapi] = None
        self._vocab: Dict[str, int] = {}       # token → index
        self._idf: Dict[int, float] = {}        # index → IDF weight

    def fit(self, texts: List[str]) -> None:
        if not _BM25_AVAILABLE:
            raise ImportError("rank_bm25 not installed — run: pip install rank-bm25")
        tokenized = [_tokenize(t) for t in texts]
        self._bm25 = BM25Okapi(tokenized)

        # Build vocab from all unique tokens
        all_tokens = sorted({tok for doc in tokenized for tok in doc})
        self._vocab = {tok: i for i, tok in enumerate(all_tokens)}

        # Extract IDF from BM25 internals
        self._idf = {}
        for tok, idx in self._vocab.items():
            if tok in self._bm25.idf:
                self._idf[idx] = float(self._bm25.idf[tok])

    def encode_document(self, text: str) -> Tuple[List[int], List[float]]:
        """Return (indices, values) sparse vector for a single document."""
        if self._bm25 is None:
            raise RuntimeError("BM25Encoder not fitted — call fit() first")

        tokens = _tokenize(text)
        tf: Dict[int, float] = {}
        for tok in tokens:
            idx = self._vocab.get(tok)
            if idx is not None:
                tf[idx] = tf.get(idx, 0.0) + 1.0

        indices, values = [], []
        for idx, count in tf.items():
            idf = self._idf.get(idx, 0.0)
            if idf > 0:
                indices.append(idx)
                values.append(float(count * idf))

        return indices, values

    def encode_query(self, text: str) -> Tuple[List[int], List[float]]:
        """Same as encode_document — BM25 query encoding is TF×IDF."""
        return self.encode_document(text)

    def save(self, path: str) -> None:
        data = {
            "vocab": self._vocab,
            "idf": {str(k): v for k, v in self._idf.items()},
        }
        Path(path).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def load(self, path: str) -> None:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self._vocab = data["vocab"]
        self._idf = {int(k): v for k, v in data["idf"].items()}
        self._bm25 = True  # sentinel — not needed after load

    @property
    def vocab_size(self) -> int:
        return len(self._vocab)


_encoder: Optional[BM25Encoder] = None


def get_bm25_encoder(vocab_path: Optional[str] = None) -> Optional[BM25Encoder]:
    """Return singleton BM25Encoder if vocab file exists, else None (graceful degradation)."""
    global _encoder
    if _encoder is not None:
        return _encoder

    path = vocab_path or "data/bm25_vocab.json"
    if Path(path).exists():
        try:
            _encoder = BM25Encoder()
            _encoder.load(path)
            return _encoder
        except Exception:
            return None

    return None
