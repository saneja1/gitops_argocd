import streamlit as st

st.set_page_config(page_title="Test Server", layout="centered")

st.markdown(
    """
    <style>
        .stApp {
            background-color: black;
        }
        h1 {
            color: white;
        }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("This is a test server - v6")
import this_module_does_not_exist
