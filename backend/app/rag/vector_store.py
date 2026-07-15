"""FAISS vector store with persistence and concurrency guards."""

import json
import os
import threading
from collections.abc import Mapping
from typing import Any

import faiss
import numpy as np

from app.utils.logger import get_logger

logger = get_logger("vector_store")


class VectorStore:
    def __init__(
        self,
        dim: int,
        persist_dir: str | None = None,
        embedder=None,
        mismatch_policy: str = "error",
    ):
        if mismatch_policy not in {"error", "rebuild"}:
            raise ValueError("mismatch_policy must be 'error' or 'rebuild'")
        self.dim = dim
        self.index = faiss.IndexFlatIP(dim)
        self.texts: list[str] = []
        self.metadata: list[dict] = []
        self.persist_dir = persist_dir
        # Optional embedder whose fitted state (for example BM25 vocab/IDF) is
        # persisted so reloaded vectors and freshly embedded queries share the
        # same lexical space.
        self.embedder = embedder
        self.mismatch_policy = mismatch_policy
        self.last_load_status = "not_loaded"
        self._loaded = False
        self._lock = threading.RLock()

    def _index_manifest(self) -> dict:
        embedder_config = (
            self.embedder.get_index_config()
            if self.embedder is not None
            else {
                "schema_version": 2,
                "embedder": "external",
                "model": "external",
                "backend": "external",
                "dim": self.dim,
                "normalization": "l2",
            }
        )
        fingerprint = (
            self.embedder.get_index_fingerprint()
            if self.embedder is not None
            else self._fingerprint(embedder_config)
        )
        return {
            "schema_version": 2,
            "dim": self.dim,
            "embedder": embedder_config,
            "fingerprint": fingerprint,
        }

    @staticmethod
    def _fingerprint(payload: dict) -> str:
        import hashlib

        encoded = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def add(
        self,
        embeddings: np.ndarray,
        texts: list[str],
        metadata: list[dict] | None = None,
    ):
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)
        if embeddings.shape[0] != len(texts):
            raise ValueError(
                "VectorStore.add received mismatched embeddings/texts lengths: "
                f"{embeddings.shape[0]} != {len(texts)}"
            )
        if metadata is not None and len(metadata) != len(texts):
            raise ValueError(
                "VectorStore.add received mismatched metadata/texts lengths: "
                f"{len(metadata)} != {len(texts)}"
            )

        embeddings = np.ascontiguousarray(embeddings, dtype="float32")
        faiss.normalize_L2(embeddings)
        with self._lock:
            self.index.add(embeddings)
            self.texts.extend(texts)
            self.metadata.extend(
                metadata if metadata is not None else [{}] * len(texts)
            )
            total = self.index.ntotal
        logger.info(f"VectorStore: added {len(texts)} items, total={total}")

    @staticmethod
    def _metadata_matches(metadata: dict, metadata_filter: Mapping | None) -> bool:
        if not metadata_filter:
            return True
        for key, expected in metadata_filter.items():
            if expected in (None, "", [], {}):
                continue
            actual = metadata.get(key)
            if isinstance(expected, (list, tuple, set)):
                if isinstance(actual, (list, tuple, set)):
                    if not set(actual).intersection(set(expected)):
                        return False
                elif actual not in expected:
                    return False
            elif isinstance(actual, (list, tuple, set)):
                if expected not in actual:
                    return False
            elif actual != expected:
                return False
        return True

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        metadata_filter: Mapping | None = None,
        min_score: float | None = None,
    ) -> list[dict]:
        if top_k <= 0:
            return []
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        query_embedding = np.ascontiguousarray(query_embedding, dtype="float32")
        faiss.normalize_L2(query_embedding)

        with self._lock:
            ntotal = self.index.ntotal
            if ntotal == 0:
                return []
            k = ntotal if metadata_filter else min(top_k, ntotal)
            scores, indices = self.index.search(query_embedding, k)
            texts = list(self.texts)
            metadata_list = [dict(meta) for meta in self.metadata]

        results = []
        for score, idx in zip(scores[0], indices[0], strict=False):
            if idx < 0:
                continue
            if idx >= len(texts) or idx >= len(metadata_list):
                logger.warning(
                    "VectorStore invariant violation during search: "
                    f"idx={idx}, texts={len(texts)}, metadata={len(metadata_list)}"
                )
                continue
            score = float(score)
            if min_score is not None and score < min_score:
                continue
            metadata = metadata_list[idx]
            if not self._metadata_matches(metadata, metadata_filter):
                continue
            results.append(
                {
                    "text": texts[idx],
                    "score": score,
                    "metadata": metadata,
                    "index": int(idx),
                }
            )
            if len(results) >= top_k:
                break
        return results

    def save(self, path: str | None = None):
        """Persist the index, texts, metadata, and embedder state to disk."""
        save_dir = path or self.persist_dir
        if not save_dir:
            logger.warning("No persist_dir configured, skipping save")
            return

        os.makedirs(save_dir, exist_ok=True)
        with self._lock:
            self._write_index_atomic(self.index, os.path.join(save_dir, "faiss.index"))
            self._write_json_atomic(os.path.join(save_dir, "texts.json"), self.texts)
            self._write_json_atomic(
                os.path.join(save_dir, "metadata.json"), self.metadata
            )
            self._write_json_atomic(
                os.path.join(save_dir, "config.json"), self._index_manifest()
            )

            if self.embedder is not None:
                state = self.embedder.get_state()
                state_path = os.path.join(save_dir, "embedder_state.json")
                if state:
                    self._write_json_atomic(state_path, state)
                elif os.path.exists(state_path):
                    os.remove(state_path)
            total = self.index.ntotal

        logger.info(f"VectorStore saved to {save_dir}: {total} vectors")

    def load(self, path: str | None = None) -> bool:
        """Load persisted vector store data from disk."""
        load_dir = path or self.persist_dir
        if not load_dir:
            return False

        index_path = os.path.join(load_dir, "faiss.index")
        texts_path = os.path.join(load_dir, "texts.json")
        meta_path = os.path.join(load_dir, "metadata.json")
        config_path = os.path.join(load_dir, "config.json")

        required_paths = [index_path, texts_path, meta_path, config_path]
        if not all(os.path.exists(p) for p in required_paths):
            self.last_load_status = "empty"
            logger.info(f"No existing data at {load_dir}, starting fresh")
            return False

        try:
            with open(config_path, encoding="utf-8") as f:
                config = json.load(f)
            with open(texts_path, encoding="utf-8") as f:
                texts = json.load(f)
            with open(meta_path, encoding="utf-8") as f:
                metadata = json.load(f)

            if not isinstance(texts, list) or not isinstance(metadata, list):
                raise ValueError("VectorStore persistence payload is not list-shaped")
            if len(texts) != len(metadata):
                raise ValueError(
                    "VectorStore persistence is inconsistent: "
                    f"texts={len(texts)}, metadata={len(metadata)}"
                )

            expected = self._index_manifest()
            stored_fingerprint = config.get("fingerprint")
            if stored_fingerprint != expected["fingerprint"]:
                reason = (
                    "RAG index fingerprint mismatch: "
                    f"stored={stored_fingerprint or 'legacy/unversioned'}, "
                    f"expected={expected['fingerprint']}, "
                    f"stored_dim={config.get('dim')}, current_dim={self.dim}"
                )
                if self.mismatch_policy != "rebuild" or self.embedder is None:
                    self.last_load_status = "incompatible"
                    logger.error(f"{reason}; refusing to mix vector spaces")
                    return False

                logger.warning(f"{reason}; rebuilding from persisted chunk texts")
                embeddings = self.embedder.embed_batch(texts)
                self.rebuild(embeddings, texts, metadata)
                self._loaded = True
                self.last_load_status = "rebuilt"
                self.save(load_dir)
                return True

            index = faiss.read_index(index_path)
            if index.d != self.dim or index.ntotal != len(texts):
                raise ValueError(
                    "VectorStore persistence is inconsistent: "
                    f"index_dim={index.d}, expected_dim={self.dim}, "
                    f"index={index.ntotal}, texts={len(texts)}"
                )

            state_path = os.path.join(load_dir, "embedder_state.json")
            if self.embedder is not None and os.path.exists(state_path):
                with open(state_path, encoding="utf-8") as f:
                    self.embedder.load_state(json.load(f))

            with self._lock:
                self.index = index
                self.texts = texts
                self.metadata = metadata
                self._loaded = True
                self.last_load_status = "loaded"
                total = self.index.ntotal

            logger.info(f"VectorStore loaded from {load_dir}: {total} vectors")
            return True
        except Exception as e:
            self.last_load_status = "load_error"
            logger.error(f"Failed to load VectorStore: {e}")
            return False

    @property
    def size(self) -> int:
        with self._lock:
            return self.index.ntotal

    def snapshot(self) -> tuple[list[str], list[dict]]:
        """Return a consistent read snapshot for non-vector fallback search."""
        with self._lock:
            return list(self.texts), [dict(meta) for meta in self.metadata]

    def rebuild(
        self,
        embeddings: np.ndarray,
        texts: list[str],
        metadata: list[dict] | None = None,
    ):
        """Atomically replace the full index contents."""
        if not texts:
            self.clear()
            return
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)
        if embeddings.shape[0] != len(texts):
            raise ValueError(
                "VectorStore.rebuild received mismatched embeddings/texts lengths: "
                f"{embeddings.shape[0]} != {len(texts)}"
            )
        if metadata is not None and len(metadata) != len(texts):
            raise ValueError(
                "VectorStore.rebuild received mismatched metadata/texts lengths: "
                f"{len(metadata)} != {len(texts)}"
            )

        embeddings = np.ascontiguousarray(embeddings, dtype="float32")
        faiss.normalize_L2(embeddings)
        new_index = faiss.IndexFlatIP(self.dim)
        new_index.add(embeddings)
        with self._lock:
            self.index = new_index
            self.texts = list(texts)
            self.metadata = [dict(meta) for meta in (metadata or [{}] * len(texts))]
            total = self.index.ntotal
        logger.info(f"VectorStore rebuilt: {total} vectors")

    def clear(self):
        """Clear all in-memory data."""
        with self._lock:
            self.index = faiss.IndexFlatIP(self.dim)
            self.texts.clear()
            self.metadata.clear()
        logger.info("VectorStore cleared")

    @staticmethod
    def _write_json_atomic(path: str, payload: Any) -> None:
        tmp_path = f"{path}.tmp.{os.getpid()}"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        os.replace(tmp_path, path)

    @staticmethod
    def _write_index_atomic(index, path: str) -> None:
        tmp_path = f"{path}.tmp.{os.getpid()}"
        faiss.write_index(index, tmp_path)
        os.replace(tmp_path, path)
