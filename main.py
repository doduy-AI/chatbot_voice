from fastapi import FastAPI
import uvicorn
from core.config import settings , setup_cors
from api.main import api_router


app = FastAPI(title=settings.PROJECT_NAME)
setup_cors(app)
app.include_router(api_router, prefix=settings.API_VERSION)

if __name__ == "__main__":
    print(f"--- Server {settings.PROJECT_NAME} khởi động tại {settings.HOST}:{settings.PORT} ---")
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=False)