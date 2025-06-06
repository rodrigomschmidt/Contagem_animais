import av
import cv2
import time
import gc
import os
import re
import numpy as np
import torch
from paddleocr import PaddleOCR
from datetime import datetime
from threading import Lock

# Configurações do ambiente
os.add_dll_directory(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\bin")
os.environ["OMP_NUM_THREADS"] = "1"

# Configurações
CONF_THRESH = 0.65
clahe = cv2.createCLAHE(clipLimit=5.0, tileGridSize=(3, 3))
ocr = PaddleOCR(use_angle_cls=True, use_gpu=True)
print("[OCR] PaddleOCR carregado com sucesso")

# Armazenamento de estado por câmera (thread-safe)
class CameraState:
    def __init__(self):
        self.melhor_placa = None
        self.melhor_conf = 0
        self.presenca = False
        self.ultimo_lado = None
        self.lock = Lock()  # Garante acesso thread-safe

# Dicionário global para armazenar estados por câmera
camera_states = {}

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

def get_placa_atual(camera_id):
    state = camera_states.get(camera_id)
    if state:
        with state.lock:
            return state.melhor_placa
    return None

def get_estado_atual(camera_id):
    state = camera_states.get(camera_id)
    if state:
        with state.lock:
            return state.presenca
    return False

def criar_pasta_run(base_dir, camera_id):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = os.path.join(base_dir, f"run_{camera_id}_{timestamp}")
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
            print(f"[INFO] Conectando ao stream {rtsp_url}...")
            container = av.open(rtsp_url, options=options)
            stream = next(s for s in container.streams if s.type == 'video')
            print(f"[INFO] Stream {rtsp_url} conectado.")
            return container, stream
        except av.AVError as e:
            print(f"[RECONEXÃO] Erro ao abrir stream {rtsp_url}: {e}. Tentando novamente em 2s...")
            time.sleep(2)

def leitura_placas(rtsp_url, linha_p1, linha_p2, camera_id, model):
    global camera_states
    camera_states[camera_id] = CameraState()  # Inicializa estado para a câmera
    state = camera_states[camera_id]
    
    path_salvamento = r"\\srvbmflserver\BARRAMANSA\PUBLICO_BM\Rodrigo\Crops_OCR"
    contador_crops = 1
    frame_counter = 0
    pasta_crops = criar_pasta_run(path_salvamento, camera_id)

    while True:
        container, stream = abrir_stream(rtsp_url)
        try:
            for packet in container.demux(stream):
                for frame in packet.decode():
                    frame_counter += 1
                    # Processar apenas 1 em cada 3 frames para reduzir carga
                    if frame_counter % 3 != 0:
                        continue

                    imagem = frame.to_ndarray(format="bgr24")

                    with torch.no_grad():
                        results = model.predict(
                            imagem, conf=0.7, imgsz=640, iou=0.6, half=True, device="cuda", verbose=True
                        )

                    boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
                    confidences = results[0].boxes.conf.cpu().numpy()

                    for box, conf in zip(boxes, confidences):
                        x1, y1, x2, y2 = box


                        crop = imagem[y1:y2, x1:x2]

                        crop_path = os.path.join(pasta_crops, f"crop_{camera_id}_{contador_crops}.jpg")
                        cv2.imwrite(crop_path, crop)
                        contador_crops += 1

                        centro = ((x1 + x2) // 2, (y1 + y2) // 2)
                        valor = lado_da_linha(linha_p1, linha_p2, centro)
                        lado_atual = 1 if valor > 0 else 0

                        with state.lock:
                            if state.ultimo_lado is not None:
                                if lado_atual != state.ultimo_lado:
                                    if state.ultimo_lado == 0 and lado_atual == 1:
                                        state.presenca = True
                                        state.melhor_placa = None
                                        state.melhor_conf = 0
                                    elif state.ultimo_lado == 1 and lado_atual == 0:
                                        state.presenca = False
                                        state.melhor_placa = None
                                        state.melhor_conf = 0

                            state.ultimo_lado = lado_atual

                            if state.ultimo_lado is None and lado_atual == 1:
                                state.presenca = True
                                state.melhor_placa = None
                                state.melhor_conf = 0

                            print(f"[YOLO] LADO ATUAL É {lado_atual}")

                            if lado_atual != 1:
                                print(f"[YOLO] Detecção FORA da ROI (câmera {camera_id})")
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
                                        print(f"[OCR] Ignorado por área pequena: {area_det:.2f} < 15% de {area_crop:.2f} (câmera {camera_id})")
                                        continue

                                    if area_det > maior_area:
                                        maior_area = area_det

                                        if conf < CONF_THRESH or len(texto_limpo) < 6 or len(texto_limpo) > 8:
                                            print("[OCR] CONF BAIXA - IGNORADO")
                                            continue

                                        if conf > state.melhor_conf:
                                            state.melhor_placa = texto_limpo
                                            state.melhor_conf = conf
                                            print(f"[PLACA] {state.melhor_placa} (conf: {state.melhor_conf:.2f}, câmera {camera_id})")

                            except Exception as e:
                                print(f"[OCR] Erro (câmera {camera_id}): {e}")
                                continue
                    
                    if frame_counter % 100 == 0:  # Limpar VRAM com mais frequência
                        torch.cuda.empty_cache()
                        gc.collect()

                    
                    cv2.line(imagem, linha_p1, linha_p2, (0, 255, 0), 2)

                    for box in boxes:
                        x1, y1, x2, y2 = box
                        cv2.rectangle(imagem, (x1, y1), (x2, y2), (0, 0, 255), 2)

                    cv2.imshow(f"Camera {camera_id}", imagem)

                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        print("[INFO] Tecla 'q' pressionada. Encerrando leitura.")
                        cv2.destroyAllWindows()
                        break

        except Exception as e:
            print(f"[RECONEXÃO] Erro crítico no stream (câmera {camera_id}): {e}. Reiniciando...")
        finally:
            try:
                if 'container' in locals() and container:
                    container.close()
                    del container
                if 'stream' in locals():
                    del stream
            except Exception as ex:
                print(f"[AVISO] Falha ao liberar recursos do stream (câmera {camera_id}): {ex}")
            torch.cuda.empty_cache()
            gc.collect()
            continue

if __name__ == "__main__":
    from ultralytics import YOLO
    model = YOLO(r"C:\Users\rodrigo.schmidt\Documents\Python\Contagem_Animais\api_ocr\app\best_13.05.pt")
    CAMERAS =  {
        "id": "P5",
        "rtsp_url": "rtsp://admin:czcz8910@192.168.42.54/Streaming/Channels/101?transport=tcp",
        "linha_p1": (0, 400),
        "linha_p2": (1280, 200)
    }
    leitura_placas(CAMERAS["rtsp_url"], CAMERAS["linha_p1"], CAMERAS["linha_p2"], CAMERAS["id"], model)
