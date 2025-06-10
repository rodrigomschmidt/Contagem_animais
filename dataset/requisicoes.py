import requests
import time

class Requisicao():
    def __init__(self, u):
        self.api_url = u
        self.status_anterior = False

    def att_status_ant(self, status):
        self.status_anterior = status
        return
    
    def get_status_ant(self):
        return self.status_anterior
    
    def consultar_execucao(self, camera):
        time.sleep(1)
        if camera.id is not None:
            request = f"{self.api_url}/status/{camera.id}"
        else:
            request = f"{self.api_url}/status" 
        
        try:
            resposta = requests.get(request, timeout=2)
            if resposta.ok:
                status = bool(resposta.json().get("executando"))
                return status
        except Exception as e:
            print(f"[ERRO] Erro {e} na requisição")
            return False
            

