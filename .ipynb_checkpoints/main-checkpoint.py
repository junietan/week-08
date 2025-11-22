import streamlit as st
from helper_functions.utility import check_password

def main():
    if not check_password():
        st.stop()

    animal_shelter = ["dog", "cat", "rabbit", "hamster", "parrot"]
    animal = st.text_input("Enter your favorite animal:")
    if st.button("Check Animal"):
        if animal and animal.lower() in animal_shelter:
            st.success(f"{animal} is available for adoption!")
        else:
            st.error(f"Sorry, {animal} is not available for adoption.")

if __name__ == "__main__":
    main()
