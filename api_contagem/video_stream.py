import threading
import time
import cv2
from utilitarios import load_config
import gc

config = load_config("config/config_contagem.txt")

frame_atual = None
stream_ativo = False

def iniciar_leitura_continua(url):
    print("[STREAM] Iniciando leitura contínua da câmera (PyAV direto):")
    t = threading.Thread(target=_ler_video, daemon=True, args=(url,))
    t.start()

def parar_leitura():
    global stream_ativo
    stream_ativo = False

def _ler_video(url):
    global stream_ativo, frame_atual
    stream_ativo = True
    delay_reconnect = 5

    while stream_ativo:
        cap = None
        try:
            print("[STREAM] Tentando conectar à câmera via OpenCV...")
            cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)

            if not cap.isOpened():
                raise Exception("Falha ao abrir o stream RTSP com OpenCV.")

            print("[STREAM] Conectado e recebendo frames.")

            while stream_ativo:
                ret, frame = cap.read()
                if not ret:
                    print("[STREAM] Falha ao ler frame. Encerrando leitura...")
                    break
                frame_atual = frame

        except Exception as e:
            print(f"[STREAM] Erro inesperado: {e}")

        finally:
            if cap:
                cap.release()
                del cap

            frame = None
            gc.collect()

        print("[STREAM] Conexão encerrada. Tentando reconectar...")
        if stream_ativo:
            time.sleep(delay_reconnect)

    print("[STREAM] Thread de leitura encerrada.")

def get_frame_atual():
    global frame_atual
    return frame_atual if frame_atual is not None else None