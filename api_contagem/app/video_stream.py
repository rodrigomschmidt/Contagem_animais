import threading
import time
import cv2
from utilitarios import load_config
import gc
import av

config = load_config("config/config_contagem.txt")

frame_atual = None
stream_ativo = False

def iniciar_leitura_continua(url):
    print("[STREAM] Iniciando leitura contínua da câmera:")
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
        container = None
        try:
            print("[STREAM] Tentando conectar à câmera via PyAV...")
            container = av.open(
                url,
                timeout=5,
                options={
                    "fflags": "nobuffer",
                    "flags": "low_delay",
                    "rtsp_transport": "tcp",
                    "max_delay": "500000"  # em microssegundos = 500ms
                }
            )
            stream = container.streams.video[0]  # <-- único stream de vídeo
            print("[STREAM] Conectado e recebendo frames.")

            for packet in container.demux(stream):
                if not stream_ativo:
                    break
                
                for frame in packet.decode():
                    # Descartar os frames acumulados e manter só o último
                    frame_atual = frame.to_ndarray(format="bgr24")
                    break  # garante apenas o último frame útil do pacote

        except Exception as e:
            print(f"[STREAM] Erro inesperado: {e}")
        finally:
            if container:
                container.close()
            gc.collect()

        print("[STREAM] Conexão encerrada. Tentando reconectar...")
        if stream_ativo:
            time.sleep(delay_reconnect)

    print("[STREAM] Thread de leitura encerrada.")

def get_frame_atual():
    global frame_atual
    return frame_atual if frame_atual is not None else None