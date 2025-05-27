import requests
import Levenshtein
import time

def leitura_placas(dict_url, dict_placa):
    try:
        for rampa in dict_url.keys():
            resp_placa = requests.get(f"{dict_url[rampa]}/placa", timeout=2)
            resp_estado = requests.get(f"{dict_url[rampa]}/estado", timeout=2)

            #CHECAGEM PLACA
            if resp_placa.ok:
                dict_placa[rampa]["placa_lida"] = resp_placa.json()
                print(f"PLACA {rampa} = {resp_placa.json()}")
            else:
                print(f"[ERRO] Código de resposta: {resp_placa.status_code}")

            #CHECAGEM ESTADO
            if resp_estado.ok:
                dict_placa[rampa]["estado"] = resp_estado.json()
                print(f"ESTADO {rampa} = {resp_estado.json()}")
            else:
                print(f"[ERRO] Código de resposta: {resp_estado.status_code}")
    except Exception as e:
        print(f"[ERRO] Falha ao consultar P1: {e}")
    
    return

def loop_placas(dict_url, dict_placa, dict_payload, tree_sem, popup):

        # enquanto a janela existir, roda o loop
        while True:
            for rampa in dict_placa.keys():
                dict_placa[rampa]["estado_anterior"] = dict_placa[rampa]["estado"]
                dict_placa[rampa]["placa_anterior"] = dict_placa[rampa]["placa_lida"]

            leitura_placas(dict_url, dict_placa)

            placa_atual = dict_placa[rampa]["placa_lida"]
            for rampa in dict_placa.keys():
                melhor_placa = None
                melhor_ordem = None
                if dict_placa[rampa]["estado_anterior"] == True:
                    if dict_placa[rampa]["estado"] == False: #ou seja, trocou de estado, pois o anterior era True e o novo é falso - Caminhão saindo da rampa
                        popup.after(0, lambda r=rampa, p=melhor_placa: dict_placa[r]["placa_var"].set(""))
                        popup.after(0, lambda r=rampa, o=melhor_ordem: dict_placa[r]["ordem_var"].set(""))

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


            time.sleep(0.5)
