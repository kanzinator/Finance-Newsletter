import re
import streamlit as st
from newsletter import build_and_send
from utils import to_ticker, fill_random_tickers

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")

st.set_page_config(page_title="Market Digest", page_icon="📈", layout="centered")

st.title("📈 Personalized Finance Newsletter")

GIF_URL = "https://www.scichart.com/wp-content/uploads/2020/04/realtime-ticking-stock-chart-gif.gif"

def _normalize_ticker(key: str):
    raw = st.session_state[key].strip()
    if raw:
        st.session_state[key] = to_ticker(raw)

def _randomize_empty():
    slots = [st.session_state.t1, st.session_state.t2, st.session_state.t3]
    filled = fill_random_tickers(slots)
    st.session_state.t1, st.session_state.t2, st.session_state.t3 = filled

# Initialize session state for the three ticker fields
for k in ("t1", "t2", "t3"):
    st.session_state.setdefault(k, "")

# Inputs
name   = st.text_input("Your name:")
region = st.selectbox("Where do you live?:", ["US", "Europe", "UK", "Asia", "South America", "Africa", "Australia"])

c1, c2, c3 = st.columns(3)
with c1:
    st.text_input("Type in a Ticker or Company", key="t1", on_change=_normalize_ticker, args=("t1",))
with c2:
    st.text_input("Ticker / Company 2", key="t2", on_change=_normalize_ticker, args=("t2",))
with c3:
    st.text_input("Ticker / Company 3", key="t3", on_change=_normalize_ticker, args=("t3",))

st.button("Randomize Empty Fields", on_click=_randomize_empty)

st.text_input("Your email address to receive the newsletter:", key="email")

# Placeholder for loading GIF
loader = st.empty()

if st.button("Submit"):
    email_stripped = st.session_state.email.strip()

    # Validation
    if not email_stripped:
        st.error("Please enter your email address.")
    elif not EMAIL_REGEX.match(email_stripped):
        st.error("Please enter a valid email address.")
    elif not name.strip():
        st.error("Please enter your name.")
    else:
        # Show centered, fixed-width loading GIF
        col_left, col_center, col_right = st.columns([1, 2, 1])
        with col_center:
            loader.image(
                GIF_URL,
                caption="Building your newsletter…",
                width=200,               # fixed 200px width
                use_container_width=False  # replace deprecated use_column_width
            )

        try:
            tickers = [to_ticker(st.session_state[k]) for k in ("t1", "t2", "t3")]
            build_and_send(name.strip(), region, tickers, email_stripped)
            loader.empty()  # remove the GIF
            st.success("✅ Newsletter sent to your inbox!")
        except Exception as e:
            loader.empty()
            st.error(f"Error: {e}")
