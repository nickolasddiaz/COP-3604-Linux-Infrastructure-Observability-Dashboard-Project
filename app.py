import streamlit as st
from pydantic import BaseModel
from database import TinyFluxDB

db = TinyFluxDB()

class MessageData(BaseModel):
    macaddress: str
    content: dict


def receive_from_client(data: MessageData) -> None:
    """
    Receives a post message from the client and stores it in the DB
    """
    # To-do start a server to receive POST requests from /metrics
    db.insert_data(data.macaddress, data.content)




# To-do display the contents of the db data
st.title("COP-3604 Linux Infrastructure Observability Dashboard Project")
x = st.slider("Select a value")
st.write(x, "squared is", x * x)