import os
import asyncpg
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI()

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "dev_secret")
)

templates = Jinja2Templates(directory="templates")

DATABASE_URL = os.getenv("DATABASE_URL")
CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")
BOT_OWNER_IDS = [int(x) for x in os.getenv("BOT_OWNER_IDS", "").split(",") if x]

@app.on_event("startup")
async def startup():
    if DATABASE_URL:
        app.state.db = await asyncpg.create_pool(DATABASE_URL)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/login")
async def login():
    return RedirectResponse(
        f"https://discord.com/oauth2/authorize"
        f"?client_id={CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope=identify%20guilds"
    )

@app.get("/callback")
async def callback(request: Request, code: str):
    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://discord.com/api/oauth2/token",
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        token_json = token_res.json()
        access_token = token_json["access_token"]

        user_res = await client.get(
            "https://discord.com/api/users/@me",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        user = user_res.json()

    request.session["user"] = user
    return RedirectResponse("/dashboard")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/login")

    return HTMLResponse(f"<h1>Welcome {user['username']}</h1><br><a href='/'>Home</a>")
