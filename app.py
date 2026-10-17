import os
import streamlit as st
from google import genai
from google.genai import types
from supabase import create_client

# 1. Konfiguracja strony
st.set_page_config(
    page_title="MultiGem - Czat", page_icon="💬", layout="centered"
)

# 2. Czysty i minimalistyczny styl CSS (bez zbędnych ozdobników)
st.markdown(
    """
    <style>
        .main {
            background-color: #0e1117;
        }
        /* Zwarty panel boczny bez nadmiernego scrollowania */
        [data-testid="stSidebar"] {
            background-color: #161920;
            padding-top: 1rem;
        }
        /* Mniejsze odstępy w sidebarze */
        [data-testid="stSidebar"] .block-container {
            padding: 1rem;
        }
        /* Stylowanie przycisków */
        .stButton > button {
            border-radius: 6px;
            width: 100%;
        }
    </style>
""",
    unsafe_allow_html=True,
)

st.title("💬 MultiGem")
st.caption("Wspólny czat z Gemini w czasie rzeczywistym.")

# 3. Pobieranie kluczy API
api_key = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")
supabase_url = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")

if not api_key or not supabase_url or not supabase_key:
  st.error("Brak wymaganych kluczy w Streamlit Secrets!")
  st.stop()

client = genai.Client(api_key=api_key)
supabase = create_client(supabase_url, supabase_key)

if "current_room" not in st.session_state:
  st.session_state.current_room = "Ogólny"

# Pobieranie listy pokoi
try:
  rooms_res = supabase.table("messages").select("room_id").execute()
  rooms_data = rooms_res.data or []
  existing_rooms = sorted(
      list(
          set(
              m.get("room_id", "Ogólny")
              for m in rooms_data
              if isinstance(m, dict) and m.get("room_id")
          )
      )
  )
  if not existing_rooms:
    existing_rooms = ["Ogólny"]
except Exception:
  existing_rooms = [st.session_state.current_room]

if st.session_state.current_room not in existing_rooms:
  existing_rooms.append(st.session_state.current_room)

# 4. Zwarty Panel Boczny
with st.sidebar:
  st.subheader("Ustawienia")
  user_name = st.text_input("Twoje imię:", value="Użytkownik")

  if st.button("Nowa rozmowa"):
    new_room_name = f"Rozmowa {len(existing_rooms) + 1}"
    st.session_state.current_room = new_room_name
    st.rerun()

  st.subheader("Wątki")
  selected_room = st.radio(
      "Wybierz pokój:",
      options=existing_rooms,
      index=existing_rooms.index(st.session_state.current_room)
      if st.session_state.current_room in existing_rooms
      else 0,
      label_visibility="collapsed",
  )

  if selected_room != st.session_state.current_room:
    st.session_state.current_room = selected_room
    st.rerun()

  st.divider()
  
  # Szybka zmiana nazwy
  new_room_name_input = st.text_input(
      "Zmień nazwę wątku:", value=st.session_state.current_room
  )
  if st.button("Zapisz nazwę"):
    if (
        new_room_name_input
        and new_room_name_input != st.session_state.current_room
    ):
      old_room = st.session_state.current_room
      try:
        supabase.table("messages").update({"room_id": new_room_name_input}).eq(
            "room_id", old_room
        ).execute()
        st.session_state.current_room = new_room_name_input
        st.rerun()
      except Exception as e:
        st.error(f"Błąd: {e}")

  if st.button("Odśwież"):
    st.rerun()

room_name = st.session_state.current_room

# 5. Pobieranie wiadomości
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
  st.error(f"Błąd pobierania: {e}")
  messages = []

# 6. Wyświetlanie historii czatu z wyraźnym podziałem na autorów
st.markdown(f"**Aktywny wątek:** `{room_name}`")
st.markdown("---")

for msg in messages:
  if not isinstance(msg, dict):
    continue

  role = msg.get("role", "user")
  author = msg.get("author", "Użytkownik")
  content = msg.get("content", "")

  if role == "model":
    with st.chat_message("assistant", avatar="🤖"):
      st.markdown(f"**Gemini:**\n\n{content}")
  else:
    with st.chat_message("user", avatar="👤"):
      st.markdown(f"**{author}:**\n\n{content}")

# 7. Obsługa wysyłania wiadomości
if prompt := st.chat_input("Napisz wiadomość..."):
  try:
    supabase.table("messages").insert({
        "author": user_name,
        "content": prompt,
        "role": "user",
        "room_id": room_name,
    }).execute()
  except Exception as e:
    st.error(f"Błąd zapisu: {e}")

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

    with st.chat_message("assistant", avatar="🤖"):
      with st.spinner("Gemini pisze..."):
        try:
          ai_response = client.models.generate_content(
              model="gemini-3.8-flash",
              contents=contents,
          )
          bot_response = ai_response.text
          st.markdown(f"**Gemini:**\n\n{bot_response}")

          supabase.table("messages").insert({
              "author": "Gemini",
              "content": bot_response,
              "role": "model",
              "room_id": room_name,
          }).execute()

        except Exception as api_err:
          error_msg = str(api_err)
          if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            bot_response = "⚠️ [Limit API]: Wyczerpano darmowy limit zapytań."
          else:
            bot_response = f"⚠️ [Błąd API]: {error_msg}"

          st.error(bot_response)
          supabase.table("messages").insert({
              "author": "System",
              "content": bot_response,
              "role": "model",
              "room_id": room_name,
          }).execute()

    st.rerun()

  except Exception as e:
    st.error(f"Błąd ogólny: {e}")