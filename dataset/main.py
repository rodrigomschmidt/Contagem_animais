from controlador import Controlador

p5 = Controlador(
    r"rtsp://admin:czcz8910@192.168.42.48/Streaming/Channels/101?transport=tcp",
    r"\\srvbmflserver\BARRAMANSA\PUBLICO_BM\Rodrigo\Videos_col",
    "http://10.1.3.93:8000",
    70,
)

if __name__ == "__main__":
    
    p5.iniciar_monitoramentos()

    

        

      