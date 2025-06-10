import cv2
import time
import os

class Video():
    def __init__(self, dir, w=640, h=512):
        self.dir = dir
        self.path = None
        self.writer = None
        self.fps = 10
        self.width = w
        self.height = h
        self.nome = None
        
        try:
            os.makedirs(self.dir, exist_ok=True)
        except OSError as e:
            print(f"Erro: Não foi possível criar o diretório de vídeos '{self.dir}'. Verifique as permissões. Erro: {e}")

    def atualizar_nome(self):
        self.nome = time.strftime("%Y%m%d-%H%M%S")
        return self.nome

    def gerar_writer(self):
        self.atualizar_nome()
        if self.dir is not None:
            self.path = f"{self.dir}/{self.nome}.mp4"
            self.writer = cv2.VideoWriter(self.path, cv2.VideoWriter_fourcc(*"mp4v"), self.fps, (self.width, self.height))
            return self.writer
        else: return None
        
    def liberar_writer(self):
        if self.writer is not None and self.writer.isOpened():
            self.writer.release()
        else:
            print("Aviso: Tentativa de liberar um VideoWriter não inicializado ou já liberado.")
    
    def gravar_video(self, frame):
        if self.writer is not None and self.writer.isOpened():
            self.writer.write(frame)
        else:
            print("Erro: Tentativa de gravar frame em um VideoWriter não inicializado ou fechado. O frame não foi gravado.")


