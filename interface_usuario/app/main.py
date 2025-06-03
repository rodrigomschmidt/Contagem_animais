import tkinter as tk
from tkinter import messagebox
import threading
from interface  import iniciar_interface
from utilitarios import load_config
import requests
from datetime import datetime
import time
from monitoramento import loop_placas, loop_iniciar

config = load_config("config/config.txt")

url_placas = None

dict_placa = {"P1": {"placa_lida": None, "placa_anterior": None, "estado": None, "estado_anterior": None, "ordem_var": None, "placa_var": None},
              "P5": {"placa_lida": None, "placa_anterior": None, "estado": None, "estado_anterior": None, "ordem_var": None, "placa_var": None}}

dict_payload = { "P1": {
    "caminho_output_base": r"C:\teste_base",
    "caminho_output_rede": r"\\srvbmflserver\BARRAMANSA\PUBLICO_BM\Rodrigo\Videos_novo",
    "placa": None,
    "sequencial": None,
    "ordem_entrada": None,
    "data_abate": None,
    "rampa": "P1"  # ou "P5"
    },
    "P5": {
    "caminho_output_base": r"C:\teste_base",
    "caminho_output_rede": r"\\srvbmflserver\BARRAMANSA\PUBLICO_BM\Rodrigo\Videos_novo",
    "placa": None,
    "sequencial": None,
    "ordem_entrada": None,
    "data_abate": None,
    "rampa": "P5"  # ou "P5"
    },
}

dict_sequenciais = {"P1": "1",
                    "P5": "1"}

def aguardar_fim_da_contagem(API_URL):
    # Aguarda até que o status da API retorne que não está mais executando
    while True:
        try:
            status = requests.get(f"{API_URL}/status").json()
            if not status.get("executando", False):
                break
        except:
            break
        time.sleep(1)

def main():
    caminho_excel = config["caminho_excel"]
    caminho_excel_rede = config["caminho_excel_rede"]
    url_clp = config["URL_CLP"]
    root = tk.Tk()
    root.withdraw()

    url_placas = config[f"API_URL_PLACAS"]
    url_contagem = config[f"API_URL_CONTAGEM"]

    # Preenche rampa nos payloads
    for rampa in dict_placa.keys():
        dict_payload[rampa]["rampa"] = rampa


    tree_sem, tree_com, popup = iniciar_interface(root, caminho_excel, dict_placa)
    
    t1 = threading.Thread(target=loop_placas, args=(url_placas, dict_placa, dict_payload, tree_sem, popup,), daemon=True)
    t1.start()

    t2 = threading.Thread(target=loop_iniciar, args=(url_clp, dict_payload, url_contagem, config, dict_sequenciais,), daemon=True)
    t2.start()
    #registrar_resultado(data_abate, placa, sequencial, contagem, caminho_excel, hora, ordem)
    #copiar_para_rede(caminho_excel, caminho_excel_rede)

    root.mainloop()
    #sequencial = str(int(sequencial) + 1)

if __name__ == "__main__":
    main()
