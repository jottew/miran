from fastapi import Security, HTTPException, Request
from fastapi.security.api_key import APIKeyQuery, APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN

async def get_api_key(request, api_key: str):
    if not request.headers.get("Authorization") and not api_key:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="vallah invalid credentials"
        )
    elif request.headers.get("Authorization") and not api_key:
        api_key = request.headers.get("Authorization")
    
    req = await request.app.db.fetch("SELECT api_key FROM users")
    
    keys = [i["api_key"] for i in req]

    if api_key not in keys:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="vallah invalid credentials"
        )
        
    return api_key