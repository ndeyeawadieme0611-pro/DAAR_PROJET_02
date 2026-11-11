FROM python:3.12-slim
WORKDIR /srv
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# main.py importe "app.*" et "scripts.build_index" (tokenize) : on copie les deux
COPY backend/app ./app
COPY backend/scripts ./scripts
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
