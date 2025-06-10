import cv2
from camera import Camera
from video import Video
from requisicoes import Requisicao
p = Camera(r"rtsp://admin:czcz8910@192.168.42.49/Streaming/Channels/101?transport=tcp")
video = Video(r"\\srvbmflserver\BARRAMANSA\PUBLICO_BM\Rodrigo\Videos_col", 0, 70)
req = Requisicao("http://10.1.3.93:8000")

p.conectar()
video.gerar_writer()

while True:

    frame = p.ler_frame()
    frame_cropado = video.crop_para_5x4(frame)
    frame_red = cv2.resize(frame_cropado, (video.width, video.height))
    cv2.imshow("FRAMES", frame_red)
    video.gravar_video(frame_red)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        video.liberar_writer()
        break