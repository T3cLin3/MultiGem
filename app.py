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
api_key = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")

if not api_key:
  st.error(
      "Brak klucza API Gemini! Ustaw zmienną środowiskową lub dodaj ją w Secrets"
      " w Streamlit Cloud."
  )
  st.stop()

client = genai.Client(api_key=api_key)

# 3. Panel boczny (Sidebar) do konfiguracji użytkowników
with st.sidebar:
  st.header("⚙️ Ustawienia sesji")
  user_name = st.text_input("Twoje imię:", value="Użytkownik")
  st.divider()
  st.info("Wyślij ten link znajomemu, abyście mogli testować aplikację razem!")

# 4. Inicjalizacja stanu sesji
if "messages" not in st.session_state:
  st.session_state.messages = []

# 5. Wyświetlanie dotychczasowej historii czatu
for message in st.session_state.messages:
  if message["role"] == "model":
    with st.chat_message("assistant", avatar="🤖"):
      st.markdown(message["content"])
  else:
    author = message.get("author", "Użytkownik")
    with st.chat_message("user"):  # Bez argumentu avatar, żeby Streamlit nie szukał pliku
      st.markdown(f"**{author}:** {message['content']}")

# 6. Obsługa wprowadzania nowej wiadomości przez użytkownika
if prompt := st.chat_input("Napisz coś do Gemini..."):
  st.session_state.messages.append(
      {"role": "user", "content": prompt, "author": user_name}
  )

  with st.chat_message("user"):
    st.markdown(f"**{user_name}:** {prompt}")

  # Przygotowanie historii dla API Gemini
  contents = []
  for msg in st.session_state.messages:
    role = "user" if msg["role"] == "user" else "model"
    prefix = (
        f"[{msg.get('author', 'Użytkownik')}]: "
        if msg["role"] == "user"
        else ""
    )
    contents.append(
        types.Content(
            role=role,
            parts=[types.Part.from_text(text=prefix + msg["content"])],
        )
    )

  # 8. Wywołanie API Gemini
  with st.chat_message("assistant", avatar="🤖"):
    with st.spinner("Gemini pisze..."):
      try:
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=contents,
        )

        bot_response = response.text
        st.markdown(bot_response)

        st.session_state.messages.append(
            {"role": "model", "content": bot_response}
        )

      except Exception as e:
        st.error(f"Wystąpił błąd podczas komunikacji z API Gemini: {e}")