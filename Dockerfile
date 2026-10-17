# Używamy oficjalnego, lekkiego obrazu Pythona
FROM python:3.11-slim

# Ustawiamy katalog roboczy w kontenerze
WORKDIR /app

# Kopiujemy wymagania i instalujemy biblioteki
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopiujemy całą zawartość projektu (backend i frontend) do kontenera
COPY . .

# Otwieramy port, na którym działa FastAPI
EXPOSE 8000

# Komenda startowa uruchamiająca serwer
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]