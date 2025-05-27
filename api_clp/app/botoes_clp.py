import time

def botoes(rampa, inicio_contagem, final_contagem, executando, deque_abertura, deque_fechamento, liberar_contagem):
        
    if all(deque_abertura) and len(deque_abertura)== deque_abertura.maxlen and not executando:
        print(f"[CLP] {rampa} pressionado por 2 segundos. Disparando contagem...")

        if time.time() - final_contagem > 15:
            try:
                liberar_contagem[rampa] = True
                print("[CLP] Iniciar contagem")
                pass #apenas para tirar a msg de erro
            except Exception as e:
                print(f"[CLP] Erro na requisição /iniciar: {e}")

    elif all(deque_fechamento) and len(deque_fechamento)== deque_fechamento.maxlen and executando:
        
            if time.time() - inicio_contagem > 10:
                try: 
                    liberar_contagem[rampa] = False 
                    print("[CLP] Finalizar contagem")
                except Exception as e:
                    print(f"[CLP] Erro na requisição /parar: {e}")

    return inicio_contagem, final_contagem, 