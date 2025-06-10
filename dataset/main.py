from camera import Camera
from video import Video
from requisicoes import Requisicao

p1 = Camera(r"rtsp://admin:czcz8910@192.168.42.49/Streaming/Channels/201?transport=tcp", "P1")
video = Video(r"\\srvbmflserver\BARRAMANSA\PUBLICO_BM\Rodrigo\Videos_col")
req = Requisicao("http://10.1.2.23:8000")

if __name__ == "__main__":
    
    while True:
        status_anterior = req.get_status_ant()
        status = req.consultar_execucao(p1)

        if status == True and status_anterior == False: #inicialização, anteriormente estava falso e trocou para true
            p1.conectar()
            video.gerar_writer()
        elif status == False and status_anterior == True: #finalização, anteriormente estava true e trocou para false
            video.liberar_writer()

        if status == True:
            frame = p1.ler_frame()
            if frame is None or frame.size == 0:
                continue
            video.gravar_video(frame)

        req.att_status_ant(status)

        

      