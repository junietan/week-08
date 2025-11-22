import streamlit as st
from helper_functions.utility import check_password

def main():
    # Configure page early
    st.set_page_config(page_title="DSJB Assessment Hub", layout="wide")

    # Password gate
    if not check_password():
        st.stop()

    st.title("DSJB Assessment Hub")
    st.write("Welcome. Use the sidebar to navigate the app pages:")
    st.markdown(
        """
        - Generate AIML Test Questions
        - Student Test
        - About Us
        - Student Analytics
        """
    )
    st.success("Authenticated. Choose a page from the sidebar to begin.")

if __name__ == "__main__":
    main()