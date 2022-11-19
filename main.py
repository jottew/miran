import uvicorn
import asyncpg
import os

from fastapi import FastAPI

from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="miran.rest", docs_url=None, redoc_url=None)
if __name__ == "main":
    for route in os.listdir("routes"):
        if not route.endswith(".py"):
            continue
        name = f"routes.{route[:-3]}"
        imp = __import__(name)
        print(name)
        print(dir(imp))
        print(getattr(__import__(f"routes.{route[:-3]}"), route[:-3]).router)
        app.include_router(getattr(__import__(f"routes.{route[:-3]}"), route[:-3]).router) 

@app.on_event("startup")
async def startup_event():
    app.db = await asyncpg.create_pool(dsn=f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@localhost/api")
    await app.db.execute("CREATE TABLE IF NOT EXISTS users (name TEXT PRIMARY KEY, api_key TEXT)")
    print("Initialized DB")
        
@app.get("/")
async def homepage():
    return "i love big black oiled up men"

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5000, log_level="info")