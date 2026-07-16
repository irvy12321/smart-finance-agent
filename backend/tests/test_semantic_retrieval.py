import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import yaml

from app.rag import embed as embed_module
from app.rag.embed import BaseEmbedder, SemanticEmbedder
from app.rag.retriever import Retriever
from app.rag.vector_store import VectorStore

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class _NamedEmbedder(BaseEmbedder):
    def __init__(self, model: str, vectors: dict[str, list[float]] | None = None):
        self.model = model
        self.vectors = vectors or {}

    @property
    def dim(self) -> int:
        return 2

    def embed_text(self, text: str) -> np.ndarray:
        return np.asarray(self.vectors.get(text, [1.0, 0.0]), dtype=np.float32)

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        return np.asarray([self.embed_text(text) for text in texts], dtype=np.float32)

    def get_index_config(self) -> dict:
        return {**super().get_index_config(), "model": self.model, "backend": "fake"}


def test_production_deploy_uses_prebuilt_semantic_backend_image():
    compose = yaml.safe_load(
        (PROJECT_ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")
    )
    backend = compose["services"]["backend"]
    environment = dict(item.split("=", 1) for item in backend["environment"])

    assert backend["image"] == "sfa-backend:latest"
    assert environment["RAG_EMBEDDING_MODE"] == "semantic"
    assert environment["RAG_EMBEDDING_LOCAL_FILES_ONLY"] == "true"
    assert environment["RAG_SEMANTIC_FAILURE_POLICY"] == "error"
    assert environment["RAG_EMBEDDING_MODEL"] == "BAAI/bge-small-zh-v1.5"

    workflow = (PROJECT_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    deploy_section = workflow.split("\n  deploy:\n", 1)[1]
    assert "name: sfa-backend-image" in workflow
    assert "outputs: type=docker,dest=/tmp/sfa-backend.tar" in workflow
    assert "gzip -dc /tmp/sfa-backend.tar.gz | docker load" in deploy_section
    assert (
        "docker compose -f docker-compose.prod.yml build backend" not in deploy_section
    )


def test_semantic_embedder_applies_instruction_to_queries_only():
    embedder = SemanticEmbedder.__new__(SemanticEmbedder)
    embedder._query_instruction = "检索："
    seen = []

    def encode(texts):
        seen.extend(texts)
        return np.asarray([[1.0, 0.0] for _ in texts], dtype=np.float32)

    embedder._encode = encode

    embedder.embed_text("文档内容")
    embedder.embed_query("口语改写")

    assert seen == ["文档内容", "检索：口语改写"]


def test_same_dimension_different_model_index_is_rejected(tmp_path):
    first = _NamedEmbedder("model-a")
    store = VectorStore(dim=2, persist_dir=str(tmp_path), embedder=first)
    store.add(first.embed_batch(["document"]), ["document"])
    store.save()

    second = _NamedEmbedder("model-b")
    reloaded = VectorStore(dim=2, persist_dir=str(tmp_path), embedder=second)

    assert reloaded.load() is False
    assert reloaded.size == 0
    assert reloaded.last_load_status == "incompatible"


def test_legacy_index_is_safely_rebuilt_from_persisted_text(tmp_path):
    old = _NamedEmbedder("old-model", {"document": [1.0, 0.0]})
    store = VectorStore(dim=2, persist_dir=str(tmp_path), embedder=old)
    store.add(old.embed_batch(["document"]), ["document"], [{"id": "doc"}])
    store.save()
    (tmp_path / "config.json").write_text(json.dumps({"dim": 2}), encoding="utf-8")

    current = _NamedEmbedder("new-model", {"document": [0.0, 1.0]})
    reloaded = VectorStore(
        dim=2,
        persist_dir=str(tmp_path),
        embedder=current,
        mismatch_policy="rebuild",
    )

    assert reloaded.load() is True
    assert reloaded.last_load_status == "rebuilt"
    assert (
        reloaded.search(np.asarray([0.0, 1.0], dtype=np.float32), top_k=1)[0][
            "metadata"
        ]["id"]
        == "doc"
    )
    manifest = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert manifest["fingerprint"] == current.get_index_fingerprint()


def test_retriever_uses_query_encoder(monkeypatch, tmp_path):
    class QueryAwareEmbedder(_NamedEmbedder):
        def __init__(self):
            super().__init__(
                "query-aware",
                {"target": [1.0, 0.0], "other": [0.0, 1.0]},
            )
            self.query_calls = []

        def embed_query(self, text: str) -> np.ndarray:
            self.query_calls.append(text)
            return np.asarray([1.0, 0.0], dtype=np.float32)

    monkeypatch.setattr("app.rag.retriever._get_persist_dir", lambda: str(tmp_path))
    monkeypatch.setattr(
        "app.rag.retriever.create_reranker",
        lambda: SimpleNamespace(is_available=False),
    )
    embedder = QueryAwareEmbedder()
    retriever = Retriever(embedder=embedder)
    retriever.add_texts(["target", "other"])

    results = retriever.retrieve("paraphrased query", top_k=1)

    assert embedder.query_calls == ["paraphrased query"]
    assert results[0]["text"] == "target"


def test_semantic_factory_failure_is_explicit(monkeypatch):
    config = SimpleNamespace(
        mode="semantic",
        model_name="missing-model",
        model_revision="revision",
        backend="sentence_transformers",
        device="cpu",
        batch_size=8,
        query_instruction="query: ",
        local_files_only=True,
        failure_policy="error",
    )
    monkeypatch.setattr(embed_module, "get_embedding_config", lambda: config)
    monkeypatch.setattr(
        embed_module, "get_rag_config", lambda: SimpleNamespace(embedding_dim=384)
    )

    class BrokenSemanticEmbedder:
        def __init__(self, **kwargs):
            raise ImportError("model files unavailable")

    monkeypatch.setattr(embed_module, "SemanticEmbedder", BrokenSemanticEmbedder)

    with pytest.raises(RuntimeError, match="Semantic embedding requested"):
        embed_module.create_embedder()


def test_embedding_environment_overrides_local_ci_yaml(monkeypatch):
    from app.infrastructure.config import get_embedding_config

    monkeypatch.setenv("RAG_EMBEDDING_MODE", "semantic")
    monkeypatch.setenv("RAG_EMBEDDING_LOCAL_FILES_ONLY", "true")
    monkeypatch.setenv("RAG_SEMANTIC_FAILURE_POLICY", "error")

    config = get_embedding_config()

    assert config.mode == "semantic"
    assert config.local_files_only is True
    assert config.failure_policy == "error"


def test_semantic_factory_fallback_is_observable(monkeypatch):
    config = SimpleNamespace(
        mode="semantic",
        model_name="missing-model",
        model_revision="revision",
        backend="sentence_transformers",
        device="cpu",
        batch_size=8,
        query_instruction="query: ",
        local_files_only=True,
        failure_policy="lexical_fallback",
    )
    monkeypatch.setattr(embed_module, "get_embedding_config", lambda: config)
    monkeypatch.setattr(
        embed_module, "get_rag_config", lambda: SimpleNamespace(embedding_dim=384)
    )

    class BrokenSemanticEmbedder:
        def __init__(self, **kwargs):
            raise ImportError("model files unavailable")

    monkeypatch.setattr(embed_module, "SemanticEmbedder", BrokenSemanticEmbedder)

    fallback = embed_module.create_embedder()
    status = fallback.get_runtime_status()

    assert status["semantic_enabled"] is False
    assert status["degraded"] is True
    assert "model files unavailable" in status["degradation_reason"]
