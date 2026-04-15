from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import sys

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, you should refine this to [ "http://localhost:1420", "tauri://localhost" ]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/hello")
def read_hello():
    return {"message": "Hello from FastAPI Backend!"}

if __name__ == "__main__":
    # When bundled, we might want to pass dynamic port or just bind to a specific one.
    # We will use 8000 for simplicity as skeleton, but it can be passed via args.
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    uvicorn.run(app, host="127.0.0.1", port=port)
