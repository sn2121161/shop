FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . ./
RUN useradd --system --uid 10001 --create-home shop && chown -R shop:shop /app
USER shop
EXPOSE 5600
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5600"]
