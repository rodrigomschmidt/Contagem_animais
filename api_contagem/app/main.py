import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from fastapi import FastAPI
from contextlib import asynccontextmanager
from routes import router
from video_stream import iniciar_leitura_continua, parar_leitura
from modelo import carregar_modelo
from state import estado_contador
import threading

estado_contador.modelo = carregar_modelo()
thread_leitura = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global thread_leitura
    print("[CONTAGEM] Iniciando leitura de video...")
    thread_leitura = threading.Thread(target=iniciar_leitura_continua, daemon=True)
    thread_leitura.start()
    yield
    print("[CONTADOR] Parando leitura...")
    parar_leitura()

app = FastAPI(lifespan=lifespan)

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    print("Subindo API Contagem")
    uvicorn.run(app, host="0.0.0.0", port=8000)
