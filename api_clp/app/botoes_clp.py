import time

def botoes(rampa, inicio_contagem, final_contagem, executando, deque_abertura, deque_fechamento, liberar_contagem):
        
    if all(deque_abertura[rampa]) and len(deque_abertura[rampa])== deque_abertura[rampa].maxlen and not executando[rampa]:
        print(f"[CLP] {rampa} pressionado por 2 segundos. Disparando contagem...")

        if time.time() - final_contagem[rampa] > 15:
            try:
                liberar_contagem[rampa] = True
                print("[CLP] Iniciar contagem")
                pass #apenas para tirar a msg de erro
            except Exception as e:
                print(f"[CLP] Erro na requisição /iniciar: {e}")

    elif all(deque_fechamento[rampa]) and len(deque_fechamento[rampa])== deque_fechamento[rampa].maxlen and executando[rampa]:
        
            if time.time() - inicio_contagem[rampa] > 10:
                try: 
                    liberar_contagem[rampa] = False 
                    print("[CLP] Finalizar contagem")
                except Exception as e:
                    print(f"[CLP] Erro na requisição /parar: {e}")

    return inicio_contagem, final_contagem 