from pydantic import BaseModel

class UserRequest(BaseModel):
    walletAddress: str
    chain: str
    input: str
