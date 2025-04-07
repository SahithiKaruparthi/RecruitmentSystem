# ui/login.py
import streamlit as st
from utils.auth_utils import create_user, authenticate_user, get_password_hash, get_user_from_token, create_access_token

def show_login_page():
    """Display login/registration page"""
    st.title("Recruitment AI Portal")
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
            
            if submitted:
                user = authenticate_user(username, password)
                if user:
                    st.session_state.user = user
                    st.session_state.token = create_access_token(
                        {"sub": user.username, "role": user.role}
                    )
                    st.rerun()
                else:
                    st.error("Invalid credentials")

    with tab2:
        with st.form("register_form"):
            new_username = st.text_input("Username")
            new_email = st.text_input("Email")
            new_password = st.text_input("Password", type="password")
            role = st.selectbox("Role", ["user", "admin"], disabled=True)
            submitted = st.form_submit_button("Register")
            
            if submitted:
                if create_user(new_username, new_email, new_password, role):
                    st.success("Registration successful! Please login.")
                else:
                    st.error("Username or email already exists")