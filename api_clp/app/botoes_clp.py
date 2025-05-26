import requests
import time

def botoes(API_URL, rampa, inicio_contagem, final_contagem, executando, payload, deque_abertura, deque_fechamento):
        
    if all(deque_abertura) and len(deque_abertura)== deque_abertura.maxlen and payload and not executando:
        print(f"[CLP] {rampa} pressionado por 2 segundos. Disparando contagem...")

        if time.time() - final_contagem > 15:
            try:
                resp = requests.post(f"{API_URL}/iniciar", json=payload)
                if resp.status_code == 200:
                    inicio_contagem = time.time()
                    print(f"[CLP] Contagem {rampa} iniciada com sucesso.")
                    deque_abertura.clear()
                else:
                    print(f"[CLP] Erro ao iniciar contagem: {resp.text}")
            except Exception as e:
                print(f"[CLP] Erro na requisição /iniciar: {e}")

    elif all(deque_fechamento) and len(deque_fechamento)== deque_fechamento.maxlen and executando:
        try:
            if time.time() - inicio_contagem > 10:
                print(f"[CLP] {rampa} pressionado por 2 segundos. Fechando contagem...")
                resp = requests.post(f"{API_URL}/parar")
                if resp.status_code == 200:
                    final_contagem = time.time()
                    print("[CLP] Contagem finalizada com sucesso.")
                    deque_fechamento.clear()
                    #print(f"Deque é dentro de BOTOES é de = {deque_monit} ")
                else:
                    print(f"[CLP] Erro ao finalizar contagem: {resp.text}")
        except Exception as e:
            print(f"[CLP] Erro na requisição /parar: {e}")

    return inicio_contagem, final_contagem, payload