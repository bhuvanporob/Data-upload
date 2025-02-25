import streamlit as st
import pandas as pd

# Streamlit app
st.title("Data Manipulator")

# File uploader (accepts multiple files)
uploaded_files = st.file_uploader("Upload all csv files at once", type="csv", accept_multiple_files=True)

# Submit button
if st.button("view analysis"):
    if uploaded_files:
        st.success(f"{len(uploaded_files)} file(s) uploaded successfully!")
        # Display file names
        for uploaded_file in uploaded_files:
            st.write(f"- {uploaded_file.name}")
    else:
        st.warning("No files uploaded. Please upload at least one CSV file.")
