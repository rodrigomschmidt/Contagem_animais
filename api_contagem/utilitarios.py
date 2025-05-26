import os
import requests
from requests.auth import HTTPDigestAuth
import shutil

def trigger_manual_correction(ip):

    # Configurações do dispositivo
    url = f"http://{ip}/ISAPI/Image/channels/2/ManualShutterCorrect"
    username = "admin"  # Substitua pelo seu nome de usuário
    password = "czcz8910"  # Substitua pela sua senha

    try:
        # Fazendo a requisição PUT com autenticação Digest
        response = requests.put(
            url,
            auth=HTTPDigestAuth(username, password),
            timeout=10  # Timeout de 10 segundos
        )

        # Verificando o status da resposta
        if response.status_code == 200:
            print("Correção manual disparada com sucesso!")
            print("Resposta:", response.text)  # Exibe o corpo da resposta (pode ser um JSON)
        else:
            print(f"Falha ao disparar a correção manual. Status Code: {response.status_code}")
            print("Resposta:", response.text)

    except requests.exceptions.RequestException as e:
        print(f"Erro ao fazer a requisição: {e}")

def copiar_para_rede(caminho_local, caminho_rede):
    try:
        if not os.path.exists(caminho_rede):
            os.makedirs(caminho_rede)  # Cria o diretório de rede se não existir
        
        arquivo_nome = os.path.basename(caminho_local)
        destino = os.path.join(caminho_rede, arquivo_nome)
        
        shutil.copy2(caminho_local, destino)
        print(f"Arquivo copiado para {destino}")
    
    except Exception as e:
        print(f"Erro ao copiar arquivo para a rede: {e}")


def load_config(config_file):
    """
    Carrega os pares chave=valor de um arquivo de configuração.

    Args:
        config_file (str): Caminho do arquivo.

    Returns:
        dict: Dicionário com as chaves e valores do arquivo.

    Raises:
        FileNotFoundError: Se o arquivo não for encontrado.
        Exception: Para outros erros de leitura.
    """
    config = {}
    try:
        with open(config_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
        return config

    except FileNotFoundError:
        print(f"Erro: arquivo de configuração não encontrado em {config_file}")
        raise
    except Exception as e:
        print(f"Erro ao carregar configuração: {e}")
        raise

def crop_para_5x4(frame, crop_config):
    
    h, w = frame.shape[:2]
    top = crop_config["top"]
    bottom = h - crop_config["bottom"]
    frame_cortado = frame[top:bottom, :]

    nova_altura = frame_cortado.shape[0]
    nova_largura = int(nova_altura * 5 / 4)
    largura_atual = frame_cortado.shape[1]

    if nova_largura > largura_atual:
        raise ValueError("Largura insuficiente para 5:4 após crop vertical.")

    inicio_x = (largura_atual - nova_largura) // 2
    fim_x = inicio_x + nova_largura

    return frame_cortado[:, inicio_x:fim_x]