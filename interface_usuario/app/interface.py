from datetime import datetime, timedelta
import tkinter as tk
from tkinter import messagebox, ttk
import requests
from utilitarios import consultar_placas, consultar_resultados_excel, load_config
#import cv2
import time
import threading
#import numpy as np
from screeninfo import get_monitors
import Levenshtein

config = load_config("config/config.txt")

dict_url = {"P1": "http://10.1.2.23:8011", "P5": "http://10.1.3.93:8015"}

dict_placa = {"P1": {"placa_lida": None, "placa_anterior": None, "estado": None, "estado_anterior": None, "ordem_var": None, "placa_var": None},
              "P5": {"placa_lida": None, "placa_anterior": None, "estado": None, "estado_anterior": None, "ordem_var": None, "placa_var": None}}


def aguardar_stream_pronto(api_url, tentativas=30, intervalo=1):
    for i in range(tentativas):
        try:
            resposta = requests.get(f"{api_url}/stream_pronto", timeout=2)
            if resposta.ok and resposta.json().get("pronto"):
                return True
        except Exception as e:
            print(f"Tentativa {i+1}/{tentativas} - stream não pronto: {e}")
        time.sleep(intervalo)
    return False

def leitura_placas(dict_url):
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

def solicitar_input(caminho_excel, contagem, placa, ordem_entrada, novo_sequencial, data_abate, rampa):
    resultados = {
        "placa": placa,
        "ordem": ordem_entrada,
        "sequencial": novo_sequencial,
        "data_abate": data_abate,
        "rampa": rampa
    }

    root = tk.Tk()
    root.withdraw()
    popup = tk.Toplevel(root)
    popup.title("Contador")
    popup.lift()
    popup.focus_force()

    def loop():

        
        # enquanto a janela existir, roda o loop
        while True:
            for rampa in dict_placa.keys():
                dict_placa[rampa]["estado_anterior"] = dict_placa[rampa]["estado"]
                dict_placa[rampa]["placa_anterior"] = dict_placa[rampa]["placa_lida"]

            leitura_placas(dict_url)

            placa_atual = dict_placa[rampa]["placa_lida"]
            for rampa in dict_placa.keys():
                melhor_placa = None
                melhor_ordem = None
                if dict_placa[rampa]["estado_anterior"] == True:
                    if dict_placa[rampa]["estado"] == False: #ou seja, trocou de estado, pois o anterior era True e o novo é falso - Caminhão saindo da rampa
                        dict_placa[rampa]["placa_lida"] = None

                if dict_placa[rampa]["placa_anterior"] != dict_placa[rampa]["placa_lida"]: #OU SEJA, SE HOUVE TROCA DE PLACA
                    
                    menor_d = None

                    # Itera por todas as linhas (itens) da treeview
                    for item_id in tree_sem.get_children():
                        
                        valores = tree_sem.item(item_id, "values")
                        placa_ais = valores[1].replace("-", "").strip()
                        ordem_ais = valores[2].replace("-", "").strip()

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

            time.sleep(1)

    # posicionamento no monitor
    largura, altura = 1080, 680
    num_monitor = int(config["monitor"])
    monitores = get_monitors()
    monitor_destino = monitores[num_monitor] if len(monitores) >= 2 else monitores[0]
    x = monitor_destino.x + (monitor_destino.width - largura) // 2
    y = monitor_destino.y + (monitor_destino.height - altura) // 2
    popup.geometry(f"{largura}x{altura}+{x}+{y}")

    fonte = ("Arial", 16)

    hoje = datetime.now().strftime("%d/%m/%Y")
    amanha = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
    if data_abate is None:
        data_abate = amanha

    def converter_data(data):
        try:
            return datetime.strptime(data, "%d/%m/%Y").strftime("%Y-%m-%d")
        except:
            return None

    # ——————————
    # FRAME ESQUEDO - PLACAS/ORDENS
    frame_esquerda = tk.Frame(popup)
    frame_esquerda.pack(side=tk.LEFT, padx=10, pady=10)

    # ESQUERDA CIMA (P1)
    frame_p1 = tk.LabelFrame(frame_esquerda, text="Rampa P1", font=fonte)
    frame_p1.pack(side=tk.TOP, fill=tk.X, padx=5, pady=(0,10))
    tk.Label(frame_p1, text="Placa P1:", font=fonte).pack(anchor="w", padx=5, pady=2)
    dict_placa["P1"]["placa_var"] = tk.StringVar()
    tk.Entry(frame_p1, textvariable=dict_placa["P1"]["placa_var"], font=fonte, state="readonly").pack(fill=tk.X, padx=5, pady=2)
    tk.Label(frame_p1, text="Ordem P1:", font=fonte).pack(anchor="w", padx=5, pady=2)
    dict_placa["P1"]["ordem_var"] = tk.StringVar()
    tk.Entry(frame_p1, textvariable=dict_placa["P1"]["ordem_var"], font=fonte, state="readonly").pack(fill=tk.X, padx=5, pady=2)

    # DIREITA BAIXO (P5)
    frame_p5 = tk.LabelFrame(frame_esquerda, text="Rampa P5", font=fonte)
    frame_p5.pack(side=tk.TOP, fill=tk.X, padx=5, pady=(10,0))
    tk.Label(frame_p5, text="Placa P5:", font=fonte).pack(anchor="w", padx=5, pady=2)
    dict_placa["P5"]["placa_var"] = tk.StringVar()
    tk.Entry(frame_p5, textvariable=dict_placa["P5"]["placa_var"], font=fonte, state="readonly").pack(fill=tk.X, padx=5, pady=2)
    tk.Label(frame_p5, text="Ordem P5:", font=fonte).pack(anchor="w", padx=5, pady=2)
    dict_placa["P5"]["ordem_var"] = tk.StringVar()
    tk.Entry(frame_p5, textvariable=dict_placa["P5"]["ordem_var"], font=fonte, state="readonly").pack(fill=tk.X, padx=5, pady=2)

    # BOTÕES CONFIRMAR E CANCELAR
    frame_botoes = tk.Frame(frame_esquerda)
    frame_botoes.pack(side=tk.TOP, fill=tk.X, padx=5, pady=10)
    tk.Button(frame_botoes, text="Confirmar", command=lambda: confirmar(), bg="green", font=fonte, fg="white")\
        .pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0,5))
    tk.Button(frame_botoes, text="Cancelar", command=lambda: cancelar(), bg="red", font=fonte, fg="white")\
        .pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(5,0))

    
    # FRAME DIREITO - TABELAS
    frame_direita = tk.Frame(popup)
    frame_direita.pack(side=tk.RIGHT, padx=10, pady=10)

    # TABELA 1 - PLACAS NÃO RECEBIDAS
    tk.Label(frame_direita, font=fonte, text="Placas sem Retorno").pack(pady=5)
    tree_sem = ttk.Treeview(
        frame_direita,
        columns=("Data","Placa","Ordem","GTA","Quantidade","Rampa","Fornecedor","Fazenda","Municipio"),
        show="headings", height=10
    )
    for col in tree_sem["columns"]:
        tree_sem.heading(col, text=col.upper())
        tree_sem.column(col, width=100 if col=="Fornecedor" else 80)
    tree_sem.pack()

    

    # TABELA 2 - PLACAS RECEBIDAS
    tk.Label(frame_direita, font=fonte, text="Placas com Retorno").pack(pady=5)
    tree_com = ttk.Treeview(
        frame_direita,
        columns=("Data","Placa","Ordem","GTA","Quantidade","Rampa","Fornecedor","Fazenda","Municipio"),
        show="headings", height=10
    )
    for col in tree_com["columns"]:
        tree_com.heading(col, text=col.upper())
        tree_com.column(col, width=100 if col=="Fornecedor" else 80)
    tree_com.pack()

    def duplo_click_tabela(event):
        print("Consultando")
        sel = tree_com.selection()
        if not sel:
            return
        valores = tree_com.item(sel, "values")
        # assumindo ordem das colunas: (Data, Placa, Ordem, GTA, Quant, Rampa, Forn, Faz, Mun)
        placa_selecionada = valores[1]
        ordem_selecionada = valores[2]

        # limpa a tabela de contagens
        tree2.delete(*tree2.get_children())

        # faz a consulta no Excel
        resultados_excel = consultar_resultados_excel(caminho_excel,
                                                     placa_selecionada,
                                                     ordem_selecionada)
        # preenche tree2
        for row in resultados_excel:
            hora, placa, ordem, seq, qtd, *_ = row
            tree2.insert("", "end", values=(hora, placa, ordem, seq, qtd))

    tree_com.bind("<Double-1>", duplo_click_tabela)

    # TABELA DE HISTÓRICO DE CONTAGEM
    tk.Label(frame_direita, font=fonte, text="Contagens por Placa").pack(pady=5)
    tree2 = ttk.Treeview(
        frame_direita,
        columns=("Hora","Placa","Ordem","Desembarque","Quantidade"),
        show="headings", height=4
    )
    for col in tree2["columns"]:
        tree2.heading(col, text=col.upper())
        tree2.column(col, width=140)
    tree2.pack()

    # ATUALIZAÇÃO DAS TABELAS 1 E 2
    def atualizar_tabelas():
        tree_sem.delete(*tree_sem.get_children())
        tree_com.delete(*tree_com.get_children())

        for data_str in (hoje, amanha):
            data_iso = converter_data(data_str)
            placas = consultar_placas(data_iso)
            for _, placa_txt, ordem_txt, gta, quant, forn, faz, mun, rampa_txt in placas:
                vals = (
                    data_str,
                    placa_txt,
                    ordem_txt,
                    gta,
                    quant,
                    rampa_txt,
                    forn,
                    faz,
                    mun
                )
                if not rampa_txt:
                    tree_sem.insert("", "end", values=vals)
                else:
                    tree_com.insert("", "end", values=vals)

        popup.after(30_000, atualizar_tabelas)

        # [opcional] atualizar tree2 de contagens aqui, se necessário

    atualizar_tabelas()

    t = threading.Thread(target=loop, daemon=True)
    t.start()
    
    

    # funções de confirmação e cancelamento (sem alterações)
    def confirmar():
        # implementar disparo com placas de P1/P5
        pass

    def cancelar():
        resultados["placa"] = None
        popup.destroy()
        root.destroy()

    root.mainloop()

    if resultados["placa"] is None:
        return None

    return (
        resultados["placa"],
        resultados["ordem"],
        resultados["sequencial"],
        resultados["data_abate"],
        resultados["rampa"]
    )
