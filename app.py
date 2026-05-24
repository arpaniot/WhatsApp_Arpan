import streamlit as st
import random
from supabase import create_client, Client
import time

# 1. Database Configuration
# Replace these with your actual Supabase credentials found under Project Settings -> API
SUPABASE_URL = "YOUR_SUPABASE_PROJECT_URL"
SUPABASE_KEY = "YOUR_SUPABASE_ANON_KEY"

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    supabase = init_supabase()
except Exception as e:
    st.error("Failed to connect to the database. Please check your Supabase credentials.")

st.set_page_config(page_title="SecureChat", page_icon="💬", layout="centered")
st.title("💬 SecureChat Model")
st.caption("A secure, phone-number-free messaging application")

# 2. Session State Initialization
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "active_chat" not in st.session_state:
    st.session_state.active_chat = None

# Helper function to check if a Chat ID already exists
def id_exists(chat_id):
    res = supabase.table("users").select("chat_id").eq("chat_id", chat_id).execute()
    return len(res.data) > 0

# 3. Authentication UI
if not st.session_state.user_id:
    tab1, tab2 = st.tabs(["🔐 Login", "🆕 Register (Get Random ID)"])
    
    with tab1:
        login_id = st.text_input("Enter your 6-Digit Chat ID", key="login_id")
        login_pass = st.text_input("Password", type="password", key="login_pass")
        if st.button("Log In", use_container_width=True):
            res = supabase.table("users").select("*").eq("chat_id", login_id).eq("password", login_pass).execute()
            if len(res.data) > 0:
                st.session_state.user_id = login_id
                st.success(f"Welcome back, {login_id}!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Invalid Chat ID or Password.")
                
    with tab2:
        st.write("Click below to generate a completely random account identity.")
        reg_pass = st.text_input("Choose a Secure Password", type="password", key="reg_pass")
        
        if st.button("Generate My Account ID", use_container_width=True):
            if not reg_pass:
                st.warning("Please provide a password to protect your account.")
            else:
                # Generate a unique 6 digit string number
                while True:
                    new_id = str(random.randint(100000, 999999))
                    if not id_exists(new_id):
                        break
                
                # Insert to database
                supabase.table("users").insert({"chat_id": new_id, "password": reg_pass}).execute()
                st.success(f"🎉 Account Created successfully!")
                st.info(f"**YOUR UNIQUE CHAT ID:** {new_id}")
                st.caption("Copy this number down! Share it with your friends so they can add you.")

# 4. Chat Interface UI
else:
    # Sidebar for profiling and switching chats
    with st.sidebar:
        st.subheader(f"👤 Your ID: {st.session_state.user_id}")
        if st.button("Logout", color="red"):
            st.session_state.user_id = None
            st.session_state.active_chat = None
            st.rerun()
        
        st.write("---")
        friend_id = st.text_input("💬 Connect with a Friend's ID:")
        if st.button("Open Chat"):
            if friend_id == st.session_state.user_id:
                st.error("You cannot chat with yourself.")
            elif id_exists(friend_id):
                st.session_state.active_chat = friend_id
                st.success(f"Connected to {friend_id}!")
                st.rerun()
            else:
                st.error("User ID not found.")

    # Main Chat View Window
    if st.session_state.active_chat:
        st.subheader(f"Chatting with: {st.session_state.active_chat}")
        
        # Live Polling Strategy to grab recent updates from Supabase
        # Pulls messages where (Sender=Me AND Receiver=Friend) OR (Sender=Friend AND Receiver=Me)
        query_me_to_friend = supabase.table("messages").select("*").eq("sender_id", st.session_state.user_id).eq("receiver_id", st.session_state.active_chat)
        query_friend_to_me = supabase.table("messages").select("*").eq("sender_id", st.session_state.active_chat).eq("receiver_id", st.session_state.user_id)
        
        all_msg = query_me_to_friend.execute().data + query_friend_to_me.execute().data
        # Sort chronologically by creation timestamp
        all_msg = sorted(all_msg, key=lambda k: k['created_at'])

        # Display historical message streams container
        chat_container = st.container(height=400)
        with chat_container:
            for msg in all_msg:
                alignment = "user" if msg['sender_id'] == st.session_state.user_id else "assistant"
                with st.chat_message(alignment):
                    st.caption(f"**{msg['sender_id']}**")
                    if msg['message_type'] == 'text':
                        st.write(msg['content'])
                    elif msg['message_type'] == 'image':
                        st.image(msg['content'])
                    elif msg['message_type'] == 'audio':
                        st.audio(msg['content'])

        # Media and Text Input Elements below conversation window
        msg_input = st.chat_input("Type your message here...")
        
        col1, col2 = st.columns(2)
        with col1:
            img_url = st.text_input("🖼️ Paste Image URL to send photo:")
            if st.button("Send Photo") and img_url:
                supabase.table("messages").insert({
                    "sender_id": st.session_state.user_id,
                    "receiver_id": st.session_state.active_chat,
                    "message_type": "image",
                    "content": img_url
                }).execute()
                st.rerun()
                
        with col2:
            audio_url = st.text_input("🎵 Paste Audio file URL (.mp3):")
            if st.button("Send Audio") and audio_url:
                supabase.table("messages").insert({
                    "sender_id": st.session_state.user_id,
                    "receiver_id": st.session_state.active_chat,
                    "message_type": "audio",
                    "content": audio_url
                }).execute()
                st.rerun()

        if msg_input:
            supabase.table("messages").insert({
                "sender_id": st.session_state.user_id,
                "receiver_id": st.session_state.active_chat,
                "message_type": "text",
                "content": msg_input
            }).execute()
            st.rerun()

        # Add a light update refresh button for real-time tracking sync
        if st.button("🔄 Refresh Messages"):
            st.rerun()
    else:
        st.info("👈 Enter a friend's 6-digit ID in the sidebar menu to start chatting securely!")
  
