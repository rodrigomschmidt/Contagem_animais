import os
import sys
# Adiciona caminho da DLL do cuDNN
os.add_dll_directory(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\bin")
# Evita uso excessivo de threads OpenMP
os.environ["OMP_NUM_THREADS"] = "1"
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),"..")))
from fastapi import FastAPI
from contextlib import asynccontextmanager
from threading import Thread
from detector_210_pyav_ import leitura_placas, get_placa_atual, get_estado_atual

def load_config(config_file):

    config = {}
    try:
        with open(config_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
        return config

    except FileNotFoundError:
        print(f"Erro: arquivo de configuração não encontrado em {config_file}")
        raise
    except Exception as e:
        print(f"Erro ao carregar configuração: {e}")
        raise

@asynccontextmanager

async def lifespan(app: FastAPI):
    ip_camera = "rtsp://admin:czcz8910@192.168.42.55/Streaming/Channels/101?transport=tcp" #p1
    #ip_camera = r"C:\Users\rodrigo.schmidt\Documents\Python\Detect_placas\Videos_dataset\ok\ok2\video_1.mp4"
    LINHA_P1 = (750, 1080)
    LINHA_P2 = (1100, 0)
    thread = Thread(target= leitura_placas, args=(ip_camera, LINHA_P1, LINHA_P2), daemon = True)
    thread.start()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/placa")
def obter_placa():
    placa = get_placa_atual()
    return placa

@app.get("/estado")
def obter_estado():
    estado = get_estado_atual()
    return estado

if __name__ == "__main__":
    import uvicorn
    print("Subindo API Leitura de Placas")
    uvicorn.run(app, host="0.0.0.0", port=8015)
    #uvicorn main_p5:app --host 0.0.0.0 --port 8015