from fastapi import APIRouter, HTTPException
from schemas import RequisicaoContador
from states import estados_cameras

router = APIRouter()

@router.post("/iniciar/{camera_id}")
def iniciar(camera_id: str, req: RequisicaoContador):
    if camera_id not in estados_cameras:
        raise HTTPException(status_code=404, detail="Câmera não encontrada")

    state = estados_cameras[camera_id]
    if state.get_executando():
        return {"status": "erro", "mensagem": "Já em execução."}

    state.parar_event.clear()
    state.set_executando(True, parametros=req.model_dump())

    return {"status": "ok", "mensagem": f"Contagem iniciada para {camera_id}"}

@router.post("/parar/{camera_id}")
def parar(camera_id: str):
    if camera_id not in estados_cameras:
        raise HTTPException(status_code=404, detail="Câmera não encontrada")
    estados_cameras[camera_id].parar_event.set()
    return {"status": "ok", "mensagem": f"Parada solicitada para {camera_id}"}

@router.get("/status/{camera_id}")
def status(camera_id: str):
    if camera_id not in estados_cameras:
        raise HTTPException(status_code=404, detail="Câmera não encontrada")
    return {"executando": estados_cameras[camera_id].get_executando()}

@router.get("/resultado/{camera_id}")
def resultado(camera_id: str):
    if camera_id not in estados_cameras:
        raise HTTPException(status_code=404, detail="Câmera não encontrada")

    resultado = estados_cameras[camera_id].resultado
    return {"contagem": int(resultado) if resultado is not None else 0}


