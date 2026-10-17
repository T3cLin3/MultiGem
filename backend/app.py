import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai

app = FastAPI()

# Włączamy CORS, żeby frontend mógł bezpiecznie komunikować się z backendem
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pobieramy klucz Gemini (zmienna środowiskowa)
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("Brak zmiennej środowiskowej GEMINI_API_KEY")

client = genai.Client(api_key=api_key)

class ChatRequest(BaseModel):
    messages: list  # Pełna historia konwersacji przekazana z frontendu

@app.post("/api/chat")
async def chat_with_gemini(req: ChatRequest):
    try:
        # Formatujemy historię do wysłania do modelu
        contents = []
        for m in req.messages:
            author = m.get("author", "Użytkownik")
            text = m.get("content", "")
            role = m.get("role", "user")
            
            if role == "model":
                contents.append(f"Gemini: {text}")
            else:
                contents.append(f"{author}: {text}")

        if not contents:
            raise HTTPException(status_code=400, detail="Brak wiadomości do przetworzenia.")

        # Wywołanie modelu Gemini (używamy stabilnego flasha)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
        )
        
        return {"response": response.text}

    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
            raise HTTPException(status_code=429, detail="Wyczerpano darmowy limit zapytań do Gemini. Odczekaj chwilę.")
        raise HTTPException(status_code=500, detail=error_str)