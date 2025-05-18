from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from models.request_model import UserRequest
from agents.router_agent import RouterAgent
from dotenv import load_dotenv
import json
import os

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv('CORS_ORIGIN')], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

router_agent = RouterAgent()

@app.post("/process")
async def process_request(request: Request):
    data = await request.json()
    user_request = UserRequest(**data)
    
    async def generate():
        async for chunk in router_agent.handle(user_request):
            yield f"data: {json.dumps({'content': chunk})}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")
