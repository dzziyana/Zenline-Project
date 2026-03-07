import os

import uvicorn
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    port = int(os.getenv("MATCHER_PORT", "8081"))
    uvicorn.run("src.api.server:app", host="0.0.0.0", port=port, reload=True)
