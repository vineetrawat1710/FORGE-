from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()


@app.get("/echo")
async def echo_get(request: Request):
    return JSONResponse({
        "method": request.method,
        "headers": dict(request.headers),
        "query": dict(request.query_params),
    })


@app.post("/echo")
async def echo_post(request: Request):
    body = await request.body()
    return JSONResponse({
        "method": request.method,
        "headers": dict(request.headers),
        "query": dict(request.query_params),
        "body": body.decode("utf-8", errors="replace"),
    })


@app.put("/echo")
async def echo_put(request: Request):
    body = await request.body()
    return JSONResponse({"method": request.method, "body": body.decode("utf-8", errors="replace")})


@app.patch("/echo")
async def echo_patch(request: Request):
    body = await request.body()
    return JSONResponse({"method": request.method, "body": body.decode("utf-8", errors="replace")})


@app.delete("/echo")
async def echo_delete(request: Request):
    return JSONResponse({"method": request.method})
