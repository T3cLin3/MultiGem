FROM python:3.11-slim

WORKDIR /app

# Kopiujemy wymagania i instalujemy
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopiujemy zawartość folderu backend bezpośrednio do /app
COPY backend/ .
# Kopiujemy też frontend, żeby pliki statyczne były na miejscu
COPY frontend/ ./frontend/

EXPOSE 8000

# Skoro main.py jest w /app, uruchamiamy po prostu main:app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]