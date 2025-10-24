import streamlit as st

animal_shelter = ["dog", "cat", "rabbit", "hamster", "parrot"]
animal = st.text_input("Enter your favorite animal:")
if st.button("Check Animal"):
    if animal.lower in animal_shelter:
        st.success(f"{animal} is available for adoption!")
    else:
        st.error(f"Sorry, {animal} is not available for adoption.")
