import os
import streamlit as st
from google import genai
from google.genai import types
from supabase import create_client

# 1. Konfiguracja strony
st.set_page_config(
    page_title="MultiGem - Wspólny Czat AI", page_icon="🤖", layout="centered"
)

st.title("✨ MultiGem")
st.caption("Wspólny dwuosobowy czat ze sztuczną inteligencją Gemini na żywo.")

# 2. Pobieranie kluczy API (Gemini + Supabase)
api_key = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")
supabase_url = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")

if not api_key or not supabase_url or not supabase_key:
  st.error(
      "Brak wymaganych kluczy! Upewnij się, że w Streamlit Secrets dodano"
      " `GEMINI_API_KEY`, `SUPABASE_URL` oraz `SUPABASE_KEY`."
  )
  st.stop()

# Inicjalizacja klientów
client = genai.Client(api_key=api_key)
supabase = create_client(supabase_url, supabase_key)

# 3. Panel boczny
with st.sidebar:
  st.header("⚙️ Ustawienia sesji")
  user_name = st.text_input("Twoje imię:", value="Użytkownik")
  st.divider()
  st.info(
      "Teraz wiadomości zapisują się w bazie danych! Wyślij ten link"
      " znajomemu, a obaj zobaczycie tę samą rozmowę na żywo."
  )
  if st.button("🔄 Odśwież czat"):
    st.rerun()

# 4. Pobieranie historii wiadomości z bazy Supabase
try:
  response = (
      supabase.table("messages")
      .select("*")
      .order("created_at", desc=False)
      .execute()
  )
  messages = response.data
except Exception as e:
  st.error(f"Błąd pobierania wiadomości z bazy: {e}")
  messages = []

# 5. Wyświetlanie historii czatu
for msg in messages:
  # Upewniamy się, że msg to słownik, żeby uniknąć błędów typu AttributeError
  if not isinstance(msg, dict):
    continue

  role = msg.get("role", "user")
  author = msg.get("author", "Użytkownik")
  content = msg.get("content", "")

  if role == "model":
    with st.chat_message("assistant", avatar="🤖"):
      st.markdown(content)
  else:
    with st.chat_message("user"):
      st.markdown(f"**{author}:** {content}")

# 6. Obsługa nowej wiadomości
if prompt := st.chat_input("Napisz coś do Gemini..."):
  # Zapisujemy wiadomość użytkownika w bazie Supabase
  try:
    supabase.table("messages").insert({
        "author": user_name,
        "content": prompt,
        "role": "user",
    }).execute()
  except Exception as e:
    st.error(f"Błąd zapisu wiadomości: {e}")

  # Wyświetlamy od razu u siebie
  with st.chat_message("user"):
    st.markdown(f"**{user_name}:** {prompt}")

# 7. Przygotowanie pełnej historii do wysłania do Gemini
  try:
    fresh_res = (
        supabase.table("messages")
        .select("*")
        .order("created_at", desc=False)
        .execute()
    )
    all_msgs = fresh_res.data or []

    # Tworzymy czystą listę wiadomości w formacie tekstowym akceptowanym przez API
    contents = []
    for m in all_msgs:
      if not isinstance(m, dict):
        continue
      author = m.get("author", "Użytkownik")
      text = m.get("content", "")
      role = m.get("role", "user")

      # Formatujemy treść, aby model wiedział, kto co napisał
      if role == "model":
        contents.append(f"Gemini: {text}")
      else:
        contents.append(f"{author}: {text}")

    # Jeśli z jakiegoś powodu lista jest pusta, wrzucamy awaryjny prompt
    if not contents:
      contents = [prompt]

    # 8. Wywołanie modelu Gemini
    with st.chat_message("assistant", avatar="🤖"):
      with st.spinner("Gemini pisze..."):
        ai_response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=contents,
        )
        bot_response = ai_response.text
        st.markdown(bot_response)

        # Zapisujemy odpowiedź AI w bazie Supabase
        supabase.table("messages").insert({
            "author": "Gemini",
            "content": bot_response,
            "role": "model",
        }).execute()

    st.rerun()

  except Exception as e:
    st.error(f"Wystąpił błąd podczas komunikacji z API Gemini: {e}")