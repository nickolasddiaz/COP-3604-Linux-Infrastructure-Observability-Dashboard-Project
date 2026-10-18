import asyncio
import json
import threading
from starlette.websockets import WebSocket, WebSocketDisconnect
from starlette.routing import WebSocketRoute
from streamlit.starlette import App
from contextlib import asynccontextmanager
from database import AsyncTinyDB
from named_pipe import NamedPipe
from receiver import start_receiver

# Simple Connection Manager to track active WebSocket clients
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

class Dashboard:
    def __init__(self) -> None:
        self.db = AsyncTinyDB()
        self.namedPipe: NamedPipe = NamedPipe()

    async def start(self):
        print("Setting up named pipe reading mode...")
        await self.namedPipe.set_reading_mode()

        print("Starting receiver thread...")
        self.receiver_thread = threading.Thread(target=start_receiver, daemon=True)
        self.receiver_thread.start()

        print("Creating background scheduler task...")
        self.scheduler_task = asyncio.create_task(self.background_scheduler())
        print("Background scheduler successfully created.")

    async def receive_from_client(self) -> None:
        raw_message = await self.namedPipe.receive_message()
        if raw_message is None:
            return

        text_buffer = raw_message.decode("utf-8", errors="ignore").strip()
        decoder = json.JSONDecoder()
        idx = 0

        while idx < len(text_buffer):
            try:
                data, next_idx = decoder.raw_decode(text_buffer, idx)
                mac_address = data.get("mac_address", "unknown_mac")
                content = data.get("content", {})

                if isinstance(content, dict) and content:
                    clean_fields = {str(k): float(v) for k, v in content.items()}
                    asyncio.create_task(self.db.insert_data(mac_address, clean_fields))
                    print(f"Inserted into TinyDB ({mac_address}): {clean_fields}")

                    # Broadcast update immediately to all connected WS clients
                    asyncio.create_task(manager.broadcast({
                                            "mac_address": mac_address,
                                            "content": clean_fields
                                        }))

                idx = next_idx
                while idx < len(text_buffer) and text_buffer[idx].isspace():
                    idx += 1
            except json.JSONDecodeError as exc:
                print(f"Broken JSON in pipe: {exc}")
                break

    async def background_scheduler(self):
        while True:
            await self.receive_from_client()
            await asyncio.sleep(5) 

# Define custom WebSocket endpoint
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, listen for client messages if needed
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@asynccontextmanager
async def lifespan(app):
    print("Initializing global server resources...")
    dashboard = Dashboard()
    await dashboard.start()
    yield  # Runs while the app is active
    print("Cleaning up global server resources...")

# Pass custom routes to Streamlit's Starlette App wrapper
routes = [
    WebSocketRoute("/ws/telemetry", endpoint=websocket_endpoint)
]

app = App("app.py", lifespan=lifespan, routes=routes)