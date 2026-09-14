from pydantic import BaseModel
from typing import Optional


class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict
    # Only set by the Google endpoint: "signed_in", "linked" or "created".
    # response_model filtering drops undeclared keys, so this has to be here
    # for the frontend to be able to say "linked your existing account".
    outcome: Optional[str] = None


class TokenData(BaseModel):
    username: Optional[str] = None