import traceback
import aiofiles
import asyncio
import string
import random
import magic
import utils
import os

from fastapi import Request, APIRouter
from starlette.responses import JSONResponse, Response

from moviepy.video.io.VideoFileClip import VideoFileClip

from io import BytesIO

from fastapi.security.api_key import APIKey
from utils import keys

router = APIRouter()
platforms = ["tiktok", "youtube"]
outputs = ["audio", "video"]

@router.post("/download")
async def download(request: Request, url: str, platform: str, output: str, Authorization: APIKey = None):
    api_key = await keys.get_api_key(request, Authorization)
    
    if platform.lower() not in platforms:
        return JSONResponse({"error": f"Platform \"{platform}\" in not supported, please choose one of {utils.format_list(platforms)}"}, status_code=400)
    
    if output.lower() not in outputs:
        return JSONResponse({"error": f"Output \"{output}\" in not supported, please choose one of {utils.format_list(outputs)}"}, status_code=400)
    
    try:
        async with aiofiles.tempfile.TemporaryDirectory() as d:
            if output == "audio":
                cmd = f"yt-dlp --extract-audio --audio-format mp3 -o \"{d}/%(title)s.%(ext)s\" {url}"
            elif output == "video":
                cmd = f"yt-dlp -o \"{d}/%(title)s.%(ext)s\" {url}"
            
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
                return JSONResponse({"error": f"Download took over 60 seconds and has therefore been cancelled"}, status_code=408)
            
            
            
            prv = await proc.communicate()
            r = prv[0].decode()
            r2= prv[1].decode()
            if len(r) == 0:
                if len(r2) == 0:
                    raise Exception("Empty result received")
                raise Exception(f"stdout is empty, but stderr returned {r2}")
            
            fn = os.path.join(d, os.listdir(d)[0])
                
            async with aiofiles.open(fn, "rb") as f:
                data = await f.read()
                
            content_type = magic.from_buffer(BytesIO(data).read(2048), mime=True)
        
        return Response(content=data, media_type=content_type)
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