from pydantic import BaseModel

class RequisicaoContador(BaseModel):
    caminho_video_local: str
    caminho_video_rede: str
    placa: str
    sequencial: str
    ordem_entrada: str
    data_abate: str
    rampa: str
    
