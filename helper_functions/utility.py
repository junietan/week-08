import os  
import streamlit as st  
import hmac  
    
def check_password(secret_name: str = "password"):  
    """Return True if the user entered the correct password.  
  
    Looks for the password in st.secrets[secret_name] first, then  
    falls back to the STREAMLIT_PASSWORD environment variable.  
    If no secret is configured the function shows an error and returns False.  
    """  
    def password_entered():  
        entered = st.session_state.get("password", "")  
        secret = st.secrets.get(secret_name) or os.environ.get("STREAMLIT_PASSWORD")  
        if secret is None:  
            st.session_state["password_correct"] = False  
            return  
        if hmac.compare_digest(entered, secret):  
            st.session_state["password_correct"] = True  
            del st.session_state["password"]  
        else:  
            st.session_state["password_correct"] = False  
  
    # Already validated  
    if st.session_state.get("password_correct", False):  
        return True  
  
    # If no configured secret, inform the user  
    if not (st.secrets.get(secret_name) or os.environ.get("STREAMLIT_PASSWORD")):  
        st.error(  
            "App password is not configured. "  
            "Add `.streamlit/secrets.toml` with `password = \"...\"` or set STREAMLIT_PASSWORD env var."  
        )  
        return False  
  
    # Show password input  
    st.text_input("Password", type="password", on_change=password_entered, key="password")  
    if "password_correct" in st.session_state and not st.session_state["password_correct"]:  
        st.error("😕 Password incorrect")  
    return st.session_state.get("password_correct", False)
