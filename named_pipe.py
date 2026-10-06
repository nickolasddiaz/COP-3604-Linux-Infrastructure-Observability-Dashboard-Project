#!/usr/bin/env python3
import os
import sys
import asyncio
from abc import ABC, abstractmethod
from pathlib import Path

NAME = "temp"
RECEIVING_BYTES = 1024

class AbstractNamedPipe(ABC):
    """
        Class to manage sending/receiving data from a Named Pipe
        implemented for both UNIX and windows systems

        if a reader you must run set_readig_mode at init
        after you can read data from receive_message

        if a writer you must run set_writing_mode at init
        after you can write data from send_message
    """
    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    async def set_reading_mode(self):
        """
            Opens the named pipe for reading
            Runs once at init
        """
        pass

    @abstractmethod
    async def set_writing_mode(self):
        """
            Opens the named pipe for writing
            Runs once at init
            It will block until set_reading_mode is ran
        """
        pass

    @abstractmethod
    async def send_message(self, message: bytes):
        pass

    @abstractmethod
    async def receive_message(self) -> bytes | None:
        pass

    @abstractmethod
    def close(self):
        pass


# Unix Implementation
class UnixNamedPipe(AbstractNamedPipe):
    def __init__(self):
        import errno
        self.errno = errno
        self.FIFO_PATH = Path(f"/tmp/{NAME}")
        self.fd = None

        if not os.path.exists(self.FIFO_PATH):
            os.mkfifo(self.FIFO_PATH, 0o666) # type: ignore

    async def set_reading_mode(self):
        self.fd = os.open(self.FIFO_PATH, os.O_RDONLY | os.O_NONBLOCK) # type: ignore

    async def set_writing_mode(self):
        while self.fd is None:
            try:
                self.fd = os.open(self.FIFO_PATH, os.O_WRONLY | os.O_NONBLOCK) # type: ignore
            except OSError as e:
                if e.errno == self.errno.ENXIO:
                    print("waiting for reading mode to be set")
                    await asyncio.sleep(1)
                else:
                    raise

    async def send_message(self, message: bytes):
        if self.fd is not None:
            os.write(self.fd, message)

    async def receive_message(self) -> bytes | None:
        if self.fd is None:
            return None
        chunks = []
        try:
            while True:
                data = os.read(self.fd, RECEIVING_BYTES)
                if not data:
                    break
                chunks.append(data)
        except OSError as e:
            if e.errno in (self.errno.EAGAIN, self.errno.EWOULDBLOCK):
                pass
            else:
                raise
        if chunks:
            data = b"".join(chunks)
            print(f"Data received: {data}")
            return data
        return None

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

# Windows Implementation based on https://gist.github.com/Coronon/6c6ef55bdccefab18779a8cef2ec3c97 

class WindowsNamedPipe(AbstractNamedPipe):
    def __init__(self):
        # Local imports 
        # imports isolated to Windows environment
        import win32pipe
        import win32file
        import win32event
        import pywintypes
        
        self.win32pipe = win32pipe
        self.win32file = win32file
        self.win32event = win32event
        self.pywintypes = pywintypes
        
        self.pipe_path = f"\\\\.\\pipe\\{NAME}"
        self.handle = None

    async def set_reading_mode(self):
        # Create a named pipe server instance
        self.handle = self.win32pipe.CreateNamedPipe(
            self.pipe_path,
            self.win32pipe.PIPE_ACCESS_DUPLEX | self.win32file.FILE_FLAG_OVERLAPPED,
            self.win32pipe.PIPE_TYPE_MESSAGE | self.win32pipe.PIPE_READMODE_MESSAGE | self.win32pipe.PIPE_NOWAIT,
            1, 65536, 65536, 0, None # type: ignore
        )
        # Non-blocking check for client connections
        try:
            self.win32pipe.ConnectNamedPipe(self.handle, None)
        except self.pywintypes.error as e:
            if e.winerror != 548: # ERROR_PIPE_LISTENING
                pass

    async def set_writing_mode(self):
        # Windows client side opening a named pipe
        while self.handle is None:
            try:
                self.handle = self.win32file.CreateFile(
                    self.pipe_path,
                    self.win32file.GENERIC_WRITE | self.win32file.GENERIC_READ,
                    0, None, self.win32file.OPEN_EXISTING,
                    self.win32file.FILE_FLAG_OVERLAPPED, None
                )
            except self.pywintypes.error:
                print("waiting for reading mode to be set")
                await asyncio.sleep(1) # Wait for server pipe to be created

    async def send_message(self, message: bytes):
        if self.handle is not None:
            self.win32file.WriteFile(self.handle, message) # type: ignore

    async def receive_message(self) -> bytes | None:
        if self.handle is None:
            return None
        chunks = []
        try:
            while True:
                _err, data = self.win32file.ReadFile(self.handle, RECEIVING_BYTES) # type: ignore
                if not data:
                    break
                chunks.append(data)
        except self.pywintypes.error as e:
            if e.winerror == 232: # ERROR_NO_DATA
                pass
            elif e.winerror == 109: # ERROR_BROKEN_PIPE (Client disconnected)
                self.close()
            else:
                raise
        if chunks:
            data = b"".join(chunks)
            # if running on a thread it won't print to console
            print(f"Data received: {data}")
            return data
        return None

    def close(self):
        if self.handle is not None:
            self.win32file.CloseHandle(self.handle) # type: ignore
            self.handle = None



# Exporting to the right platform
if sys.platform == 'win32':
    NamedPipe = WindowsNamedPipe
else:
    NamedPipe = UnixNamedPipe
