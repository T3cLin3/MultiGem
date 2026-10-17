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

# Inicjalizacja stanu sesji dla aktywnego pokoju
if "current_room" not in st.session_state:
  st.session_state.current_room = "Nowa rozmowa"

# 3. Pobieranie listy unikalnych pokoi z bazy Supabase
try:
  rooms_res = supabase.table("messages").select("room_id").execute()
  rooms_data = rooms_res.data or []
  # Wyciągamy unikalne nazwy pokoi i sortujemy
  existing_rooms = sorted(
      list(
          set(
              m.get("room_id", "Nowa rozmowa")
              for m in rooms_data
              if isinstance(m, dict) and m.get("room_id")
          )
      )
  )
  if not existing_rooms:
    existing_rooms = ["Nowa rozmowa"]
except Exception:
  existing_rooms = [st.session_state.current_room]

# Zapewnienie, że aktualny pokój jest na liście
if st.session_state.current_room not in existing_rooms:
  existing_rooms.append(st.session_state.current_room)

# 4. Panel boczny w stylu Gemini (Historia i Nowy Czat)
with st.sidebar:
  st.header("⚙️ Ustawienia")
  user_name = st.text_input("Twoje imię:", value="Użytkownik")

  st.divider()

  # Przycisk tworzenia nowego czatu (jak w Gemini)
  if st.button("➕ Nowy czat", use_container_width=True):
    # Generujemy prostą nazwę bazującą na liczbie rozmów lub timestampie
    new_room_name = f"Rozmowa {len(existing_rooms) + 1}"
    st.session_state.current_room = new_room_name
    st.rerun()

  st.subheader("💬 Twoje rozmowy")

  # Wybór pokoju za pomocą listy (radio)
  selected_room = st.radio(
      "Wybierz wątek:",
      options=existing_rooms,
      index=existing_rooms.index(st.session_state.current_room)
      if st.session_state.current_room in existing_rooms
      else 0,
      label_visibility="collapsed",
  )

  # Jeśli użytkownik kliknął inny pokój na liście
  if selected_room != st.session_state.current_room:
    st.session_state.current_room = selected_room
    st.rerun()

  st.divider()
  if st.button("🔄 Odśwież widok", use_container_width=True):
    st.rerun()

room_name = st.session_state.current_room

# 5. Pobieranie historii wiadomości dla aktywnego pokoju
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

# 6. Wyświetlanie historii czatu
st.markdown(f"### Aktualny pokój: `{room_name}`")
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

# 7. Obsługa nowej wiadomości
if prompt := st.chat_input(f"Napisz coś do Gemini..."):
  # Zapisujemy wiadomość użytkownika
  try:
    supabase.table("messages").insert({
        "author": user_name,
        "content": prompt,
        "role": "user",
        "room_id": room_name,
    }).execute()
  except Exception as e:
    st.error(f"Błąd zapisu: {e}")

  # 8. Pobieramy pełną historię do Gemini dla tego pokoju
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

    # 9. Wywołanie modelu Gemini
    with st.chat_message("assistant", avatar="🤖"):
      with st.spinner("Gemini pisze..."):
        try:
          ai_response = client.models.generate_content(
              model="gemini-3.8-flash",
              contents=contents,
          )
          bot_response = ai_response.text
          st.markdown(bot_response)

          # Zapisujemy odpowiedź bota w bazie
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