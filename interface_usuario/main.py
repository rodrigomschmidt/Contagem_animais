import tkinter as tk
from tkinter import messagebox
from interface  import solicitar_input
from utilitarios import load_config, registrar_resultado, copiar_para_rede
import requests
from datetime import datetime
import time

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
    config = load_config("config/config.txt")
    caminho_excel = config["caminho_excel"]
    caminho_excel_rede = config["caminho_excel_rede"]

    placa = ""
    ordem = ""
    rampa = ""
    sequencial = 1
    data_abate = None
    contagem = 0

    while True:
        resultados = solicitar_input(caminho_excel, contagem, placa, ordem, sequencial, data_abate, rampa)
        if resultados is None:
            break

        placa, ordem, sequencial, data_abate, rampa = resultados

        if rampa == "P1":
            API_URL = config["API_URL_P1"]
        elif rampa == "P5":
            API_URL = config["API_URL_P5"]

        hora = datetime.now().strftime("%H:%M:%S")

        print("Aguardando finalização da contagem...")
        aguardar_fim_da_contagem(API_URL)
        print("Contagem encerrada!")

        try:
            r = requests.get(f"{API_URL}/resultado")
            contagem = int(r.json().get("contagem", 0))
            print(f"A contagem foi de {contagem}")          

        except Exception as e:
            print(f"Erro ao obter contagem: {e}")
            contagem = 0

        registrar_resultado(data_abate, placa, sequencial, contagem, caminho_excel, hora, ordem)
        copiar_para_rede(caminho_excel, caminho_excel_rede)

        sequencial = str(int(sequencial) + 1)

if __name__ == "__main__":
    main()
