import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),"..")))

from fastapi import FastAPI
from contextlib import asynccontextmanager
import threading
from clp_monitor import escutar_clp, get_liberar_contagem

thread_clp = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global thread_clp
    print("[CLP_API] Iniciando leitura do CLP...")
    thread_clp = threading.Thread(target=escutar_clp, daemon=True)
    thread_clp.start()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/estado_clp")
def estado_clp():
    estado = get_liberar_contagem()
    return estado


if __name__ == "__main__":
    import uvicorn
    print("Subindo API CLP")
    uvicorn.run(app, host="0.0.0.0", port=8002)
    #uvicorn main:app --host 0.0.0.0 --port 8002