FROM python:3.12-slim
WORKDIR /app
RUN pip install uv --no-cache-dir
COPY pyproject.toml .
RUN uv pip install --system -e . --no-cache
COPY . .
EXPOSE 8001
CMD ["uvicorn", "quant_engine.api:app", "--host", "0.0.0.0", "--port", "8001"]
