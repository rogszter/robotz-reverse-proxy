from fastapi import FastAPI, Request
import httpx

app = FastAPI()

TARGET_URL = "https://robotz-results-592303669867.southamerica-east1.run.app"  # Your main API

@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(full_path: str, request: Request):
    method = request.method
    url = f"{TARGET_URL}/{full_path}"
    headers = dict(request.headers)
    body = await request.body()

    async with httpx.AsyncClient() as client:
        resp = await client.request(method, url, headers=headers, content=body)
    
    return {
        "status_code": resp.status_code,
        "content": resp.text
    }
