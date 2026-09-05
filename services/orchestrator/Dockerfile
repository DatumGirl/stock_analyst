FROM python:3.12-slim
WORKDIR /app
RUN pip install uv --no-cache-dir
COPY pyproject.toml .
RUN uv pip install --system -e . --no-cache
COPY . .
EXPOSE 8002
CMD ["uvicorn", "orchestrator.api:app", "--host", "0.0.0.0", "--port", "8002"]
