from pymodbus.client import ModbusTcpClient
import time


CLP_IP = '10.1.3.220'   # ajuste se necessário
PORTA = 502
UNIT_ID = 1
ENDERECO_INICIAL = 16882
NUM_BITS = 85
INTERVALO_LEITURA = 0.1  # segundos


def monitorar_clp_alteracoes():
    client = ModbusTcpClient(CLP_IP, port=PORTA)

    if not client.connect():
        print("[CLP] Falha ao conectar no CLP")
        return

    print("[CLP] Conectado com sucesso. Monitorando alterações...")

    ultimo_estado = [None] * NUM_BITS

    try:
        while True:
            resposta = client.read_coils(address=ENDERECO_INICIAL, count=NUM_BITS, slave=UNIT_ID)

            if not resposta.isError():
                estados = resposta.bits

                for i in range(min(len(estados), NUM_BITS)):
                    if ultimo_estado[i] is None:
                        ultimo_estado[i] = estados[i]
                    elif estados[i] != ultimo_estado[i]:
                        print(f"[CLP] Bit {ENDERECO_INICIAL + i+ 1} alterado para {estados[i]}")
                        ultimo_estado[i] = estados[i]

            else:
                print("[CLP] Erro na leitura do CLP.")

            time.sleep(INTERVALO_LEITURA)

    except Exception as e:
        print(f"[CLP] Erro inesperado: {e}")

    finally:
        client.close()
        print("[CLP] Conexão com CLP encerrada.")


if __name__ == "__main__":
    monitorar_clp_alteracoes()
