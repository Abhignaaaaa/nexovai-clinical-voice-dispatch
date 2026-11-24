import os
import sys
from dotenv import load_dotenv

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)

for env_path in [
    os.path.join(ROOT_DIR, ".env"),
    os.path.join(CURRENT_DIR, ".env"),
    os.path.join(os.getcwd(), ".env"),
    os.path.join(os.getcwd(), "backend", ".env")
]:
    if os.path.isfile(env_path):
        load_dotenv(env_path, override=True)

if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    print(f"\n-> Server starting on http://127.0.0.1:{port} (host: {host})")
    uvicorn.run("app.server:app", host=host, port=port, reload=True)