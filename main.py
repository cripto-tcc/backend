from fastapi import FastAPI, Request
from models.request_model import UserRequest
from agents.router_agent import RouterAgent

app = FastAPI()
router_agent = RouterAgent()

@app.post("/process")
async def process_request(request: Request):
    data = await request.json()
    print("Recebido do frontend:", data)
    user_request = UserRequest(**data)
    response = await router_agent.handle(user_request)
    return {"message": response}
