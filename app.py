import os
import streamlit as st
from google import genai
from google.genai import types
from supabase import create_client

# 1. Konfiguracja strony
st.set_page_config(
    page_title="MultiGem", page_icon="✨", layout="wide"
)

# 2. Zaawansowane style CSS nadające profesjonalny wygląd
st.markdown(
    """
    <style>
        /* Globalne tło i czcionka */
        .stApp {
            background-color: #0b0f19;
            color: #f3f4f6;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }

        /* Ukrycie elementów systemowych Streamlit */
        header, #MainMenu, footer { visibility: hidden; }

        /* Panel boczny (Sidebar) */
        [data-testid="stSidebar"] {
            background-color: #030712;
            border-right: 1px solid #1f2937;
            padding: 1.5rem 1rem;
        }

        /* Nagłówki w sidebarze */
        [data-testid="stSidebar"] h3 {
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #9ca3af;
            margin-top: 1.5rem;
            margin-bottom: 0.5rem;
        }

        /* Styl przycisków */
        .stButton > button {
            background-color: #1f2937;
            color: #f3f4f6;
            border: 1px solid #374151;
            border-radius: 8px;
            font-weight: 500;
            transition: all 0.2s ease;
        }
        .stButton > button:hover {
            background-color: #374151;
            border-color: #4b5563;
            color: #ffffff;
        }

        /* Przycisk główny (Nowa rozmowa) */
        div.stButton > button[kind="primary"], [data-testid="stSidebar"] .stButton:first-of-type > button {
            background-color: #4f46e5;
            border-color: #4f46e5;
            color: white;
        }
        div.stButton > button[kind="primary"]:hover {
            background-color: #4338ca;
        }

        /* Pola tekstowe */
        .stTextInput input {
            background-color: #1f2937 !important;
            border: 1px solid #374151 !important;
            color: #f3f4f6 !important;
            border-radius: 8px !important;
        }
        .stTextInput input:focus {
            border-color: #4f46e5 !important;
            box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.2) !important;
        }

        /* Styl dymków czatu */
        [data-testid="stChatMessage"] {
            padding: 1rem 1.2rem;
            border-radius: 12px;
            margin-bottom: 0.75rem;
            border: 1px solid transparent;
        }
        
        /* Dymek użytkownika */
        [data-testid="stChatMessage"][data-testid*="user"] {
            background-color: #111827;
            border-color: #1f2937;
        }

        /* Dymek asystenta (Gemini) */
        [data-testid="stChatMessage"][data-testid*="assistant"] {
            background-color: #1f2937;
            border-color: #374151;
        }

        /* Wyczyszczenie marginesów kontenera głównego */
        .block-container {
            max-width: 800px;
            padding-top: 2rem;
        }
    </style>
""",
    unsafe_allow_html=True,
)

# 3. Inicjalizacja kluczy
api_key = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")
supabase_url = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")

if not api_key or not supabase_url or not supabase_key:
  st.error("Brak wymaganych kluczy w Streamlit Secrets!")
  st.stop()

client = genai.Client(api_key=api_key)
supabase = create_client(supabase_url, supabase_key)

if "current_room" not in st.session_state:
  st.session_state.current_room = "Główny czat"

# Pobieranie listy pokoi
try:
  rooms_res = supabase.table("messages").select("room_id").execute()
  rooms_data = rooms_res.data or []
  existing_rooms = sorted(
      list(
          set(
              m.get("room_id", "Główny czat")
              for m in rooms_data
              if isinstance(m, dict) and m.get("room_id")
          )
      )
  )
  if not existing_rooms:
    existing_rooms = ["Główny czat"]
except Exception:
  existing_rooms = [st.session_state.current_room]

if st.session_state.current_room not in existing_rooms:
  existing_rooms.append(st.session_state.current_room)

# 4. Elegancki Panel Boczny
with st.sidebar:
  st.markdown("### Profil")
  user_name = st.text_input("Imię użytkownika", value="Użytkownik", label_visibility="collapsed")

  if st.button("✨ Nowa rozmowa", use_container_width=True):
    new_room_name = f"Rozmowa {len(existing_rooms) + 1}"
    st.session_state.current_room = new_room_name
    st.rerun()

  st.markdown("### Wątki rozmów")
  
  # Zamiast brzydkiego radia robimy zgrabne przyciski dla każdego pokoju
  for room in existing_rooms:
    is_active = room == st.session_state.current_room
    button_type = "primary" if is_active else "secondary"
    if st.button(f"💬 {room}", key=f"room_btn_{room}", use_container_width=True, type=button_type):
      if not is_active:
        st.session_state.current_room = room
        st.rerun()

  st.markdown("---")
  st.markdown("### Ustawienia wątku")
  new_name_input = st.text_input("Zmień nazwę:", value=st.session_state.current_room, label_visibility="collapsed")
  if st.button("Zapisz zmianę", use_container_width=True):
    if new_name_input and new_name_input != st.session_state.current_room:
      old_room = st.session_state.current_room
      try:
        supabase.table("messages").update({"room_id": new_name_input}).eq("room_id", old_room).execute()
        st.session_state.current_room = new_name_input
        st.rerun()
      except Exception as e:
        st.error(f"Błąd: {e}")

  if st.button("🔄 Odśwież dane", use_container_width=True):
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

# 6. Główny interfejs czatu (Czysty, profesjonalny widok)
st.markdown(f"## ✦ {room_name}")
st.markdown("<div style='margin-bottom: 2rem;'></div>", unsafe_allow_html=True)

for msg in messages:
  if not isinstance(msg, dict):
    continue

  role = msg.get("role", "user")
  author = msg.get("author", "Użytkownik")
  content = msg.get("content", "")

  if role == "model":
    with st.chat_message("assistant", avatar="✨"):
      st.markdown(content)
  else:
    # Używamy imienia użytkownika jako czystego nagłówka nad treścią bez sztucznych ozdobników
    with st.chat_message("user", avatar="👤"):
      st.markdown(f"**{author}**\n\n{content}")

# 7. Obsługa wiadomości
if prompt := st.chat_input("Wpisz wiadomość..."):
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

    with st.chat_message("assistant", avatar="✨"):
      with st.spinner("Gemini generuje odpowiedź..."):
        try:
          ai_response = client.models.generate_content(
              model="gemini-3.8-flash",
              contents=contents,
          )
          bot_response = ai_response.text
          st.markdown(bot_response)

          supabase.table("messages").insert({
              "author": "Gemini",
              "content": bot_response,
              "role": "model",
              "room_id": room_name,
          }).execute()

        except Exception as api_err:
          error_msg = str(api_err)
          if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            bot_response = "⚠️ [Limit API]: Wyczerpano darmowy limit zapytań do Gemini. Spróbuj za chwilę."
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