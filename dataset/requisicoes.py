import requests
import time
from threading import Thread

class Requisicao():
    def __init__(self, u):
        self.api_url = u
        self.status = False
        self.status_anterior = False


    def att_status_ant(self, status):
        self.status_anterior = status
        return
    
    def get_status_ant(self):
        return self.status_anterior
    
    def get_status(self):
        return self.status
    
    def consultar_execucao(self, camera):
        time.sleep(0.5)
        if camera.id is not None:
            request = f"{self.api_url}/status/{camera.id}"
        else:
            request = f"{self.api_url}/status" 
        
        try:
            resposta = requests.get(request, timeout=2)
            if resposta.ok:
                self.status = bool(resposta.json().get("executando"))
                print(f"O status é {self.status}")
                
        except Exception as e:
            print(f"[ERRO] Erro {e} na requisição")
            return False
            

