import aiofiles
import asyncio
import magic
import utils
import os

from io import BytesIO

from fastapi import Response, APIRouter, Request, File
from starlette.responses import JSONResponse

from moviepy.video.io.VideoFileClip import VideoFileClip

from fastapi.security.api_key import APIKey
from utils import keys

router = APIRouter()

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

@router.post("/video-to-mp3")
async def video_to_mp3(request: Request, file: bytes = File(), Authorization: APIKey = None):
    api_key = await keys.get_api_key(request, Authorization)
    
    if len(file) > 500000000:
        return JSONResponse({"error": "Payload too large (over 500mb)"}, status_code=413)
    
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