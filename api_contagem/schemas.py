from pydantic import BaseModel

class RequisicaoContador(BaseModel):
    caminho_output_base: str
    caminho_output_rede: str
    placa: str
    sequencial: str
    ordem_entrada: str
    data_abate: str
    ip: str
    rampa: str
