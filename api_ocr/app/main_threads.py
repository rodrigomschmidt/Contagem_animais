import os
import sys
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from threading import Thread
from ultralytics import YOLO
from detector_threads import leitura_placas, get_placa_atual, get_estado_atual

# Configurações do ambiente
os.add_dll_directory(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\bin")
os.environ["OMP_NUM_THREADS"] = "1"
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Configurações das câmeras
CAMERAS = [
    {
        "id": "P1",
        "rtsp_url": "rtsp://admin:czcz8910@192.168.42.54/Streaming/Channels/101?transport=tcp",
        "linha_p1": (0, 433),
        "linha_p2": (733, 0),
    },
    {
        "id": "P5",
        "rtsp_url": "rtsp://admin:czcz8910@192.168.42.55/Streaming/Channels/101?transport=tcp",
        "linha_p1": (500, 720),
        "linha_p2": (733, 0),
    },
]

# Carregar o modelo YOLO uma única vez (compartilhado entre threads)
model = YOLO("best_13.05.pt")
print("[YOLO] Modelo carregado com sucesso")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Iniciar uma thread para cada câmera
    threads = []
    for camera in CAMERAS:
        thread = Thread(
            target=leitura_placas,
            args=(
                camera["rtsp_url"],
                camera["linha_p1"],
                camera["linha_p2"],
                camera["id"],
                model,  # Passar o modelo compartilhado
            ),
            daemon=True,
        )
        threads.append(thread)
        thread.start()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/placa/{camera_id}")
def obter_placa(camera_id: str):
    if camera_id not in [cam["id"] for cam in CAMERAS]:
        raise HTTPException(status_code=404, detail="Câmera não encontrada")
    placa = get_placa_atual(camera_id)
    return {"camera_id": camera_id, "placa": placa}

@app.get("/estado/{camera_id}")
def obter_estado(camera_id: str):
    if camera_id not in [cam["id"] for cam in CAMERAS]:
        raise HTTPException(status_code=404, detail="Câmera não encontrada")
    estado = get_estado_atual(camera_id)
    return {"camera_id": camera_id, "estado": estado}

if __name__ == "__main__":
    import uvicorn
    print("Subindo API Leitura de Placas")
    uvicorn.run(app, host="0.0.0.0", port=8000)