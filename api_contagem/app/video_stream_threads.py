import threading
import time
import cv2
from utilitarios import load_config
import gc
import av

config = load_config("config/config_contagem.txt")

# Armazenar frames por câmera
frames_atuais = {}
stream_ativos = {}
lock_frames = threading.Lock()

def iniciar_leitura_continua(url, camera_id):
    print(f"[STREAM] Iniciando leitura contínua da câmera {camera_id}...")
    t = threading.Thread(target=_ler_video, daemon=True, args=(url, camera_id))
    t.start()

def parar_leitura():
    global stream_ativos
    with lock_frames:
        for camera_id in stream_ativos:
            stream_ativos[camera_id] = False

def _ler_video(url, camera_id):
    global stream_ativos, frames_atuais
    with lock_frames:
        stream_ativos[camera_id] = True
    delay_reconnect = 5

    while stream_ativos.get(camera_id, False):
        container = None
        try:
            print(f"[STREAM] Tentando conectar à câmera {camera_id} via PyAV...")
            container = av.open(
                url,
                timeout=5,
                options={
                    "fflags": "nobuffer+discardcorrupt",
                    "flags": "low_delay",
                    "rtsp_transport": "tcp",
                    "max_delay": "500000",
                    "stimeout": "5000000" 
                }
            )
            stream = container.streams.video[0]
            print(f"[STREAM] Conectado e recebendo frames para {camera_id}.")

            for packet in container.demux(stream):
                if not stream_ativos.get(camera_id, False):
                    break
                try:
                    for frame in packet.decode():
                        img = frame.to_ndarray(format="bgr24")

                        # Protege contra frames inválidos
                        if img is None or img.size == 0:
                            print(f"[STREAM] Frame inválido ignorado ({camera_id})")
                            continue

                        with lock_frames:
                            frames_atuais[camera_id] = img
                        break  # Pegamos um frame válido e saímos
                except Exception as e:
                    print(f"[STREAM] Erro de decodificação em {camera_id}: {e}")
                    continue

        except Exception as e:
            print(f"[STREAM] Erro inesperado para {camera_id}: {e}")
        finally:
            if container:
                container.close()
            gc.collect()

        print(f"[STREAM] Conexão encerrada para {camera_id}. Tentando reconectar...")
        if stream_ativos.get(camera_id, False):
            time.sleep(delay_reconnect)

    print(f"[STREAM] Thread de leitura encerrada para {camera_id}.")

def get_frame_atual(camera_id):
    with lock_frames:
        frame = frames_atuais.get(camera_id)
        return frame.copy() if frame is not None else None