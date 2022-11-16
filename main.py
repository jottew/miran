import traceback
import aiofiles
import tempfile
import asyncpg
import asyncio
import random
import string
import base64
import magic
import utils
import json
import time
import os

from fastapi import Security, Depends, FastAPI, HTTPException, File, Request
from fastapi.security.api_key import APIKeyQuery, APIKeyHeader, APIKey

from starlette.status import HTTP_403_FORBIDDEN
from starlette.responses import JSONResponse, Response

from io import BytesIO

from moviepy.video.io.VideoFileClip import VideoFileClip

from dotenv import load_dotenv
load_dotenv()

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

api_key_query = APIKeyQuery(name="Authorization", auto_error=False)
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)
        
@utils.executor()
def convert_video_to_mp3(path: str, data: bytes, fmt: str):
    video = os.path.join(path, f"file.{fmt}")
    audio = os.path.join(path, "file.mp3")
    
    with open(video, "wb") as f:
        f.write(data)
        
    vid = VideoFileClip(video)
    vid.audio.write_audiofile(audio)
    vid.close()
    os.remove(video)
    
    return audio

@app.on_event("startup")
async def startup_event():
    app.db = await asyncpg.create_pool(dsn=f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@localhost/api")
    await app.db.execute("CREATE TABLE IF NOT EXISTS users (name TEXT PRIMARY KEY, api_key TEXT)")
    print("Initialized DB")


async def get_api_key(
    api_key_query: str = Security(api_key_query),
    api_key_header: str = Security(api_key_header),
):
    req = await app.db.fetch("SELECT api_key FROM users")
    
    keys = [i["api_key"] for i in req]
    
    if api_key_query in keys:
        return api_key_query
    elif api_key_header in keys:
        return api_key_header
    else:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="vallah invalid credentials"
        )
        
@app.get("/")
async def homepage():
    return "i love big black oiled up men"

@app.post("/video-to-mp3")
async def video_to_mp3(request: Request, file: bytes = File(), api_key: APIKey = Depends(get_api_key)):
    if len(file) > 100000000:
        return JSONResponse({"error": "Payload too large (over 100mb)"}, status_code=413)
    
    types = {
        "video/quicktime": "mov",
        "video/mp4": "mp4",
    }
    
    buf = BytesIO(file)
    content_type = magic.from_buffer(buf.read(2048), mime=True)
    
    if content_type not in types.keys():
        valid = utils.format_list(list(types.values()))
        return JSONResponse({"error": f"Unsupported media type passed, please use {valid}"}, status_code=400)
    
    fmt = types.get(content_type)
    
    async with aiofiles.tempfile.TemporaryDirectory() as d:
        try:
            path = await asyncio.wait_for(
                convert_video_to_mp3(
                    d,
                    file,
                    fmt
                ), 
                timeout=60
            )
        except asyncio.TimeoutError:
            return JSONResponse({"error": f"Conversion took over 60 seconds and has therefore been cancelled"}, status_code=408)

        async with aiofiles.open(path, "rb") as f:
            data = await f.read()
        
    return Response(data, media_type="audio/mpeg")
    

@app.post("/shazam")
async def shazam(request: Request, output: str, file: bytes = File(), api_key: APIKey = Depends(get_api_key)):
    if len(file) > 100000000:
        return JSONResponse({"error": "Payload too large (over 100mb)"}, status_code=413)
    
    types = {
        "video/quicktime": "mov",
        "video/mp4": "mp4",
        "audio/mpeg": "mp3",
        "audio/x-wav": "wav",
        "audio/ogg": "ogg"
    }
    
    buf = BytesIO(file)
    content_type = magic.from_buffer(buf.read(2048), mime=True)
    
    if content_type not in types.keys():
        valid = utils.format_list(list(types.values()))
        return JSONResponse({"error": f"Unsupported media type passed, please use {valid}"}, status_code=400)
    
    fmt = types.get(content_type)
    
    try:
        async with aiofiles.tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, f"song.{fmt}")
            
            with open(path, "wb") as f:
                f.write(file)
            
            cmd = f"songrec audio-file-to-recognized-song {path}"
            
            try:
                proc = await asyncio.wait_for(
                    asyncio.create_subprocess_shell(
                            cmd,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                    ), 
                    timeout=60
                )
            except asyncio.TimeoutError:
                return JSONResponse({"error": f"Recognition took over 60 seconds and has therefore been cancelled"}, status_code=408)
            
            prv = await proc.communicate()
            r = prv[0].decode()
            r2= prv[1].decode()
            if len(r) == 0:
                if len(r2) == 0:
                    raise Exception("Empty result received")
                raise Exception(f"stdout is empty, but stderr returned {r2}")
            
        try:
            res = json.loads(r).get("track", {})
        except Exception:
            raise Exception(f"Corrupted result received\nResult: {r}")
        
        if res == {}:
            return JSONResponse({"error": "Could not recognise song"}, status_code=417)
        
        return JSONResponse(res)
    except Exception as exc:
        fexc = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        error_id = ''.join(random.choices(string.ascii_letters+string.digits, k=12))
        name = await app.db.fetchval("SELECT name FROM users WHERE api_key = $1", api_key)
        async with aiofiles.open(f"errors/{error_id}.txt", "w") as f:
            data = f"""
host: {request.client.host}
user: {name}
key: {api_key}
url: {request.url}

{fexc}
""".rstrip()
            await f.write(data)
        return JSONResponse({"error": f"An error has occured during processing and has been reported with ID {error_id}"}, status_code=400)