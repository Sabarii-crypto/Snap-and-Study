
 
import streamlit as st
from google import genai
from google.genai import types
import smtplib 
from email.mime.text import MIMEText
 

 
from prompts import SUMMARY_REQUEST_PROMPT, SYSTEM_PROMPT, WELCOME_MESSAGE_TEMPLATE
 
MODEL_NAME = "gemini-3.5-flash"
st.set_page_config(page_title="Snap & Study", page_icon="📚")
 
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
GMAIL_ADDRESS = st.secrets["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = st.secrets["GMAIL_APP_PASSWORD"]


@st.cache_resource
def get_gemini_client():
    return genai.Client(api_key=GEMINI_API_KEY)
 


gemini_client = get_gemini_client()


def send_email(to_address, subject, body):
    message = MIMEText(body)
    message["Subject"] = subject
    message["From"] = GMAIL_ADDRESS
    message["To"] = to_address
 
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.send_message(message)


def render_message(message):
    with st.chat_message(message["role"]):
        if message["kind"] == "text":
            st.write(message["content"])
        elif message["kind"] == "image":
            st.image(message["content"])
 
 
def add_message(role, kind, content):
    st.session_state.messages.append({"role": role, "kind": kind, "content": content})
    render_message(st.session_state.messages[-1])


def ask_gemini(parts):
    try:
        return st.session_state.chat.send_message(parts).text
    except Exception as error:
        return f"Sorry, something went wrong: {error}"



if 'onboarded' not in st.session_state:
    st.title("Welcome to Snap & Study 📚") 
    st.caption("Snap it. Understand it. Study smarter. 📸📚")
    with st.form("onboarding_form"):
        name = st.text_input("What's your name?", placeholder="Enter your name")
        email_address = st.text_input(
            "What's your email address?", placeholder="Enter your email address"
        )
        submitted = st.form_submit_button("Let's get started!")
        if submitted:
            if not name.strip() or not email_address.strip():
                st.error("Please fill in all fields to continue.")
            else:
                st.session_state.name = name.strip()
                st.session_state.email_address = email_address.strip()
                st.session_state.chat = gemini_client.chats.create(model=MODEL_NAME,config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
                )
                st.session_state.messages = []
                st.session_state.onboarded = True
                st.rerun()
    st.stop()

header_col, button_col = st.columns([5, 2], vertical_alignment="center")
 
with header_col:
    st.title("Snap & Study 📚")

send_disabled = False

if st.button(
    "📧 Send explanation to Email", 
    disabled=send_disabled, 
    use_container_width=True
):
    with st.spinner("Summarizing your study session..."):
        summary = ask_gemini([SUMMARY_REQUEST_PROMPT])

    try:
        send_email(
            st.session_state.email_address,
            "Your Snap & Study Explanation 📚",
            summary
        )

        st.success("Sent! Check your email 📧")

    except Exception as error:
        st.error(f"Couldn't send the email: {error}")

st.caption(
    f"Logged in as {st.session_state.name} - explanations go to {st.session_state.email_address}"
)
 
if not st.session_state.messages:
    add_message("assistant", "text", WELCOME_MESSAGE_TEMPLATE.format(name=st.session_state.name))
else:
    for message in st.session_state.messages:
        render_message(message)
 
user_input = st.chat_input(
    "Ask a question, or attach a photo of a problem, diagram, or notes you don't understand.",
    accept_file=True,
    file_type=["jpg", "jpeg", "png"],
)

if user_input:
    photo = user_input.files[0] if user_input.files else None
    text = user_input.text
    parts = []
 
    if photo is not None:
        photo_bytes = photo.getvalue()
        add_message("user", "image", photo_bytes)
        parts.append(types.Part.from_bytes(data=photo_bytes, mime_type=photo.type))
    if text:
        add_message("user", "text", text)
        parts.append(text)
    elif photo is not None:
        parts.append("What is this? Explain it in simple terms and help me understand the key concept.")
 
    with st.spinner("Getting results..."):
        answer = ask_gemini(parts)
    add_message("assistant", "text", answer)
