import os
import streamlit as st
from google import genai
from google.genai import types
from supabase import create_client

# 1. Konfiguracja strony i nowoczesne style CSS
st.set_page_config(
    page_title="MultiGem - Wspólny Czat AI", page_icon="✨", layout="centered"
)

# Wstrzykujemy customowy CSS, aby poprawić wygląd interfejsu
st.markdown(
    """
    <style>
        /* Styl ogólny strony */
        .main {
            background-color: #0e1117;
        }
        /* Nagłówki */
        h1, h2, h3 {
            font-family: 'Inter', sans-serif;
            letter-spacing: -0.5px;
        }
        /* Styl panelu bocznego */
        [data-testid="stSidebar"] {
            background-color: #161920;
            border-right: 1px solid #262730;
        }
        /* Styl przycisków */
        .stButton>button {
            border-radius: 8px;
            font-weight: 500;
            transition: all 0.2s ease;
        }
        .stButton>button:hover {
            border-color: #4f46e5;
            color: #4f46e5;
        }
        /* Pola tekstowe */
        .stTextInput>div>div>input {
            border-radius: 8px;
        }
        /* Ukrycie domyślnego menu Streamlit dla czystszego widoku */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
""",
    unsafe_allow_html=True,
)

st.title("✨ MultiGem")
st.caption(
    "Wspólny, dwuosobowy czat ze sztuczną inteligencją w czasie rzeczywistym."
)

# 2. Pobieranie kluczy API
api_key = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")
supabase_url = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")

if not api_key or not supabase_url or not supabase_key:
  st.error(
      "⚠️ Brak wymaganych kluczy w Streamlit Secrets! Skonfiguruj"
      " `GEMINI_API_KEY`, `SUPABASE_URL` oraz `SUPABASE_KEY`."
  )
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

if st.session_state.current_room not in existing_rooms:
  existing_rooms.append(st.session_state.current_room)

# 4. Panel boczny (Sidebar w stylu ChatGPT / Gemini)
with st.sidebar:
  st.markdown("### 👤 Profil użytkownika")
  user_name = st.text_input("Twoje imię:", value="Użytkownik")

  st.markdown("---")

  # Przycisk tworzenia nowego czatu
  if st.button("➕ Nowa rozmowa", use_container_width=True):
    new_room_name = f"Rozmowa {len(existing_rooms) + 1}"
    st.session_state.current_room = new_room_name
    st.rerun()

  st.markdown("### 💬 Twoje wątki")

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

  st.markdown("---")

  # Opcja zmiany nazwy aktywnego pokoju
  st.markdown("### ✏️ Edytuj wątek")
  new_room_name_input = st.text_input(
      "Nazwa wątku:",
      value=st.session_state.current_room,
      label_visibility="collapsed",
  )
  if st.button("Zmień nazwę", use_container_width=True):
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
        st.success("Zmieniono nazwę!")
        st.rerun()
      except Exception as e:
        st.error(f"Błąd zmiany nazwy: {e}")

  st.markdown("---")
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

# 6. Nagłówek aktywnego pokoju i wyświetlanie historii czatu
st.markdown(
    f"##### 📍 Aktywny wątek: <span style='color: #4f46e5;'>{room_name}</span>",
    unsafe_allow_html=True,
)
st.markdown("---")

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
if prompt := st.chat_input(f"Napisz wiadomość w wątku '{room_name}'..."):
  try:
    supabase.table("messages").insert({
        "author": user_name,
        "content": prompt,
        "role": "user",
        "room_id": room_name,
    }).execute()
  except Exception as e:
    st.error(f"Błąd zapisu wiadomości: {e}")

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
      with st.spinner("Gemini pisze odpowiedź..."):
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
    st.error(f"Błąd ogólny: {e}")