from collections import deque
from utilitarios import load_config
from pymodbus.client import ModbusTcpClient
from botoes_clp import botoes
import time
import requests

payload_em_espera = {}
monitorando_clp = True
config = load_config("config_clp.txt")
API_URL_CONTAGEM = config["API_URL"]
api_urls = {"P1": config["API_URL_P1"], "P5": config["API_URL_P5"]}
executando = {}

def verificar_executando(url):
    try:
        resp = requests.get((f"{url}/status"), timeout=2)
        if resp.status_code == 200:
            return resp.json().get("executando", False)
    except Exception as e:
        print(f"[CLP] Erro ao consultar status de execução: {e}")
    return False

def escutar_clp():
    global payload_em_espera, executando

    deque_abertura = {"P1": deque(maxlen=5), "P5": deque(maxlen=5)}
    deque_fechamento = {"P1": deque(maxlen=5), "P5": deque(maxlen=5)}
    
    CLP_IP = '10.1.3.220'  # ✅ Ajuste se necessário
    PORTA = 502
    UNIT_ID = 1
    ENDERECO_INICIAL = 16882
    INTERVALO_LEITURA = 0.4  # segundos

    payload_p1 = {
    "caminho_output_base": "C:/teste_base",
    "caminho_output_rede": "C:/teste_rede",
    "placa": "TESTE123",
    "sequencial": "1",
    "ordem_entrada": "0000",
    "data_abate": "29/04/2025",
    "ip": config["ip_p1"],  # ou config["ip_p5"] dependendo do botão
    "rampa": "P1"  # ou "P5"
    }

    payload_p5 = {
        "caminho_output_base": "C:/teste_base",
        "caminho_output_rede": "C:/teste_rede",
        "placa": "TESTE123",
        "sequencial": "1",
        "ordem_entrada": "0000",
        "data_abate": "29/04/2025",
        "ip": config["ip_p5"],  # ou config["ip_p5"] dependendo do botão
        "rampa": "P5"  # ou "P5"
    }

    #bloqueio = {"P1": False, "P5": False}
    fechando = {"P1": None, "P5": None}
    abrindo = {"P1": None, "P5": None}
    inicio_contagem = {"P1": 0, "P5": 0}
    final_contagem = {"P1": 0, "P5": 0}

    client = ModbusTcpClient(CLP_IP, port=PORTA)

    if not client.connect():
        print("[CLP] Falha ao conectar no CLP")
        return

    print("[CLP] Conectado com sucesso.")

    try:
        while monitorando_clp:
            for rampa in api_urls.keys():
                executando[rampa] = verificar_executando(api_urls[rampa])

            resposta = client.read_coils(address=ENDERECO_INICIAL, count=20, slave=UNIT_ID)
            payload_em_espera["P1"] = payload_p1
            payload_em_espera["P5"]  = payload_p5
            if not resposta.isError():
                
                estados = resposta.bits
                if len(estados) >= 20:
                    abrindo["P1"] = estados[0]
                    fechando["P1"] = estados[1]
                    abrindo["P5"] = estados[16]
                    fechando["P5"] = estados[17]

                    print(f"[CLP] Abrindo: P1={abrindo['P1']}, P5={abrindo['P5']}")
                    print(f"[CLP] Fechando: P1={fechando['P1']}, P5={fechando['P5']}")


                    for rampa in api_urls.keys():
                        deque_abertura[rampa].append(abrindo[rampa])
                        deque_fechamento[rampa].append(fechando[rampa])
                        print(f"[CONTAGEM] Executando {rampa} = {executando[rampa]}")
                        print(f"[CLP] Deque Fechamento {rampa} : {deque_fechamento[rampa]}")
                        print(f"[CLP] Deque Abertura {rampa} : {deque_abertura[rampa]}")
                        inicio_contagem[rampa], final_contagem[rampa], payload_em_espera[rampa] = botoes(api_urls[rampa], rampa, inicio_contagem[rampa], final_contagem[rampa], executando[rampa], payload_em_espera[rampa], deque_abertura[rampa], deque_fechamento[rampa])
                        #print(f"A Deque_monit{rampa} logo após botoes é de: {deque_monit[rampa]}")
                        #inicio_contagem, payload_em_espera_p5= botoes(API_URL, "P5", inicio_contagem, executando, payload_em_espera_p5, deque_monit, deque_solto)

                else:
                    print("[CLP] Resposta de botões incompleta.")
            else:
                print("[CLP] Falha na leitura dos botões.")

            time.sleep(INTERVALO_LEITURA)

    except Exception as e:
        print(f"[CLP] Erro inesperado: {e}")

    finally:
        client.close()
        print("[CLP] Conexão com CLP encerrada.")