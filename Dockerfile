ARG BASE_IMAGE=pytorch/pytorch:2.9.1-cuda12.8-cudnn9-runtime@sha256:7b324d212a4450795b49edba9949b7cdc72429148a64e974334bfe5774d51385
FROM ${BASE_IMAGE}

WORKDIR /app
COPY src/one_more_run /app/one_more_run

RUN useradd --create-home --uid 10001 worker \
    && chown -R worker:worker /app

USER worker
ENV PYTHONUNBUFFERED=1
EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=2)"]

CMD ["python", "-m", "one_more_run.worker"]
