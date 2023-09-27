import asyncio
import datetime
import logging

from typing import List, Dict
from fastapi import WebSocket
from config import check_openai_api_key
from agent.research_agent import ResearchAgent


class WebSocketManager:
    print("Run")
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.sender_tasks: Dict[WebSocket, asyncio.Task] = {}
        self.message_queues: Dict[WebSocket, asyncio.Queue] = {}

    async def start_sender(self, websocket: WebSocket):
        print("Start sender")
        queue = self.message_queues[websocket]
        while True:
            message = await queue.get()
            print(f"Next message: {message}")
            if websocket in self.active_connections:
                await websocket.send_text(message)
            else:
                break

    async def connect(self, websocket: WebSocket):
        print("Connecting")
        await websocket.accept()
        self.active_connections.append(websocket)
        self.message_queues[websocket] = asyncio.Queue()
        self.sender_tasks[websocket] = asyncio.create_task(self.start_sender(websocket))

    async def disconnect(self, websocket: WebSocket):
        print("Disconnecting")
        self.active_connections.remove(websocket)
        self.sender_tasks[websocket].cancel()
        del self.sender_tasks[websocket]
        del self.message_queues[websocket]

    async def start_streaming(self, task, websocket):
        print("Start streaming")
        await websocket.send_json({"type": "logs", "output": f"🫡 Starting the task {task}"})
        agent = await run_agent(task, websocket)
        return agent


async def run_agent(task, websocket):
    check_openai_api_key()

    start_time = datetime.datetime.now()
    start_time_string = start_time.strftime("%Y-%m-%d %H:%M:%S")

    print(f"Start time {start_time_string}")
    await websocket.send_json({"type": "logs", "output": f"⏱️ Start time: {start_time_string}\n\n"})

    assistant = ResearchAgent(task, websocket)
    await assistant.conduct_research()

    end_time = datetime.datetime.now()
    end_time_string = end_time.strftime("%Y-%m-%d %H:%M:%S")
    await websocket.send_json({"type": "logs", "output": f"\n⏱️ End time: {end_time_string}\n"})
    await websocket.send_json({"type": "logs", "output": f"\n⏱️ Total run time: {end_time - start_time}\n"})

    return assistant
