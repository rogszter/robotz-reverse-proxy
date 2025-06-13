from fastapi import FastAPI, Request, Response
import httpx
import os

app = FastAPI()

BACKEND_URL = "https://robotz-results-592303669867.southamerica-east1.run.app"

@app.api_route("/send_results/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(path: str, request: Request):
    method = request.method
    url = f"{BACKEND_URL}/{path}"  # removes /send_results prefix

    headers = dict(request.headers)
    body = await request.body()

    async with httpx.AsyncClient() as client:
        response = await client.request(method, url, headers=headers, content=body)

    # Return response with proper status code and headers
    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=dict(response.headers),
    )
