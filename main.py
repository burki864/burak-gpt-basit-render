from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/")
def health():
    return {"status": "BurakGPT ayakta 🟢"}

@app.post("/ask")
async def ask(request: Request):
    data = await request.json()
    prompt = data.get("prompt")

    if not prompt:
        return JSONResponse(
            status_code=400,
            content={"error": "prompt gerekli"}
        )

    # şimdilik sahte cevap
    return {"answer": f"BurakGPT diyor ki: {prompt}"}
