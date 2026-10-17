#!/usr/bin/env python3
import asyncio
import json
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
        print("Setting up named pipe reading mode...")
        await self.namedPipe.set_reading_mode()

        # create a new thread and allow it to print in the main console
        # start_receiver is a seprate process, which receives web requests and sends that data to the named pipe
        print("Starting receiver thread...")
        self.receiver_thread = threading.Thread(target=start_receiver, daemon=True)
        self.receiver_thread.start()

        # asynchronous read from the pipe every X amount of seconds 
        print("Creating background scheduler task...")
        self.scheduler_task = asyncio.create_task(self.background_scheduler())
        print("Background scheduler successfully created.")

    async def receive_from_client(self) -> None:
        """
        Receives a post message from the named pipe and stores it in the DB
        """

        raw_message = await self.namedPipe.receive_message()
        if raw_message is None:
            return

        text_buffer = raw_message.decode("utf-8", errors="ignore").strip()
        decoder = json.JSONDecoder()
        idx = 0

        # converting a raw string to a usable list of dictionaries
        # it is called every 5 seconds, there may be a change that more than one hit is requested
        while idx < len(text_buffer):
            try:
                data, next_idx = decoder.raw_decode(text_buffer, idx)
                mac_address = data.get("mac_address", "unknown_mac")
                content = data.get("content", {})

                if isinstance(content, dict) and content:
                    # Ensure all values are stored as floats
                    clean_fields = {str(k): float(v) for k, v in content.items()}
                    await self.db.insert_data(mac_address, clean_fields)
                    print(f"Inserted into TinyFluxDB ({mac_address}): {clean_fields}")

                idx = next_idx
                while idx < len(text_buffer) and text_buffer[idx].isspace():
                    idx += 1
            except json.JSONDecodeError as exc:
                print(f"Broken JSON in pipe: {exc}")
                break


    async def background_scheduler(self):
        while True:
            # windows specific printing will not work
            value = await self.receive_from_client()
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