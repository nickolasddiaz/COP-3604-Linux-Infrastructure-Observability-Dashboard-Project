#!/usr/bin/env python3
import os
from pathlib import Path
import errno
import asyncio


class NamedPipe:
    def __init__(self):
        self.FIFO_PATH = Path("/tmp/my_fifo")

        self.fd = None

        if not os.path.exists(self.FIFO_PATH):
            os.mkfifo(self.FIFO_PATH, 0o666)


    async def set_reading_mode(self):
        self.fd = os.open(self.FIFO_PATH, os.O_RDONLY | os.O_NONBLOCK)
        print("set_reading_mode")

    async def set_writing_mode(self):
        while self.fd is None:
            try:
                # Open will fail unless a reader is already active
                self.fd = os.open(self.FIFO_PATH, os.O_WRONLY | os.O_NONBLOCK)
            except OSError as e:
                if e.errno == errno.ENXIO:
                    print("No reader ready yet, retrying...")
                    await asyncio.sleep(1) # Yield execution briefly
                else:
                    raise

        print("set_writing_mode")


    async def send_message(self, message):
        os.write(self.fd, message)


    async def receive_message(self)-> str | None:
        try:
            # os.read yields bytes
            data = os.read(self.fd, 1024)
            if data:
                print(f"Received: {data.decode().strip()}")
        except OSError as e:
            # Error 11 (EAGAIN/EWOULDBLOCK) means no data is currently available
            if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
                pass # Continue instead of freezing


    def __exit__(self):
        os.close(self.fd)