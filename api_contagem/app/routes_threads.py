from fastapi import APIRouter, HTTPException, Response
from schemas import RequisicaoContador
from contador_thread import contador
from state_threads import camera_states
from video_stream_threads import get_frame_atual
from threading import Thread
import cv2

router = APIRouter()

@router.post("/iniciar/{camera_id}")
def iniciar(camera_id: str, req: RequisicaoContador):
    if camera_id not in camera_states:
        raise HTTPException(status_code=404, detail="Câmera não encontrada")
    state = camera_states[camera_id]
    if state.executando:
        return {"status": "erro", "mensagem": "Já em execução."}

    req_data = req.model_dump()
    def executar():
        state.executando = True
        state.stream_pronto = False
        try:
            state.ultimo_resultado = contador(
                state.modelo,
                **req_data,
                get_frame_func=lambda: get_frame_atual(camera_id),
                set_frame_callback=state.set_ultimo_frame,
                camera_id=camera_id  # Passa camera_id explicitamente
            )
        finally:
            state.executando = False
            state.stream_pronto = False

    state.parar_event.clear()
    thread = Thread(target=executar)
    thread.start()
    
    return {"status": "ok", "mensagem": f"Contagem iniciada para {camera_id}"}

@router.post("/parar/{camera_id}")
def parar(camera_id: str):
    if camera_id not in camera_states:
        raise HTTPException(status_code=404, detail="Câmera não encontrada")
    camera_states[camera_id].parar_event.set()
    return {"status": "ok", "mensagem": f"Parada solicitada para {camera_id}"}

@router.get("/status/{camera_id}")
def status(camera_id: str):
    if camera_id not in camera_states:
        raise HTTPException(status_code=404, detail="Câmera não encontrada")
    return {"executando": camera_states[camera_id].executando}

@router.get("/resultado/{camera_id}")
def resultado(camera_id: str):
    if camera_id not in camera_states:
        raise HTTPException(status_code=404, detail="Câmera não encontrada")
    return {"contagem": camera_states[camera_id].ultimo_resultado}

@router.get("/frame/{camera_id}")
def frame(camera_id: str):
    if camera_id not in camera_states:
        raise HTTPException(status_code=404, detail="Câmera não encontrada")
    if camera_states[camera_id].ultimo_frame is None:
        raise HTTPException(status_code=404, detail="Nenhum frame disponível")
    ret, buffer = cv2.imencode(".jpg", camera_states[camera_id].ultimo_frame)
    if not ret:
        raise HTTPException(status_code=500, detail="Erro ao codificar frame")
    return Response(buffer.tobytes(), media_type="image/jpeg")

@router.get("/stream_pronto/{camera_id}")
def stream_pronto(camera_id: str):
    if camera_id not in camera_states:
        raise HTTPException(status_code=404, detail="Câmera não encontrada")
    return {"pronto": camera_states[camera_id].stream_pronto}