import os
os.environ["OMP_NUM_THREADS"] = "1"

import gc
import torch
import re
from ultralytics import YOLO
from paddleocr import PaddleOCR
import numpy as np
from datetime import datetime
import time
import cv2  # Ainda necessário para CLAHE, filtros etc.
import av

melhor_placa = None
presenca = False
path_salvamento_crops = r"\\srvbmflserver\BARRAMANSA\PUBLICO_BM\Rodrigo\Crops_OCR"

def lado_da_linha(p1, p2, ponto):
    return (p2[0] - p1[0]) * (ponto[1] - p1[1]) - (p2[1] - p1[1]) * (ponto[0] - p1[0])

def area_quadrilatero(pontos):
    pontos = np.array(pontos)
    x = pontos[:, 0]
    y = pontos[:, 1]
    return 0.5 * abs(
        x[0]*y[1] + x[1]*y[2] + x[2]*y[3] + x[3]*y[0]
        - (y[0]*x[1] + y[1]*x[2] + y[2]*x[3] + y[3]*x[0])
    )

def limpar_placa_ocr(texto):
    return re.sub(r"[^A-Z0-9]", "", texto.upper().strip())

def placa_valida(texto):
    texto = limpar_placa_ocr(texto)
    return bool(re.match(r"^[A-Z]{3}[0-9]{4}$|^[A-Z]{3}[0-9][A-Z][0-9]{2}$", texto))

def criar_pasta_run(base_dir):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = os.path.join(base_dir, f"run_{timestamp}")
    os.makedirs(run_dir, exist_ok=True)
    print(f"[INFO] Pasta para crops criada: {run_dir}")
    return run_dir

def get_placa_atual():
    global melhor_placa
    return melhor_placa

def get_estado_atual():
    global presenca
    return presenca

def abrir_stream_pyav(ip_camera):
    return av.open(ip_camera, options={
        "rtsp_transport": "tcp",
        "stimeout": "5000000",
        "buffer_size": "2048000",
        "max_delay": "500000",
        "fflags": "nobuffer"
    })

def leitura_placas(ip_camera, LINHA_P1, LINHA_P2):
    global melhor_placa

    try:
        CONF_THRESH = 0.65
        FRAME_CHECK_INTERVAL = 600
        ultimo_lado = None
        melhor_placa = None
        melhor_conf = 0
        frame_counter = 0
        global presenca

        path_salvamento = "resultados"
        os.makedirs(path_salvamento, exist_ok=True)
        pasta_crops = criar_pasta_run(path_salvamento)
        contador_crops = 1

        model = YOLO(r"best_13.05.pt")
        print("[PLACAS] Modelo YOLO carregado com sucesso")
        ocr = PaddleOCR(use_angle_cls=True, use_gpu=True)
        print("[OCR] Modelo PaddleOCR carregado com sucesso")
        print(f"IP: {ip_camera}")

        container = abrir_stream_pyav(ip_camera)
        stream = container.streams.video[0]
        stream.thread_type = "AUTO"

        while True:
            try:
                for frame_av in container.decode(stream):
                    time.sleep(0.05)
                    frame = frame_av.to_ndarray(format="bgr24")
                    frame_counter += 1

                    try:
                        with torch.no_grad():
                            results = model.predict(source=frame, conf=0.7, imgsz=640, iou=0.6, half=True, device="cuda", save=False, show=False)
                    except RuntimeError as e:
                        print(f"Erro de inferencia: {e}")
                        torch.cuda.empty_cache()
                        continue

                    boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
                    confidences = results[0].boxes.conf.cpu().numpy()

                    for box, conf in zip(boxes, confidences):
                        x1, y1, x2, y2 = box
                        crop = frame[y1:y2, x1:x2]

                        if crop.size == 0:
                            continue

                        crop_path = os.path.join(pasta_crops, f"crop_{contador_crops}.jpg")
                        cv2.imwrite(crop_path, crop)
                        contador_crops += 1

                        centro = ((x1 + x2) // 2, (y1 + y2) // 2)
                        valor = lado_da_linha(LINHA_P1, LINHA_P2, centro)
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

                        crop_cinza = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                        clahe = cv2.createCLAHE(clipLimit=5.0, tileGridSize=(3, 3))
                        crop_bilateral = cv2.bilateralFilter(crop_cinza, d=7, sigmaColor=75, sigmaSpace=75)
                        crop_clahe = clahe.apply(crop_bilateral)

                        try:
                            resultado = ocr.ocr(crop_clahe, det=True, rec=True)
                        except Exception as e:
                            print(f"[OCR] Erro: {e}")
                            continue

                        if not resultado or not resultado[0]:
                            print("[OCR] Nenhum texto reconhecido")
                            continue

                        maior_area = 0

                        for det in resultado[0]:
                            texto_raw = det[1][0]
                            conf = det[1][1]
                            texto_limpo = limpar_placa_ocr(texto_raw)
                            area_det = area_quadrilatero(det[0])
                            area_crop = crop.shape[0] * crop.shape[1]

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

                    del results
                    gc.collect()
                    if frame_counter % FRAME_CHECK_INTERVAL == 0:
                        torch.cuda.empty_cache()

            except Exception as e:
                if "avcodec_send_packet()" in str(e) or hasattr(e, "__module__") and "av" in e.__module__ or isinstance(e, OSError):
                    print(f"[RECONEXÃO] Erro no stream: {e}. Tentando reconectar...")
                    try:
                        container.close()
                    except:
                        pass
                    time.sleep(1)
                    container = abrir_stream_pyav(ip_camera)
                    stream = container.streams.video[0]
                    stream.thread_type = "AUTO"
                else:
                    raise

    finally:
        try:
            container.close()
        except:
            pass
