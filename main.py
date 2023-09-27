from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import json
import os

from agent.run import WebSocketManager



app = FastAPI()
app.mount("/site", StaticFiles(directory="client"), name="site")
# Dynamic directory for outputs once first research is run
@app.on_event("startup")
def startup_event():
    if not os.path.isdir("outputs"):
        os.makedirs("outputs")
    app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

templates = Jinja2Templates(directory="client")

manager = WebSocketManager()


@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse('index.html', {"request": request, "report": None})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data.startswith("start"):
                json_data = json.loads(data[6:])
                task = json_data.get("task")
                if task:
                    await manager.start_streaming(task, websocket)
                else:
                    print("Error: not enough parameters provided.")

    except WebSocketDisconnect:
        await manager.disconnect(websocket)

import logging
import sys

log_format_str = "%(levelname)s: %(asctime)s - %(name)s - %(message)s"
formatter = logging.Formatter(log_format_str)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.DEBUG)

logging.basicConfig(
    level=logging.DEBUG,
    format=log_format_str,
    handlers=[
        console_handler
    ],
)

root_logger = logging.getLogger('')
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(console_handler)



# logging.getLogger('langchain.retrievers.multi_query').setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)
logger.info('TEst1')
logging.info('Test 2')

#google_search_tool = Tool(
#    name="Google Search Snippets",
#    description="Search Google for recent results.",
#    func=top_google_results,
#)

if __name__ == "__main__":

    
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
