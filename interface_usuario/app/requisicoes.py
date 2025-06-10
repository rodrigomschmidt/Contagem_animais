import requests
import time

def get_resultado(api_url, camera_id, tentativas=1, intervalo=1):
    for i in range(tentativas):
        try:
            resposta = requests.get(f"{api_url}/resultado/{camera_id}", timeout=2)
            if resposta.ok:
                contagem = int(resposta.json().get("contagem"))
                return contagem
        except Exception as e:
            print(f"Tentativa {i+1}/{tentativas} - stream não pronto: {e}")
        time.sleep(intervalo)
    return False

def get_executando(api_url, camera_id, tentativas=1, intervalo=1):
    for i in range(tentativas):
        try:
            resposta = requests.get(f"{api_url}/status/{camera_id}", timeout=2)
            if resposta.ok:
                status = bool(resposta.json().get("executando"))
                return status
        except Exception as e:
            print(f"Tentativa {i+1}/{tentativas} - stream não pronto: {e}")
        time.sleep(intervalo)
    return False

