import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from google import genai
from google.genai import types
import base64

app = FastAPI()

# Pobieramy klucz Gemini
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("Brak zmiennej środowiskowej GEMINI_API_KEY")

client = genai.Client(api_key=api_key)

class ChatRequest(BaseModel):
    messages: list

@app.post("/api/chat")
async def chat_with_gemini(req: ChatRequest):
    try:
        contents = []
        for m in req.messages:
            author = m.get("author", "Użytkownik")
            text = m.get("content", "")
            role = m.get("role", "user")
            file_data = m.get("file_data")  # Opcjonalny załącznik (Base64)
            file_mime = m.get("file_mime")  # Typ MIME pliku (np. image/png)

            # Jeśli wiadomość zawierała plik/obrazek, przekazujemy go do Gemini przez types.Part
            parts = []
            if file_data and file_mime:
                binary_data = base64.b64decode(file_data)
                parts.append(types.Part.from_bytes(data=binary_data, mime_type=file_mime))
            
            if text:
                prefix = "Gemini: " if role == "model" else f"{author}: "
                parts.append(prefix + text)

            contents.append(parts if len(parts) > 1 else (parts[0] if parts else ""))

        if not contents:
            raise HTTPException(status_code=400, detail="Brak wiadomości do przetworzenia.")

        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=contents,
        )
        
        return {"response": response.text}

    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
            raise HTTPException(status_code=429, detail="Wyczerpano darmowy limit zapytań do Gemini. Odczekaj chwilę.")
        raise HTTPException(status_code=500, detail=error_str)

# Serwowanie frontendu jako plików statycznych pod /static oraz strona główna
# Zmień tę linijkę w main.py:
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def read_index():
    return FileResponse("frontend/index.html")