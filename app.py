import os
import streamlit as st
from google import genai
from google.genai import types
from supabase import create_client

# 1. Konfiguracja strony - Czysty start
st.set_page_config(
    page_title="MultiGem - Ekskluzywny Czat AI", page_icon="✨", layout="wide"
)

# -----------------------------------------------------------------------------
# 2. RADYKALNE WSTRZYKIWANIE STYLÓW CSS (Aby strona była nie do poznania)
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
        /* --- Zmienne kolorystyczne (Deep Black & Gold) --- */
        :root {
            --bg-deep: #050505;
            --bg-sidebar: #111111;
            --text-main: #e0e0e0;
            --text-muted: #888888;
            --accent-gold: #d4af37;
            --accent-hover: #e0c256;
            --border-color: #333333;
        }

        /* --- Reset i styl ogólny --- */
        .stApp {
            background-color: var(--bg-deep);
            color: var(--text-main);
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        }

        /* Ukrycie domyślnych elementów Streamlit */
        header, #MainMenu, footer { visibility: hidden; height: 0; }
        
        /* Główny kontener */
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 6rem; /* Miejsce na input */
            max-width: 720px;
        }

        /* --- Styl Panelu Bocznego (Sidebar) --- */
        [data-testid="stSidebar"] {
            background-color: var(--bg-sidebar);
            border-right: 1px solid var(--border-color);
            padding: 2rem 1rem;
        }
        
        /* Nagłówki w sidebarze */
        [data-testid="stSidebar"] h3 {
            color: var(--accent-gold);
            font-size: 1.1rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 1rem;
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 0.5rem;
        }
        
        /* Etykieta "Twój imię" */
        [data-testid="stSidebar"] label {
            color: var(--text-muted);
            font-size: 0.85rem;
        }

        /* Pola tekstowe w sidebarze */
        [data-testid="stSidebar"] .stTextInput > div > div > input {
            background-color: transparent;
            border: 1px solid var(--border-color);
            color: var(--text-main);
            border-radius: 6px;
        }
        [data-testid="stSidebar"] .stTextInput > div > div > input:focus {
            border-color: var(--accent-gold);
            box-shadow: 0 0 0 1px var(--accent-gold);
        }

        /* --- Nowe Przyciski (Całkowity redesign) --- */
        .stButton > button {
            background-color: transparent;
            color: var(--text-main);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 0.5rem 1rem;
            font-size: 0.9rem;
            font-weight: 400;
            transition: all 0.3s ease;
            width: 100%;
            text-align: left;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .stButton > button:hover {
            background-color: rgba(212, 175, 55, 0.1);
            color: var(--accent-hover);
            border-color: var(--accent-gold);
        }

        /* Specjalny styl dla przycisku "Nowy czat" */
        [data-testid="stSidebar"] .stButton:first-of-type > button {
            background-color: var(--accent-gold);
            color: var(--bg-deep);
            font-weight: 600;
            border: none;
        }
        [data-testid="stSidebar"] .stButton:first-of-type > button:hover {
            background-color: var(--accent-hover);
            color: var(--bg-deep);
        }

        /* --- Lista Radio (Wybór wątku) --- */
        [data-testid="stSidebar"] [role="radiogroup"] {
            gap: 0.2rem;
        }
        [data-testid="stSidebar"] [role="radiogroup"] label {
            padding: 0.6rem 1rem;
            border-radius: 6px;
            transition: background 0.2s;
            color: var(--text-muted);
            border: none;
        }
        [data-testid="stSidebar"] [role="radiogroup"] label:hover {
            background-color: #1a1a1a;
            color: var(--text-main);
        }
        /* Kropka zaznaczenia radio */
        [data-testid="stSidebar"] [role="radiogroup"] input[type="radio"]:checked + div {
            background-color: var(--accent-gold);
        }
        /* Wybrany element radio */
        [data-testid="stSidebar"] [role="radiogroup"] label:has(input[type="radio"]:checked) {
             background-color: rgba(212, 175, 55, 0.15);
             color: var(--accent-gold);
             font-weight: 500;
        }

        /* --- Styl Komunikatów Czatowych (Zmiana dymków) --- */
        /* Usuwamy domyślne avatary Streamlita */
        [data-testid="stChatMessageAvatarUser"], [data-testid="stChatMessageAvatarAssistant"] {
            display: none;
        }
        
        /* Kontener wiadomości */
        [data-testid="stChatMessageContent"] {
            background-color: transparent;
            border-radius: 12px;
            padding: 1rem 1.5rem;
            margin-left: 0;
            color: var(--text-main);
            border: none;
        }
        
        /* Dymek użytkownika */
        [data-testid="stChatMessage"] {
            flex-direction: row-reverse; /* Imię po prawej */
            gap: 10px;
            margin-bottom: 1.5rem;
        }
        
        [data-testid="stChatMessage"][data-testid="stChatMessageUser"] [data-testid="stChatMessageContent"] {
            background-color: #1a1a1a;
            border-bottom-right-radius: 4px;
        }
        [data-testid="stChatMessage"][data-testid="stChatMessageUser"]::before {
             content: "Ty";
             font-size: 0.7rem;
             color: var(--accent-gold);
             font-weight: bold;
             align-self: flex-end;
             margin-bottom: 5px;
        }

        /* Dymek asystenta */
        [data-testid="stChatMessage"][data-testid="stChatMessageAssistant"] [data-testid="stChatMessageContent"] {
            background-color: transparent;
            border-bottom-left-radius: 4px;
            color: var(--accent-gold); /* Odpowiedzi bota złote */
        }
        [data-testid="stChatMessage"][data-testid="stChatMessageAssistant"]::before {
             content: "MultiGem";
             font-size: 0.7rem;
             color: var(--text-muted);
             font-weight: bold;
             align-self: flex-end;
             margin-bottom: 5px;
        }

        /* Treść wiadomości (pogrubienia, kod) */
        strong { color: var(--accent-gold); }
        code { background-color: #222 !important; color: var(--accent-gold) !important; padding: 2px 4px !important; border-radius: 4px !important;}

        /* --- Obszar wprowadzania (Na samym dole) --- */
        [data-testid="stChatInput"] {
            background-color: var(--bg-deep);
            border-top: 1px solid var(--border-color);
            padding: 1rem 0;
            position: fixed;
            bottom: 0;
            left: 0; /* Wersja desktop */
            width: 100%;
            display: flex;
            justify-content: center;
            box-shadow: 0 -10px 20px rgba(0,0,0,0.4);
        }
        
        /* Dostosowanie szerokości inputa do głównej kolumny */
        @media (min-width: 800px) {
             [data-testid="stChatInput"] {
                 left: 20rem; /* Szerokość paska bocznego */
                 width: calc(100% - 20rem);
             }
        }

        /* Właściwe pole input */
        [data-testid="stChatInput"] textarea {
            background-color: #161920 !important;
            border: 1px solid var(--border-color) !important;
            color: var(--text-main) !important;
            border-radius: 24px !important;
            padding: 0.8rem 1.5rem !important;
            font-size: 1rem !important;
        }
        [data-testid="stChatInput"] textarea:focus {
            border-color: var(--accent-gold) !important;
            box-shadow: none !important;
        }
        
        /* Przycisk wysyłania (strzałka) */
        [data-testid="stChatInputSubmitButton"] {
             color: var(--accent-gold) !important;
        }

    </style>
""",
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# 3. Logika aplikacji (Pozostaje bez zmian)
# -----------------------------------------------------------------------------
api_key = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")
supabase_url = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")

if not api_key or not supabase_url or not supabase_key:
  st.error("Brak kluczy API w Secrets!")
  st.stop()

client = genai.Client(api_key=api_key)
supabase = create_client(supabase_url, supabase_key)

if "current_room" not in st.session_state:
  st.session_state.current_room = "Nowa rozmowa"

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
  if not existing_rooms: existing_rooms = ["Nowa rozmowa"]
except Exception:
  existing_rooms = [st.session_state.current_room]

if st.session_state.current_room not in existing_rooms:
  existing_rooms.append(st.session_state.current_room)

# 4. Budowa Panelu Bocznego z nowymi klasami
with st.sidebar:
  st.markdown("### 👤 Użytkownik")
  user_name = st.text_input("Twoje imię:", value="Użytkownik", label_visibility="collapsed")

  st.markdown("---")
  if st.button("➕ Nowa rozmowa", use_container_width=True):
    new_room_name = f"Rozmowa {len(existing_rooms) + 1}"
    st.session_state.current_room = new_room_name
    st.rerun()

  st.markdown("### 💬 Historia")
  selected_room = st.radio(
      "Wybierz wątek:",
      options=existing_rooms,
      index=existing_rooms.index(st.session_state.current_room) if st.session_state.current_room in existing_rooms else 0,
      label_visibility="collapsed",
  )
  
  if selected_room != st.session_state.current_room:
    st.session_state.current_room = selected_room
    st.rerun()

  st.markdown("---")
  st.markdown("### ✏️ Zmień nazwę wątku")
  new_room_name_input = st.text_input("Nowa nazwa:", value=st.session_state.current_room, label_visibility="collapsed")
  if st.button("Zmień nazwę", use_container_width=True):
    if new_room_name_input and new_room_name_input != st.session_state.current_room:
      old_room = st.session_state.current_room
      try:
        supabase.table("messages").update({"room_id": new_room_name_input}).eq("room_id", old_room).execute()
        st.session_state.current_room = new_room_name_input
        st.rerun()
      except Exception as e:
        st.error(f"Błąd: {e}")

  st.markdown("---")
  if st.button("🔄 Odśwież czat", use_container_width=True):
    st.rerun()

room_name = st.session_state.current_room

# 5. Pobieranie wiadomości
try:
  response = supabase.table("messages").select("*").eq("room_id", room_name).order("id", desc=False).execute()
  messages = response.data or []
except Exception as e:
  st.error(f"Błąd: {e}")
  messages = []

# 6. Wyświetlanie czatu (z nowym stylem dymków)
# Ukrywamy nazwę pokoju na górze, żeby było czyściej
for msg in messages:
  if not isinstance(msg, dict): continue
  role = msg.get("role", "user")
  author = msg.get("author", "Użytkownik")
  content = msg.get("content", "")
  
  # Streamlit wyświetla avatary po lewej, ale my je ukrywamy CSS i dodajemy własne etykiety
  with st.chat_message(role):
    st.markdown(content)

# 7. Input użytkownika (przeniesiony na sam dół w stylu unoszącym się)
if prompt := st.chat_input("Zadaj pytanie MultiGem..."):
  try:
    supabase.table("messages").insert({"author": user_name, "content": prompt, "role": "user", "room_id": room_name}).execute()
  except Exception as e:
    st.error(f"Błąd zapisu: {e}")

  try:
    # Przygotowanie historii dla API (Gemini 3.8-flash)
    all_msgs_res = supabase.table("messages").select("*").eq("room_id", room_name).order("id", desc=False).execute()
    all_msgs_data = all_msgs_res.data or []
    
    contents_gemini = []
    for m in all_msgs_data:
        if not isinstance(m, dict): continue
        auth = m.get("author", "Użytkownik")
        txt = m.get("content", "")
        role_db = m.get("role", "user")
        if role_db == "model":
            contents_gemini.append(f"Gemini: {txt}")
        else:
            contents_gemini.append(f"{auth}: {txt}")

    if not contents_gemini: contents_gemini = [prompt]

    # Wywołanie Gemini
    with st.chat_message("assistant"):
      with st.spinner("MultiGem analizuje..."):
        try:
            ai_response = client.models.generate_content(model="gemini-3.8-flash", contents=contents_gemini)
            bot_txt = ai_response.text
            st.markdown(bot_txt)
            supabase.table("messages").insert({"author": "Gemini", "content": bot_txt, "role": "model", "room_id": room_name}).execute()
        except Exception as api_err:
            err_msg = str(api_err)
            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                system_msg = "⚠️ [Limit wyczerpany]: Darmowy limit zapytań chwilowo przekroczony. Spróbuj za chwilę."
            else:
                system_msg = f"⚠️ [Błąd API]: {err_msg}"
            st.error(system_msg)
            supabase.table("messages").insert({"author": "System", "content": system_msg, "role": "model", "room_id": room_name}).execute()
            
    st.rerun()
  except Exception as e:
    st.error(f"Błąd główny: {e}")