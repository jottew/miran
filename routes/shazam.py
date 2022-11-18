import traceback
import aiofiles
import asyncio
import string
import random
import magic
import utils
import json
import os

from io import BytesIO

from fastapi import Request, APIRouter, File
from starlette.responses import JSONResponse

from moviepy.video.io.VideoFileClip import VideoFileClip

from fastapi.security.api_key import APIKey
from utils import keys

router = APIRouter()

@router.post("/shazam")
async def shazam(request: Request, output: str, file: bytes = File(), Authorization: APIKey = None):
    api_key = await keys.get_api_key(request, Authorization)
    
    if len(file) > 500000000:
        return JSONResponse({"error": "Payload too large (over 500mb)"}, status_code=413)
    
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
        name = await request.app.db.fetchval("SELECT name FROM users WHERE api_key = $1", api_key)
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