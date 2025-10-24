# syntax=docker/dockerfile:1

ARG USE_CUDA=false
ARG USE_OLLAMA=false
ARG USE_SLIM=false
ARG USE_PERMISSION_HARDENING=false
ARG USE_CUDA_VER=cu128
ARG USE_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
ARG USE_RERANKING_MODEL=""
ARG USE_TIKTOKEN_ENCODING_NAME="cl100k_base"
ARG BUILD_HASH=dev-build
ARG UID=0
ARG GID=0

FROM --platform=$BUILDPLATFORM node:22-alpine3.20 AS frontend-build
ARG BUILD_HASH

WORKDIR /app

RUN apk add --no-cache git

COPY package.json package-lock.json ./
RUN npm ci

COPY postcss.config.js svelte.config.js tailwind.config.js tsconfig.json vite.config.ts ./
COPY static ./static
COPY src ./src
ENV APP_BUILD_HASH=${BUILD_HASH}
RUN npm run build

FROM python:3.11-slim-bookworm AS runtime

ARG USE_CUDA
ARG USE_OLLAMA
ARG USE_CUDA_VER
ARG USE_SLIM
ARG USE_PERMISSION_HARDENING
ARG USE_EMBEDDING_MODEL
ARG USE_RERANKING_MODEL
ARG USE_TIKTOKEN_ENCODING_NAME
ARG UID
ARG GID
ARG BUILD_HASH

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

ENV ENV=prod \
    PORT=8080 \
    USE_OLLAMA_DOCKER=${USE_OLLAMA} \
    USE_CUDA_DOCKER=${USE_CUDA} \
    USE_SLIM_DOCKER=${USE_SLIM} \
    USE_CUDA_DOCKER_VER=${USE_CUDA_VER} \
    USE_EMBEDDING_MODEL_DOCKER=${USE_EMBEDDING_MODEL} \
    USE_RERANKING_MODEL_DOCKER=${USE_RERANKING_MODEL}

ENV OLLAMA_BASE_URL="/ollama" \
    OPENAI_API_BASE_URL=""

ENV OPENAI_API_KEY="" \
    WEBUI_SECRET_KEY="" \
    SCARF_NO_ANALYTICS=true \
    DO_NOT_TRACK=true \
    ANONYMIZED_TELEMETRY=false

ENV WHISPER_MODEL="base" \
    WHISPER_MODEL_DIR="/app/backend/data/cache/whisper/models"

ENV RAG_EMBEDDING_MODEL="$USE_EMBEDDING_MODEL_DOCKER" \
    RAG_RERANKING_MODEL="$USE_RERANKING_MODEL_DOCKER" \
    SENTENCE_TRANSFORMERS_HOME="/app/backend/data/cache/embedding/models"

ENV TIKTOKEN_ENCODING_NAME="${USE_TIKTOKEN_ENCODING_NAME}" \
    TIKTOKEN_CACHE_DIR="/app/backend/data/cache/tiktoken"

ENV HF_HOME="/app/backend/data/cache/embedding/models" \
    HOME=/root

WORKDIR /app/backend

RUN if [ "$UID" -ne 0 ] || [ "$GID" -ne 0 ]; then \
    GROUP_ID="$GID"; \
    if [ "$GROUP_ID" -eq 0 ]; then \
        GROUP_ID="$UID"; \
    fi; \
    addgroup --gid "$GROUP_ID" app 2>/dev/null || true; \
    adduser --uid "$UID" --gid "$GROUP_ID" --home "$HOME" --disabled-password --no-create-home app; \
    fi

RUN mkdir -p "$HOME/.cache/chroma" && \
    echo -n 00000000-0000-0000-0000-000000000000 > "$HOME/.cache/chroma/telemetry_user_id"

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        build-essential \
        pandoc \
        gcc \
        netcat-openbsd \
        curl \
        jq \
        python3-dev \
        ffmpeg \
        libsm6 \
        libxext6 \
    && rm -rf /var/lib/apt/lists/*

COPY --chown=${UID}:${GID} ./backend/requirements.txt ./requirements.txt

RUN python -m pip install --no-cache-dir --upgrade pip && \
    python -m pip install --no-cache-dir "uv==0.5.11"

RUN set -eux; \
    USE_CUDA_LC=$(printf '%s' "${USE_CUDA:-}" | tr '[:upper:]' '[:lower:]'); \
    USE_SLIM_LC=$(printf '%s' "${USE_SLIM:-}" | tr '[:upper:]' '[:lower:]'); \
    if [ "$USE_CUDA_LC" = "true" ]; then \
        python -m pip install --no-cache-dir torch torchvision torchaudio --index-url "https://download.pytorch.org/whl/${USE_CUDA_DOCKER_VER}"; \
    else \
        python -m pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu; \
    fi; \
    uv pip install --system --no-cache-dir -r requirements.txt; \
    if [ "$USE_CUDA_LC" = "true" ] || [ "$USE_SLIM_LC" != "true" ]; then \
        python -c "import os; from sentence_transformers import SentenceTransformer; from faster_whisper import WhisperModel; SentenceTransformer(os.environ['RAG_EMBEDDING_MODEL'], device='cpu'); WhisperModel(os.environ['WHISPER_MODEL'], device='cpu', compute_type='int8', download_root=os.environ['WHISPER_MODEL_DIR'])"; \
    fi; \
    python -c "import os, tiktoken; tiktoken.get_encoding(os.environ['TIKTOKEN_ENCODING_NAME'])"

RUN mkdir -p /app/backend/data && \
    if [ "$UID" -ne 0 ] || [ "$GID" -ne 0 ]; then \
        chown -R "$UID":"$GID" /app/backend/data "$HOME"; \
    fi

RUN set -eux; \
    USE_OLLAMA_LC=$(printf '%s' "${USE_OLLAMA:-}" | tr '[:upper:]' '[:lower:]'); \
    if [ "$USE_OLLAMA_LC" = "true" ]; then \
        date +%s > /tmp/ollama_build_hash && \
        echo "Cache broken at timestamp: $(cat /tmp/ollama_build_hash)" && \
        curl -fsSL https://ollama.com/install.sh | sh && \
        rm -rf /var/lib/apt/lists/*; \
    fi

COPY --chown=${UID}:${GID} --from=frontend-build /app/build /app/build
COPY --chown=${UID}:${GID} --from=frontend-build /app/package.json /app/package.json

COPY --chown=${UID}:${GID} ./backend .

EXPOSE 8080

HEALTHCHECK CMD curl --silent --fail http://localhost:${PORT:-8080}/health | jq -ne 'input.status == true' || exit 1

RUN set -eux; \
    USE_PERMISSION_HARDENING_LC=$(printf '%s' "${USE_PERMISSION_HARDENING:-}" | tr '[:upper:]' '[:lower:]'); \
    if [ "$USE_PERMISSION_HARDENING_LC" = "true" ]; then \
        chgrp -R 0 /app /root || true; \
        chmod -R g+rwX /app /root || true; \
        find /app -type d -exec chmod g+s {} + || true; \
        find /root -type d -exec chmod g+s {} + || true; \
    fi

USER $UID:$GID

ENV WEBUI_BUILD_VERSION=${BUILD_HASH} \
    DOCKER=true

CMD ["bash", "start.sh"]
