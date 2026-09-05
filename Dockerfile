FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# --timeout/--retries: requirements.txt pulls in a couple of large wheels
# (e.g. torch, via sentence-transformers for the optional cross-encoder
# reranker) — on a slow or flaky connection, pip's short default read
# timeout can kill an otherwise-fine download mid-stream. This makes a slow
# network take longer instead of failing outright; it's a no-op on a fast one.
#
# torch first, from PyTorch's own CPU-only index: nothing here uses a GPU,
# and the default PyPI wheel bundles the full CUDA runtime (multiple gigabytes
# of nvidia-* packages) for no benefit — the CPU build is a fraction of the
# size and download. The version must match requirements.txt's torch== pin;
# once it's installed, `pip install -r requirements.txt` below is satisfied
# by it (PEP 440 `==` matches a local-version-tagged install like `+cpu`) and
# won't try to replace it with the GPU build from the default index.
RUN pip install --no-cache-dir --timeout=120 --retries=10 \
    torch==2.13.0 --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir --timeout=120 --retries=10 -r requirements.txt

COPY . .

RUN mkdir -p uploads && chmod +x docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
