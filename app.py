#!/usr/bin/env python3


# To-do display the contents of the db data
import streamlit as st


st.title("COP-3604 Linux Infrastructure Observability Dashboard Project")
x = st.slider("Select a value")
st.write(x, "squared is", x * x)