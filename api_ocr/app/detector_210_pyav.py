import av
import cv2
import time
import gc
import os
import re
import numpy as np
from ultralytics import YOLO
import torch
from paddleocr import PaddleOCR
from datetime import datetime


# Estados globais compartilhados
melhor_placa = None
melhor_conf = 0
presenca = False
path_salvamento_crops = r"\\srvbmflserver\BARRAMANSA\PUBLICO_BM\Rodrigo\Crops_OCR"

# Configurações
CONF_THRESH = 0.65
clahe = cv2.createCLAHE(clipLimit=5.0, tileGridSize=(3, 3))
ocr = PaddleOCR(use_angle_cls=True, use_gpu=True)
print("[OCR] PaddleOCR carregado com sucesso")

def lado_da_linha(p1, p2, ponto):
    return (p2[0] - p1[0]) * (ponto[1] - p1[1]) - (p2[1] - p1[1]) * (ponto[0] - p1[0])

def limpar_placa_ocr(texto):
    return re.sub(r"[^A-Z0-9]", "", texto.upper().strip())

def area_quadrilatero(pontos):
    pontos = np.array(pontos)
    x = pontos[:, 0]
    y = pontos[:, 1]
    return 0.5 * abs(
        x[0]*y[1] + x[1]*y[2] + x[2]*y[3] + x[3]*y[0]
        - (y[0]*x[1] + y[1]*x[2] + y[2]*x[3] + y[3]*x[0])
    )

def get_placa_atual():
    global melhor_placa
    return melhor_placa

def get_estado_atual():
    global presenca
    return presenca

def criar_pasta_run(base_dir):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = os.path.join(base_dir, f"run_{timestamp}")
    os.makedirs(run_dir, exist_ok=True)
    print(f"[INFO] Pasta para crops criada: {run_dir}")
    return run_dir

def abrir_stream(rtsp_url):
    options = {
        "rtsp_transport": "tcp",
        "fflags": "nobuffer",
        "stimeout": "5000000",
        "max_delay": "500000",
        "reorder_queue_size": "0",
        "analyzemaxduration": "0"
    }

    while True:
        try:
            print("[INFO] Conectando ao stream...")
            container = av.open(rtsp_url, options=options)
            stream = next(s for s in container.streams if s.type == 'video')
            print("[INFO] Stream conectado.")
            return container, stream
        except av.AVError as e:
            print(f"[RECONEXÃO] Erro ao abrir stream: {e}. Tentando novamente em 2s...")
            time.sleep(2)

def leitura_placas(rtsp_url, linha_p1, linha_p2):
    global melhor_placa, presenca
    model = YOLO("best_13.05.pt")
    print("[YOLO] Modelo carregado com sucesso")

    ultimo_lado = None
    path_salvamento = "resultados"
    contador_crops = 1
    frame_counter = 0
    pasta_crops = criar_pasta_run(path_salvamento)

    while True:
        container, stream = abrir_stream(rtsp_url)
        try:
            for packet in container.demux(stream):
                for frame in packet.decode():
                    frame_counter += 1
                    imagem = frame.to_ndarray(format="bgr24")

                    with torch.no_grad():
                        results = model.predict(imagem, conf=0.7, imgsz=640, iou=0.6, half=True, device="cuda", verbose=True)

                    boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
                    confidences = results[0].boxes.conf.cpu().numpy()

                    for box, conf in zip(boxes, confidences):
                        x1, y1, x2, y2 = box
                        crop = imagem[y1:y2, x1:x2]

                        crop_path = os.path.join(pasta_crops, f"crop_{contador_crops}.jpg")
                        cv2.imwrite(crop_path, crop)
                        contador_crops += 1

                        centro = ((x1 + x2) // 2, (y1 + y2) // 2)
                        valor = lado_da_linha(linha_p1, linha_p2, centro)
                        lado_atual = 1 if valor > 0 else 0

                        if ultimo_lado is not None:
                            if lado_atual != ultimo_lado:
                                if ultimo_lado == 0 and lado_atual == 1:
                                    presenca = True
                                    melhor_placa = None
                                    melhor_conf = 0
                                elif ultimo_lado == 1 and lado_atual == 0:
                                    presenca = False
                                    melhor_placa = None
                                    melhor_conf = 0

                        ultimo_lado = lado_atual

                        if lado_atual != 1:
                            print("[YOLO] Detecção FORA da ROI")
                            continue

                        crop = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                        crop = cv2.bilateralFilter(crop, d=7, sigmaColor=75, sigmaSpace=75)
                        crop = clahe.apply(crop)

                        try:
                            resultado = ocr.ocr(crop, det=True, rec=True)

                            maior_area = 0
                            area_crop = crop.shape[0] * crop.shape[1]

                            if not resultado or not resultado[0]:
                                continue

                            for det in resultado[0]:
                                texto_raw = det[1][0]
                                conf = det[1][1]
                                texto_limpo = limpar_placa_ocr(texto_raw)
                                area_det = area_quadrilatero(det[0])

                                if area_det < 0.15 * area_crop:
                                    print(f"[OCR] Ignorado por área pequena: {area_det:.2f} < 15% de {area_crop:.2f}") 
                                    continue

                                if area_det > maior_area:
                                    maior_area = area_det

                                    if conf < CONF_THRESH or len(texto_limpo) < 6 or len(texto_limpo) > 8:
                                        continue

                                    if conf > melhor_conf:
                                        melhor_placa = texto_limpo
                                        melhor_conf = conf
                                        print(f"[PLACA] {melhor_placa} (conf: {melhor_conf:.2f})")

                        except Exception as e:
                            print(f"[OCR] Erro: {e}")
                            continue

                    # Limpeza após cada frame
                    del results, boxes, confidences, imagem
                    if frame_counter % 500 == 0:
                        torch.cuda.empty_cache()
                    gc.collect()

        except Exception as e:
            print(f"[RECONEXÃO] Erro crítico no stream: {e}. Reiniciando...")

            try:
                if 'container' in locals() and container:
                    container.close()
                    del container
                if 'stream' in locals():
                    del stream
            except Exception as ex:
                print(f"[AVISO] Falha ao liberar recursos do stream: {ex}")

            torch.cuda.empty_cache()
            gc.collect()
            continue
