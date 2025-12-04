from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
import httpx
import asyncio
from typing import Dict, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Reverse Proxy Service")

# Service mapping configuration
SERVICE_MAPPING: Dict[str, str] = {
    "send_results": "https://robotz-results-592303669867.southamerica-east1.run.app",
    # NEW MAPPINGS FOR GOOGLE APPS SCRIPTS
    "instructions": "https://script.google.com/macros/s/AKfycbwroCVMllaJmL75b9B5j-td5oFWhleheKERQzmVQUGD9bOH04Ekpgttbr3MKrb7rIiM4A/exec",
    "licenses": "https://script.google.com/macros/s/AKfycbyteIDtFzFMUSufnlfEU_nY1pvRuFvsXBMHMu7tSP26VLpmUBnl-fe2GiMqUcY83qhI/exec",
    "telegram": "https://script.google.com/macros/s/AKfycbydN_gMIEkDHtFZGA8qGJCixj3ZVVQ7wJOfB2AOnfWaL51hacbM92Is6-ldwVmdlFrJYg/exec",
    "results": "https://script.google.com/macros/s/AKfycbxtLIJAK1c-oHIPf-jh8i1czm7qXVGskw4ymkDURF0kBxzbmYWlJeTNuRe2W065lki6rw/exec",
    # "serviceB": "https://secondExampleURL.com",
    # Add more services here as needed
    # "serviceC": "https://thirdExampleURL.com",
}

# HTTP client configuration
client = httpx.AsyncClient(
    timeout=httpx.Timeout(30.0),  # 30 seconds timeout
    limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
)

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up HTTP client on shutdown"""
    await client.aclose()

@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run"""
    return {"status": "healthy", "services": list(SERVICE_MAPPING.keys())}

# ------------------------------------------------------------------
# DEDICATED APPS SCRIPT ROUTES (FIX for MetaTrader Redirect Issue)
# These specific routes ensure POST/GET methods are handled without redirection
# as the path is explicitly defined without a trailing slash issue.
# ------------------------------------------------------------------

# Generic proxy function reused by the specific routes
async def generic_proxy(service_name: str, request: Request, path: str = ""):
    # Check if service exists in mapping
    if service_name not in SERVICE_MAPPING:
        logger.warning(f"Service not found: {service_name}")
        raise HTTPException(
            status_code=404, 
            detail=f"Service '{service_name}' not found. Available services: {list(SERVICE_MAPPING.keys())}"
        )
    
    target_base_url = SERVICE_MAPPING[service_name].rstrip('/')
    
    # Smarter URL construction: Append path only if present
    target_url = target_base_url
    if path:
        target_url = target_base_url + f"/{path}"

    # Add query parameters if they exist
    query_params = str(request.url.query)
    if query_params:
        target_url += f"?{query_params}"
    
    logger.info(f"Proxying {request.method} {request.url} -> {target_url}")
    
    try:
        # Prepare headers (exclude host header to avoid conflicts)
        headers = dict(request.headers)
        headers.pop("host", None)
        
        # Get request body for POST/PUT/PATCH requests
        body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()
        
        # Make the proxied request
        response = await client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=body,
            follow_redirects=True
        )
        
        # Prepare response headers (exclude certain headers that shouldn't be forwarded)
        excluded_headers = {
            "content-encoding", "content-length", "transfer-encoding", 
            "connection", "upgrade", "proxy-authenticate", "proxy-authorization"
        }
        
        response_headers = {
            key: value for key, value in response.headers.items()
            if key.lower() not in excluded_headers
        }
        
        # Return streaming response
        async def generate():
            async for chunk in response.aiter_bytes():
                yield chunk
        
        return StreamingResponse(
            generate(),
            status_code=response.status_code,
            headers=response_headers,
            media_type=response.headers.get("content-type")
        )
        
    except httpx.TimeoutException:
        logger.error(f"Timeout when proxying to {target_url}")
        raise HTTPException(status_code=504, detail="Gateway timeout")
    
    except httpx.RequestError as e:
        logger.error(f"Request error when proxying to {target_url}: {str(e)}")
        raise HTTPException(status_code=502, detail="Bad gateway")
    
    except Exception as e:
        logger.error(f"Unexpected error when proxying to {target_url}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.api_route("/instructions", methods=["GET", "POST"])
async def proxy_instructions(request: Request):
    return await generic_proxy("instructions", request)

@app.api_route("/licenses", methods=["GET", "POST"])
async def proxy_licenses(request: Request):
    return await generic_proxy("licenses", request)

@app.api_route("/telegram", methods=["GET", "POST"])
async def proxy_telegram(request: Request):
    return await generic_proxy("telegram", request)

@app.api_route("/results", methods=["GET", "POST"])
async def proxy_telegram(request: Request):
    return await generic_proxy("results", request)

# FALLBACK GENERIC ROUTE (Only used if the above specific routes don't match)
@app.api_route("/{service_name}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def reverse_proxy_generic(service_name: str, path: str, request: Request):
    return await generic_proxy(service_name, request, path)
# ------------------------------------------------------------------

@app.get("/")
async def root():
    """Root endpoint showing available services"""
    return {
        "message": "Reverse Proxy Service",
        "available_services": list(SERVICE_MAPPING.keys()),
        "usage": "/{service_name}/{path}"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
