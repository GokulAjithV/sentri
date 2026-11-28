import time
import jwt, secrets
from fastapi import HTTPException, Security, APIRouter, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings
from pydantic import BaseModel

security = HTTPBearer()

def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    """Verify the JWT token and return the payload."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

EXPLORE_SUBJECT = "explore-user"
INCIDENT_SUBJECT = "triage-incident" # must match app/notify/links.py

def require_explore_user(payload: dict = Depends(verify_jwt_token)):
    if payload["sub"] != EXPLORE_SUBJECT:
        raise HTTPException(status_code=403, detail="This token cannot access 'Explore'")
    return payload

def require_incident_user(payload: dict = Depends(verify_jwt_token)):
    if payload["sub"] != INCIDENT_SUBJECT:
        raise HTTPException(status_code=403, detail="This token cannot access 'Incident Chat'")
    return payload

router = APIRouter()

class LoginRequest(BaseModel):
    password: str

@router.post("/auth/login")
async def login(body: LoginRequest):
    # compare_digest takes the same time whether the first or last character is wrong

    if not secrets.compare_digest(body.password.encode(), settings.EXPLORE_PASSWORD.encode()):
        raise HTTPException(status_code=401, detail="Invalid Password")
    
    now = int(time.time())
    expires_in = settings.EXPLORE_SESSION_EXPIRY_HOURS * 3600
    token = jwt.encode(
        {"sub": EXPLORE_SUBJECT, "iat": now, "exp": now + expires_in},
        settings.JWT_SECRET,
        algorithm="HS256",
    )
    return {"access_token": token, "token_type": "bearer", "expires_in": expires_in}
