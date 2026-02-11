from fastapi import FastAPI
from user.router import router as user_router


app = FastAPI()

app.include_router(user_router)


@app.get("/")
async def health_check():
    return {"status": "OK"}
