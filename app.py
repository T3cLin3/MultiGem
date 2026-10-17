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

# 2. Pobieranie kluczy API
api_key = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")
supabase_url = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")

if not api_key or not supabase_url or not supabase_key:
  st.error("Brak wymaganych kluczy w Streamlit Secrets!")
  st.stop()

client = genai.Client(api_key=api_key)
supabase = create_client(supabase_url, supabase_key)

# 3. Panel boczny (Ustawienia i Pokoje)
with st.sidebar:
  st.header("⚙️ Ustawienia sesji")
  user_name = st.text_input("Twoje imię:", value="Użytkownik")
  
  st.divider()
  st.subheader("💬 Pokoje / Wątki")
  # Możesz wpisać dowolną nazwę pokoju, żeby przełączyć się na inny wątek rozmowy!
  room_name = st.text_input("Nazwa pokoju:", value="ogólny")
  
  st.divider()
  if st.button("🔄 Odśwież czat"):
    st.rerun()

# 4. Pobieranie historii wiadomości tylko dla wybranego pokoju
try:
  response = (
      supabase.table("messages")
      .select("*")
      .eq("room_id", room_name)
      .order("id", desc=False)
      .execute()
  )
  messages = response.data or []
except Exception as e:
  st.error(f"Błąd pobierania wiadomości: {e}")
  messages = []

# 5. Wyświetlanie historii czatu
for msg in messages:
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
if prompt := st.chat_input(f"Napisz coś w pokoju '{room_name}'..."):
  # Zapisujemy wiadomość użytkownika z przypisaniem do aktualnego pokoju
  try:
    supabase.table("messages").insert({
        "author": user_name,
        "content": prompt,
        "role": "user",
        "room_id": room_name,
    }).execute()
  except Exception as e:
    st.error(f"Błąd zapisu: {e}")

  # 7. Pobieramy pełną historię dla Gemini w tym pokoju
  try:
    fresh_res = (
        supabase.table("messages")
        .select("*")
        .eq("room_id", room_name)
        .order("id", desc=False)
        .execute()
    )
    all_msgs = fresh_res.data or []

    contents = []
    for m in all_msgs:
      if not isinstance(m, dict):
        continue
      author = m.get("author", "Użytkownik")
      text = m.get("content", "")
      role = m.get("role", "user")

      if role == "model":
        contents.append(f"Gemini: {text}")
      else:
        contents.append(f"{author}: {text}")

    if not contents:
      contents = [prompt]

    # 8. Wywołanie modelu Gemini
    with st.chat_message("assistant", avatar="🤖"):
      with st.spinner("Gemini pisze..."):
        try:
          ai_response = client.models.generate_content(
              model="gemini-3.8-flash",
              contents=contents,
          )
          bot_response = ai_response.text
          st.markdown(bot_response)

          # Zapisujemy odpowiedź bota w bazie dla tego pokoju
          supabase.table("messages").insert({
              "author": "Gemini",
              "content": bot_response,
              "role": "model",
              "room_id": room_name,
          }).execute()

        except Exception as api_err:
          error_msg = str(api_err)
          if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            bot_response = (
                "⚠️ [Błąd API]: Wyczerpano darmowy limit zapytań do Gemini."
                " Odczekaj chwilę."
            )
          else:
            bot_response = f"⚠️ [Błąd API Gemini]: {error_msg}"

          st.error(bot_response)

          supabase.table("messages").insert({
              "author": "System",
              "content": bot_response,
              "role": "model",
              "room_id": room_name,
          }).execute()

    st.rerun()

  except Exception as e:
    st.error(f"Wystąpił błąd ogólny: {e}")