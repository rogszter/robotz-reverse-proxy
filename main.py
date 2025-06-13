from fastapi import FastAPI, Request, HTTPException
import httpx

app = FastAPI()

TARGET_URL = "https://robotz-results-592303669867.southamerica-east1.run.app"  # Main backend

@app.api_route("/send_results/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(full_path: str, request: Request):
    method = request.method
    # Strip the "/send_results/" prefix and forward to backend
    url = f"{TARGET_URL}/{full_path}"
    headers = dict(request.headers)
    body = await request.body()

    async with httpx.AsyncClient() as client:
        resp = await client.request(method, url, headers=headers, content=body)
    
    return {
        "status_code": resp.status_code,
        "content": resp.text
    }
