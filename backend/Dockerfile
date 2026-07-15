# ============================================
# Stage 1: Builder
# ============================================
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

RUN sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' \
        /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ENV PIP_NO_CACHE_DIR=1
ENV HF_HOME=/opt/huggingface

COPY requirements.txt requirements-semantic.txt ./

RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install -r requirements-semantic.txt

ARG RAG_SEMANTIC_MODEL=BAAI/bge-small-zh-v1.5
ARG RAG_SEMANTIC_REVISION=7999e1d3359715c523056ef9478215996d62a620
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('${RAG_SEMANTIC_MODEL}', revision='${RAG_SEMANTIC_REVISION}', device='cpu')"

# ============================================
# Stage 2: Production
# ============================================
FROM python:3.12-slim-bookworm AS production

WORKDIR /app

ARG RAG_SEMANTIC_MODEL=BAAI/bge-small-zh-v1.5
ARG RAG_SEMANTIC_REVISION=7999e1d3359715c523056ef9478215996d62a620
ENV HF_HOME=/opt/huggingface \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    RAG_EMBEDDING_MODE=semantic \
    RAG_EMBEDDING_BACKEND=sentence_transformers \
    RAG_EMBEDDING_LOCAL_FILES_ONLY=true \
    RAG_SEMANTIC_FAILURE_POLICY=error \
    RAG_EMBEDDING_MODEL=${RAG_SEMANTIC_MODEL} \
    RAG_EMBEDDING_REVISION=${RAG_SEMANTIC_REVISION}

RUN sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' \
        /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y --no-install-recommends \
    curl \
    tini \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local /usr/local
COPY --from=builder /opt/huggingface /opt/huggingface

COPY app/ ./app/

RUN groupadd -r appuser && \
    useradd -r -g appuser -d /app -s /sbin/nologin appuser && \
    mkdir -p /app/data /app/output /app/logs && \
    chown -R appuser:appuser /app /opt/huggingface

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/ping || exit 1

ENTRYPOINT ["tini", "--"]

CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--limit-concurrency", "100", \
     "--limit-max-requests", "10000", \
     "--timeout-keep-alive", "65", \
     "--access-log", \
     "--log-level", "info"]
