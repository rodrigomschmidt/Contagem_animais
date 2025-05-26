from fastapi import APIRouter
from schemas import RequisicaoContador
from contador import contador
from state import estado_contador, set_ultimo_frame
from video_stream import get_frame_atual
from threading import Thread
import cv2
from fastapi import HTTPException, Response
from multiprocessing import Process, Queue  # <-- Adicionado para multiprocessamento
router = APIRouter()
thread: Thread = None

@router.post("/iniciar")
def iniciar(req: RequisicaoContador):
    if estado_contador.executando:
        return {"status": "erro", "mensagem": "Já em execução."}

    req_data = req.model_dump()
    def executar():
        estado_contador.executando = True
        estado_contador.stream_pronto = False
        try:
            estado_contador.ultimo_resultado = contador(estado_contador.modelo, **req_data, get_frame_func=get_frame_atual, set_frame_callback=set_ultimo_frame)
        finally:
            estado_contador.executando = False
            estado_contador.stream_pronto = False

    estado_contador.parar_event.clear()
    global thread
    thread = Thread(target=executar)
    thread.start()
    
    return {"status": "ok", "mensagem": "Contagem iniciada"}

@router.post("/parar")
def parar():
    estado_contador.parar_event.set()
    return {"status": "ok", "mensagem": "Parada solicitada"}

@router.get("/status")
def status():
    return {"executando": estado_contador.executando}

@router.get("/resultado")
def resultado():
    return {"contagem": estado_contador.ultimo_resultado}

@router.get("/frame")
def frame():
    if estado_contador.ultimo_frame is None:
        raise HTTPException(status_code=404, detail="Nenhum frame disponível")
    ret, buffer = cv2.imencode(".jpg", estado_contador.ultimo_frame)
    if not ret:
        raise HTTPException(status_code=500, detail="Erro ao codificar frame")
    return Response(buffer.tobytes(), media_type="image/jpeg")

@router.get("/stream_pronto")
def stream_pronto():
    return {"pronto": estado_contador.stream_pronto}
