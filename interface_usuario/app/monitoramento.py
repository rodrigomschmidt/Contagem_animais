import requests
import Levenshtein
import time
from datetime import datetime
from utilitarios import registrar_resultado, copiar_para_rede

def leitura_placas(url_placas, dict_placa):
    try:
        for rampa in dict_placa.keys():
            resp_placa = requests.get(f"{url_placas}/placa/{rampa}", timeout=2)
            resp_estado = requests.get(f"{url_placas}/estado/{rampa}", timeout=2)

            #CHECAGEM PLACA
            if resp_placa.ok:
                resposta = resp_placa.json()
                dict_placa[rampa]["placa_lida"] = resposta["placa"]
                placa = dict_placa[rampa]["placa_lida"]
                print(f"PLACA {rampa} = {placa}")
            else:
                print(f"[ERRO] Código de resposta: {resp_placa.status_code}")

            #CHECAGEM ESTADO
            if resp_estado.ok:
                resposta = resp_estado.json()
                dict_placa[rampa]["estado"] = resposta["estado"]
                estado = dict_placa[rampa]["estado"]
                print(f"ESTADO {rampa} = {estado}")
            else:
                print(f"[ERRO] Código de resposta: {resp_estado.status_code}")
    except Exception as e:
        print(f"[ERRO] Falha ao consultar P1: {e}")
    
    return

def loop_placas(url_placas, dict_placa, dict_payload, tree_sem, popup):

        # enquanto a janela existir, roda o loop
        while True:
            for rampa in dict_placa.keys():
                dict_placa[rampa]["estado_anterior"] = dict_placa[rampa]["estado"]
                dict_placa[rampa]["placa_anterior"] = dict_placa[rampa]["placa_lida"]

            leitura_placas(url_placas, dict_placa)

            placa_atual = dict_placa[rampa]["placa_lida"]
            for rampa in dict_placa.keys():
                melhor_placa = None
                melhor_ordem = None
                if dict_placa[rampa]["estado_anterior"] == True:
                    if dict_placa[rampa]["estado"] == False: #ou seja, trocou de estado, pois o anterior era True e o novo é falso - Caminhão saindo da rampa
                        popup.after(0, lambda r=rampa: dict_placa[r]["placa_var"].set(""))
                        popup.after(0, lambda r=rampa: dict_placa[r]["ordem_var"].set(""))

                        dict_placa[rampa]["placa_lida"] = None

                        dict_payload[rampa]["placa"] = None
                        dict_payload[rampa]["sequencial"] = None
                        dict_payload[rampa]["ordem_entrada"] = None
                        dict_payload[rampa]["data_abate"] = None

                if dict_placa[rampa]["placa_anterior"] != dict_placa[rampa]["placa_lida"]: #OU SEJA, SE HOUVE TROCA DE PLACA
                    
                    menor_d = None

                    # Itera por todas as linhas (itens) da treeview
                    for item_id in tree_sem.get_children():
                        
                        valores = tree_sem.item(item_id, "values")
                        placa_ais = valores[1].replace("-", "").strip()
                        ordem_ais = valores[2].replace("-", "").strip()
                        data_abate = valores[0].replace("-", "").strip()

                        if dict_placa[rampa]["placa_lida"] == None or placa_ais == None:

                            print("[SIM] Um ou mais argumentos None")
                            continue
                        else:
                            d = Levenshtein.distance(placa_ais, dict_placa[rampa]["placa_lida"]) 
                            print(f"[SIM] Similaridade entre {placa_ais} e {placa_atual} é de {d}")

                        if menor_d is None: # Se menor_d for None, primeira iteração - atribuir os valores atuais. 
                            menor_d = d
                            melhor_placa = placa_ais
                            melhor_ordem = ordem_ais
                            
                        else: # menor_d existe, ou seja, não é a primeira iteração
                            if d < menor_d:
                                menor_d = d 
                                if placa_ais == melhor_placa:
                                    if int(ordem_ais) < int(melhor_ordem):

                                        melhor_placa = placa_ais
                                        melhor_ordem = ordem_ais
                                else:
                                    melhor_placa = placa_ais
                                    melhor_ordem = ordem_ais
                        
                        #print(f"Placa = {placa_ais} - Ordem = {ordem_ais}")

                if melhor_placa is not None:
                    popup.after(0, lambda r=rampa, p=melhor_placa: dict_placa[r]["placa_var"].set(p))
                    popup.after(0, lambda r=rampa, o=melhor_ordem: dict_placa[r]["ordem_var"].set(o))

                    dict_payload[rampa]["placa"] = melhor_placa
                    dict_payload[rampa]["sequencial"] = "1"
                    dict_payload[rampa]["ordem_entrada"] = melhor_ordem
                    dict_payload[rampa]["data_abate"] = data_abate


            time.sleep(1.5)


def loop_iniciar(url_clp, dict_payload, url, config, dict_sequenciais):
    estado_anterior = {"P1": False, "P5": False}
    
    while True:
        try:
            resp = requests.get(f"{url_clp}/estado_clp", timeout=2)
            if resp.ok:
                estado = resp.json()
                print(f"[DEBUG] O estado é = {estado}")

                for rampa in dict_payload.keys():
                    atual = estado.get(rampa, False)
                    anterior = estado_anterior[rampa]
                    payload = dict_payload[rampa]
                    
                    if atual and not anterior:
                        # Sinal subiu: iniciar contagem
                        if all([payload["placa"], payload["ordem_entrada"], payload["data_abate"], payload["sequencial"]]):
                            print(f"[INTERFACE] Disparando contagem para {rampa}: {payload}")
                            try:
                                r = requests.post(f"{url}/iniciar/{rampa}", json=payload, timeout=5)
                                if r.ok:
                                    print(f"[INTERFACE] Contagem iniciada com sucesso para {rampa}")
                                else:
                                    print(f"[INTERFACE] Erro ao iniciar contagem para {rampa}: {r.text}")
                            except Exception as e:
                                print(f"[INTERFACE] Falha ao iniciar contagem para {rampa}: {e}")
                        else:
                            print(f"[INTERFACE] Payload incompleto para {rampa}, contagem não iniciada.")

                    elif not atual and anterior:
                        # Sinal desceu: finalizar contagem
                        print(f"[INTERFACE] Finalizando contagem de {rampa}")
                        try:
                            r = requests.post(f"{url}/parar/{rampa}", timeout=5)
                            if r.ok:
                                print(f"[INTERFACE] Contagem finalizada para {rampa}")
                            else:
                                print(f"[INTERFACE] Erro ao finalizar contagem para {rampa}: {r.text}")
                        except Exception as e:
                            print(f"[INTERFACE] Falha ao finalizar contagem para {rampa}: {e}")
                            continue

                        # Aguarda finalização real via /status
                        try:
                            print(f"[INTERFACE] Aguardando finalização segura da contagem de {rampa}...")
                            while True:
                                status = requests.get(f"{url}/status/{rampa}", timeout=2)
                                if status.ok and not status.json().get("executando", True):
                                    print(f"[INTERFACE] Confirmado: contagem finalizada para {rampa}")
                                    break
                                time.sleep(0.5)
                        except Exception as e:
                            print(f"[INTERFACE] Erro ao aguardar /status de {rampa}: {e}")
                            continue

                        # Coleta e salva o resultado
                        try:
                            r_resultado = requests.get(f"{url}/resultado/{rampa}", timeout=5)
                            if r_resultado.ok:
                                contagem = int(r_resultado.json().get("contagem", 0))
                                hora = datetime.now().strftime("%H:%M:%S")
                                data = datetime.now().strftime("%d/%m/%Y")

                                registrar_resultado(
                                    data=data,
                                    placa=payload["placa"],
                                    sequencial=payload["sequencial"],
                                    quantidade=contagem,
                                    caminho_excel=config["caminho_excel"],
                                    hora=hora,
                                    ordem_compra=payload["ordem_entrada"]
                                )

                                copiar_para_rede(config["caminho_excel"], config["caminho_excel_rede"])

                                dict_sequenciais[rampa] = str(int(dict_sequenciais[rampa]) + 1)
                                dict_payload[rampa]["sequencial"] = dict_sequenciais[rampa]

                                print(f"[INTERFACE] Resultado registrado com sucesso para {rampa}")
                            else:
                                print(f"[INTERFACE] Erro ao obter resultado: {r_resultado.text}")
                        except Exception as e:
                            print(f"[INTERFACE] Erro ao consultar /resultado de {rampa}: {e}")

                    # Atualiza o estado anterior da rampa
                    estado_anterior[rampa] = atual

        except Exception as e:
            print(f"[INTERFACE] Erro geral no loop_iniciar: {e}")

        time.sleep(1.5)
