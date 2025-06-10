from camera import Camera
from requisicoes import Requisicao
from video import Video
import cv2
from threading import Thread

class Controlador():
    def __init__(self, url_cam, dir_video, url_api, crop_top = 0, crop_bot = 0, w=640, h=512, id=None):
        self.camera = Camera(url_cam, id)
        self.req = Requisicao(url_api)
        self.video = Video(dir_video, crop_top, crop_bot, w, h)

    def monitorar_cam(self):
        while True:

            status_anterior = self.req.get_status_ant()
            status = self.req.get_status()

            if status == True and status_anterior == False: #inicialização, anteriormente estava falso e trocou para true
                print("INICIANDO CONEXÃO")
                self.camera.conectar()
                self.video.gerar_writer()
            elif status == False and status_anterior == True: #finalização, anteriormente estava true e trocou para false
                self.video.liberar_writer()

            if status == True:
                if self.camera.check_stream() is True:
                    frame = self.camera.ler_frame()
                    frame_cropado = self.video.crop_para_5x4(frame)
                    frame_redimensionado = cv2.resize(frame_cropado, (self.video.width, self.video.height))
                    self.video.gravar_video(frame_redimensionado)
                else:
                    self.camera.conectar()

            self.req.att_status_ant(status)

    def monitorar_status(self):
        while True:
            self.req.consultar_execucao(self.camera)

    def iniciar_monitoramentos(self):
        print("INICIANDO THREAD DE MONITORAMENTO DE STATUS")
        Thread(target=self.monitorar_status, daemon=True).start()
        Thread(target=self.monitorar_cam, daemon=False).start()
        

