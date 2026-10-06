#!/usr/bin/env python3
import streamlit as st


# To-do display the contents of the db data

st.title("COP-3604 Linux Infrastructure Observability Dashboard Project")
x = st.slider("Select a value")
st.write(x, "squared is", x * x)