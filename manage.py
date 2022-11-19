import argparse
import asyncpg
import asyncio
import secrets
import os

import uvloop

from dotenv import load_dotenv
load_dotenv()

async def main(parser: argparse.ArgumentParser):
    args = parser.parse_args()

    db = await asyncpg.create_pool(dsn=f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@localhost/miran")
    await db.execute("CREATE TABLE IF NOT EXISTS users (name TEXT PRIMARY KEY, api_key TEXT)")
    
    if args.action.lower() == "adduser":
        if not args.value:
            return print("kys")
        while True:
            api_key = secrets.token_hex(16)
            res = input(f"is {api_key} oki?: ")
            if res.lower() == "y":
                break
            
        value = value = args.value[0]
        try:
            await db.execute("INSERT INTO users (name, api_key) VALUES ($1, $2)", value, api_key)
        except asyncpg.exceptions.UniqueViolationError:
            res = input(f"user {value} already exists, do you want to replace the api key?: ")
            if res.lower() == "y":
                oapi_key = await db.fetchval("SELECT api_key FROM users WHERE name = $1", value)
                await db.execute("UPDATE users SET api_key = $1 WHERE user = $2", api_key, value)
                napi_key = await db.fetchval("SELECT api_key FROM users WHERE name = $1", value)
                if napi_key == api_key and oapi_key != napi_key:
                    print("Replaced successfully")
                else:
                    print("Failed to replace")
            else:
                exit()
                
    if args.action.lower() == "deluser":
        if not args.value:
            return print("kys")
            
        value = args.value[0]
        val = await db.fetchrow("SELECT * FROM users WHERE name = $1", value)
        
        if not val:
            return print("that user doesnt exist")
        
        await db.execute("DELETE FROM users WHERE name = $1", value)
        
        nval = await db.fetchrow("SELECT * FROM users WHERE name = $1", value)
        
        if not nval:
            return print("Removed user successfully")
        print("Failed to remove user")
        
    if args.action.lower() == "listusers":
        val = await db.fetch("SELECT * FROM users")
        
        for user in val:
            print(f"{user['name']}: {user['api_key']}")
            
    if args.action.lower() == "getkey":
        if not args.value:
            return print("kys")
            
        value = args.value[0]
        val = await db.fetchval("SELECT api_key FROM users WHERE name = $1", value)
        
        if not val:
            return print("that user doesnt exist")
        
        print(f"{value}: {val}")
        
    if args.action.lower() == "identifykey":
        if not args.value:
            return print("kys")
            
        value = args.value[0]
        val = await db.fetchval("SELECT name FROM users WHERE api_key = $1", value)
        
        if not val:
            return print("that key doesnt exist")
        
        print(f"{val}: {value}")
        
    if args.action.lower() == "execute":
        value = " ".join(args.value)
        print(str(await db.execute(value)))
        
    if args.action.lower() == "fetch":
        value = " ".join(args.value)
        print(str(await db.fetch(value)))
        
    if args.action.lower() == "fetchrow":
        value = " ".join(args.value)
        print(str(await db.fetchrow(value)))
        
    if args.action.lower() == "fetchval":
        value = " ".join(args.value)
        print(str(await db.fetchval(value)))

if __name__ == "__main__":
    uvloop.install()
    
    parser = argparse.ArgumentParser(prog='api management')
    parser.add_argument("action"),
    parser.add_argument("value", nargs="*")
    
    asyncio.run(main(parser))