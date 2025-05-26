import os
os.environ["OMP_NUM_THREADS"] = "1"

import gc
import cv2
import torch
import re
from ultralytics import YOLO
from paddleocr import PaddleOCR
import numpy as np
from datetime import datetime
import time

melhor_placa = None
presenca = False
path_salvamento_crops = r"\\srvbmflserver\BARRAMANSA\PUBLICO_BM\Rodrigo\Crops_OCR"

def lado_da_linha(p1, p2, ponto):
    """
    Retorna:
    > 0 → lado 1
    < 0 → lado 0
    = 0 → sobre a linha
    """
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

        # Configs para salvamento dos videos/crops
        #res_w, res_h = 1920, 1080
        path_salvamento = "resultados"
        os.makedirs(path_salvamento, exist_ok=True)
        #n_vid = len([f for f in os.listdir(path_salvamento) if f.endswith(".mp4")])
        #nome_video = f"{path_salvamento}/videos/1_video_{n_vid}.mp4"
        #video_writer = cv2.VideoWriter(nome_video, cv2.VideoWriter_fourcc(*"mp4v"), 4, (res_w, res_h))
        pasta_crops = criar_pasta_run(r"\\srvbmflserver\BARRAMANSA\PUBLICO_BM\Rodrigo\Crops_OCR")
        contador_crops = 1

        # Inicialização
        model = YOLO(r"best_13.05.pt")
        print("[PLACAS] Modelo YOLO carregado com sucesso")
        ocr = PaddleOCR(use_angle_cls=True, use_gpu = False)
        print("[OCR] Modelo PaddleOCR carregado com sucesso")
        print(f"IP: {ip_camera}")

        cap = cv2.VideoCapture(ip_camera, cv2.CAP_FFMPEG)

        if not cap.isOpened():
            raise RuntimeError("[STREAM] Não foi possivel abrir o stream com OpenCV")

        while True:

            time.sleep(0.05)
            ret, frame = cap.read()

            if not ret:
                print("[STREAM] Falha ao ler frame. Tentando reconectar...")
                cap.release()
                cap = cv2.VideoCapture(ip_camera, cv2.CAP_FFMPEG)
                continue

            #video_writer.write(frame)
            frame_counter += 1 

            try:
                with torch.no_grad():
                    results = model.predict(source=frame, conf = 0.7, imgsz=640, iou = 0.6, half = True, device = "cuda", save = False, show = False)
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
                        if ultimo_lado == 0 and lado_atual == 1: # Entrou para area de interesse
                            presenca = True
                            melhor_placa = None
                            melhor_conf = 0
                        elif ultimo_lado == 1 and lado_atual == 0: # Saiu da area de interesse
                            presenca = False
                            melhor_placa = None
                            melhor_conf = 0

                ultimo_lado = lado_atual

                if lado_atual != 1:
                    print("[YOLO] Detecção FORA da ROI")
                    continue

                crop_cinza = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                clahe = cv2.createCLAHE(clipLimit=5.0, tileGridSize=(3,3))
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

                    # Seleciona apenas boxes de area maior que 15% para evitar leituras de palabras como: "BRASIL", "BR", etc
                    if area_det < 0.15 * area_crop:
                        print(f"[OCR] Ignorado por área pequena: {area_det:.2f} < 15% de {area_crop:.2f}") 
                        print(f"[OCR] PLACA ATUAL: {melhor_placa} CONF: {melhor_conf}") 
                        continue

                    # Reforça o uso da maior area da detecção
                    if area_det > maior_area:
                        
                        # Atualiza o valor da maior area
                        maior_area = area_det

                        # Ignora a leitura em caso de conf baixa ou tamanho do texto incompativel
                        if conf < CONF_THRESH or len(texto_limpo) < 6 or len(texto_limpo) > 8:
                            print(f"[OCR] Ignorado: '{texto_raw}' (conf: {conf:.2f}, len: {len(texto_limpo)})")
                            print(f"[OCR] PLACA ATUAL: {melhor_placa} CONF: {melhor_conf}") 
                            continue
                        
                        # Seleciona o a leitura caso ela seja a maior conf até o momento. Atualiza as variaveis de melhor_placa e melhor_conf
                        if conf > melhor_conf:
                            melhor_placa = texto_limpo
                            melhor_conf = conf
                            print(f"[PLACA] {melhor_placa} (conf: {melhor_conf:.2f})")
                        else:
                            print(f"[OCR] Ignorando '{texto_raw}' (conf: {conf:.2f}, len: {len(texto_limpo)} por não ser a melhor conf")
                            print(f"[OCR] PLACA ATUAL: {melhor_placa} CONF: {melhor_conf}") 
                    else:
                        print(f"[OCR] Ignorando '{texto_raw}' (conf: {conf:.2f}, len: {len(texto_limpo)} devido a área")
                        print(f"[OCR] PLACA ATUAL: {melhor_placa} CONF: {melhor_conf}") 
                        continue
                
                #cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            #if melhor_placa:
                #cv2.putText(frame, f"Placa: {melhor_placa}", (20, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            #cv2.line(frame, (LINHA_PT1, 0), (LINHA_PT1, res_h), (0, 0, 255), 2)
            #cv2.putText(frame, status, (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            #cv2.imshow("Stream RTSP via PyAV", cv2.resize(frame, (1280, 720)))

            del results
            gc.collect() 

            if frame_counter % FRAME_CHECK_INTERVAL == 0:
                torch.cuda.empty_cache()
    finally:
        #video_writer.release()
        pass