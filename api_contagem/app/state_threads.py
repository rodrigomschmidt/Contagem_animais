from threading import Event, Lock

class EstadoContador:
    def __init__(self):
        self._executando = False
        self._executando_lock = Lock()
        self.parar_event = Event()
        self.parametros = None
        self.resultado = None

    def set_executando(self, valor: bool, parametros: dict = None):
        with self._executando_lock:
            self._executando = valor
            if valor and parametros is not None:
                self.parametros = parametros

    def get_executando(self) -> bool:
        with self._executando_lock:
            return self._executando

    def reset(self):
        self.set_executando(False)
        self.parar_event.clear()

yolo_lock = Lock()

estado = EstadoContador()

estados_cameras = {}
