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

