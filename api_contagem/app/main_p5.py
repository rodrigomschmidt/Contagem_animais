import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from fastapi import FastAPI
from contextlib import asynccontextmanager
from routes import router
from video_stream import iniciar_leitura_continua, parar_leitura
from utilitarios import load_config
from modelo import carregar_modelo
from state import estado_contador
import threading

thread_leitura = None
app = FastAPI()  # <-- Inicializado fora para ser reutilizado no __main__

@asynccontextmanager
async def lifespan(app: FastAPI):
    global thread_leitura
    config = load_config("config/config_contagem.txt")
    url = config["url_p5"]
    print("[CONTAGEM] Iniciando leitura de video...")
    thread_leitura = threading.Thread(target=iniciar_leitura_continua, args=(url,), daemon=True)
    thread_leitura.start()
    yield
    print("[CONTADOR] Parando leitura...")
    parar_leitura()

app.router.lifespan_context = lifespan
app.include_router(router)

if __name__ == "__main__":  # <-- Bloco adicionado para garantir compatibilidade com multiprocessing
    import uvicorn
    from multiprocessing import freeze_support  # <-- Necessário no Windows
    freeze_support()
    print("Subindo API Contagem")
    estado_contador.modelo = carregar_modelo()  # <-- Carrega o modelo dentro do processo principal
    uvicorn.run(app, host="0.0.0.0", port=8005)

    #uvicorn app.main_p1:app --host 0.0.0.0 --port 8001