import os
import sys
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from threading import Thread
from routes_threads import router
from video_stream_threads import iniciar_leitura_continua, parar_leitura, get_frame_atual
from utilitarios import load_config
from modelo import carregar_modelo
from state_threads import EstadoContador, yolo_lock, camera_states  # Importa yolo_lock de state

# Configurações do ambiente
os.add_dll_directory(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\bin")
os.environ["OMP_NUM_THREADS"] = "1"
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Configurações das câmeras
CAMERAS = [
    {
        "id": "P1",
        "url_key": "url_p1",
    },
    {
        "id": "P5",
        "url_key": "url_p5",
    },
]

@asynccontextmanager
async def lifespan(app: FastAPI):
    global camera_states
    config = load_config("config/config_contagem.txt")

    # Carregar modelo YOLO uma única vez
    print("[CONTAGEM] Carregando modelo...")
    model = carregar_modelo()

    # Inicializar estados e threads para cada câmera
    threads = []
    for camera in CAMERAS:
        camera_states[camera["id"]] = EstadoContador()
        camera_states[camera["id"]].modelo = model  # Compartilhar modelo
        url = config[camera["url_key"]]
        print(f"[CONTAGEM] Iniciando leitura de vídeo para {camera['id']}...")
        thread = Thread(target=iniciar_leitura_continua, args=(url, camera["id"]), daemon=True)
        threads.append(thread)
        thread.start()

    yield

    # Parar leitura ao encerrar
    print("[CONTADOR] Parando leitura...")
    parar_leitura()

app = FastAPI(lifespan=lifespan)
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    print("Subindo API Contagem Unificada")
    uvicorn.run(app, host="0.0.0.0", port=8007)