# main.py
import streamlit as st
from ui.login import show_login_page
from ui.company_dashboard import show_company_dashboard
from ui.applicant_portal import show_applicant_portal
from utils.auth_utils import get_user_from_token

def main():
    """Main application entry point"""
    st.set_page_config(page_title="AI Recruitment System", layout="wide")
    
    # Initialize session state
    if 'user' not in st.session_state:
        st.session_state.user = None
    
    # Check authentication
    if st.session_state.user:
        # Show appropriate dashboard based on role
        if st.session_state.user.role == "admin":
            show_company_dashboard()
        else:
            show_applicant_portal()
    else:
        show_login_page()

if __name__ == "__main__":
    main()