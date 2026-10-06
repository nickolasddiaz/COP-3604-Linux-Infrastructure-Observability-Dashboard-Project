#!/usr/bin/env python3
import asyncio
import threading
import streamlit as st
from database import TinyFluxDB
from streamlit.starlette import App
from contextlib import asynccontextmanager
import streamlit as st


from named_pipe import NamedPipe
from receiver import start_receiver


class Dashboard:

    def __init__(self) -> None:
        self.db = TinyFluxDB()
        self.namedPipe: NamedPipe = NamedPipe()

    async def start(self):
        await self.namedPipe.set_reading_mode()

        # create a new thread and allow it to print in the main console
        self.receiver_thread = threading.Thread(target=start_receiver)
        self.receiver_thread.start()

        self.scheduler_task = asyncio.create_task(self.background_scheduler())

    async def receive_from_client(self) -> None:
        """
        Receives a post message from the client and stores it in the DB
        """

        message = await self.namedPipe.receive_message()
        if message is None:
            return

        print("Received From app.py: ", message)
        #db.insert_data(data.macaddress, data.content)

    async def background_scheduler(self):
        while True:
            await self.receive_from_client()
            await asyncio.sleep(5) 



@asynccontextmanager
async def lifespan(app):
    # SETUP: Runs ONCE when the server boots up, before any user connects
    print("Initializing global server resources...")

    dashboard = Dashboard()
    await dashboard.start()
    
    yield  # The app runs while yielded

    print("Cleaning up global server resources...")


app = App("app.py", lifespan=lifespan)