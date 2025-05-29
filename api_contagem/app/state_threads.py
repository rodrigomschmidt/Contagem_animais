from threading import Event, Lock
import gc

class EstadoContador:
    def __init__(self):
        self.executando = False
        self.ultimo_resultado = None
        self.ultimo_frame = None
        self.stream_pronto = False
        self.parar_event = Event()
        self.modelo = None

    def set_ultimo_frame(self, frame):
        if self.ultimo_frame is not None:
            del self.ultimo_frame
            gc.collect()
        self.ultimo_frame = frame.copy()
        self.stream_pronto = True

# Lock compartilhado para acesso ao modelo YOLO
yolo_lock = Lock()

# Dicionário para armazenar estados por câmera
camera_states = {}