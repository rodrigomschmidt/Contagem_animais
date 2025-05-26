from threading import Event
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
            del self.ultimo_frame  # <-- Libera o frame anterior da memória
            gc.collect()           # <-- Garante liberação mais imediata
        self.ultimo_frame = frame.copy()  # <-- Garante independência da referência
        self.stream_pronto = True

estado_contador = EstadoContador()
set_ultimo_frame = estado_contador.set_ultimo_frame
parar_event = estado_contador.parar_event
