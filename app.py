import os
import streamlit as st
from google import genai
from google.genai import types

# 1. Konfiguracja strony Streamlit
st.set_page_config(
    page_title="MultiGem - Wspólny Czat AI",
    page_icon="🤖",
    layout="centered",
)

st.title("✨ MultiGem")
st.caption("Wspólny dwuosobowy czat ze sztuczną inteligencją Gemini na żywo.")

# 2. Konfiguracja klucza API i klienta Gemini
# Klucz pobieramy bezpiecznie z sekretów Streamlit lub zmiennych środowiskowych
api_key = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")

if not api_key:
    st.error(
        "Brak klucza API Gemini! Ustaw zmienną środowiskową `GEMINI_API_KEY` lub dodaj ją w zakładce Secrets w Streamlit Cloud."
    )
    st.stop()

# Inicjalizacja oficjalnego klienta genai
client = genai.Client(api_key=api_key)

# 3. Panel boczny (Sidebar) do konfiguracji użytkowników
with st.sidebar:
  st.header("⚙️ Ustawienia sesji")
  user_name = st.text_input("Twoje imię:", value="Użytkownik")
  st.divider()
  st.info(
      "Wskazówka: Wyślij ten link znajomemu, aby mógł dołączyć do projektu"
      " na GitHubie i uruchomić własną instancję lub połączyć się z tym"
      " samym widokiem!"
  )

# 4. Inicjalizacja stanu sesji (pamięć czatu w pamięci podręcznej Streamlit)
if "messages" not in st.session_state:
  st.session_state.messages = []

# 5. Wyświetlanie dotychczasowej historii czatu
for message in st.session_state.messages:
  # Jeśli rola to model, wyświetlamy jako asystenta, w przeciwnym razie jako użytkownika z imieniem
  role = (
      "assistant"
      if message["role"] == "model"
      else f"user ({message.get('author', 'Ktoś')})"
  )
  with st.chat_message(role):
    st.markdown(message["content"])

# 6. Obsługa wprowadzania nowej wiadomości przez użytkownika
if prompt := st.chat_input("Napisz coś do Gemini..."):
  # Zapisujemy wiadomość użytkownika w historii stanu
  st.session_state.messages.append(
      {"role": "user", "content": prompt, "author": user_name}
  )

  # Wyświetlamy wiadomość użytkownika w interfejsie
  with st.chat_message(f"user ({user_name})"):
    st.markdown(prompt)

  # 7. Przygotowanie historii dla API Gemini
  # API wymaga specyficznego formatu: lista obiektów z 'role' ('user' lub 'model') oraz 'parts'
  api_history = []
  for msg in st.session_state.messages:
    # Mapujemy role na format akceptowany przez SDK google-genai
    role_to_send = (
        "user" if msg["role"] == "user" else "model"
    )  # API Gemini rozróżnia 'user' i 'model'
    # Do treści wiadomości użytkownika możemy dokleić informację o autorze, żeby AI wiedziało, z kim rozmawia
    content_to_send = (
        f"[{msg.get('author', 'Użytkownik')}]: {msg['content']}"
        if msg["role"] == "user"
        else msg["content"]
    )

    api_history.append(
        types.Content(
            role=role_to_send,
            parts=[types.Part.from_text(text=content_to_send)],
        )
    )

  # 8. Wywołanie API Gemini (używamy lekkiego i szybkiego modelu gemini-2.5-flash)
  with st.chat_message("assistant"):
    with st.spinner("Gemini pisze..."):
      try:
        # Tworzymy czat z uwzględnieniem dotychczasowej historii
        chat = client.chats.create(
            model="gemini-2.5-flash", history=api_history[:-1]
        )
        # Wysyłamy ostatnią wiadomość
        response = chat.send_message(api_history[-1].parts[0].text)
        bot_response = response.text

        st.markdown(bot_response)

        # Zapisujemy odpowiedź modelu w historii stanu
        st.session_state.messages.append(
            {"role": "model", "content": bot_response}
        )

      except Exception as e:
        st.error(f"Wystąpił błąd podczas komunikacji z API Gemini: {e}")