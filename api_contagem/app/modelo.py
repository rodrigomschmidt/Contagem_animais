import torch
import gc
from ultralytics import YOLO
from utilitarios import load_config

def carregar_modelo():
    torch.cuda.empty_cache()
    gc.collect()
    config = load_config("config/config_contagem.txt")
    caminho_modelo = config["caminho_modelo"]
    modelo = YOLO(caminho_modelo)
    modelo.eval()
    modelo.to("cuda")
    print("[YOLO] Modelo carregado com sucesso")
    return modelo

