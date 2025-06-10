import cv2

class Camera():
    
    def __init__(self, url, id=None):
        """Passar id no construtor apenas em caso das cameras novas, onde a api é uma só"""
        self.id = id
        self.url = url
        self.cap = None

    def conectar(self):
        
        if self.cap is None or not self.cap.isOpened():
            print(f"[CAMERA] TENTANDO CONECTAR À CAMERA {self.id if self.id else self.url}")
            self.cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
            if self.cap.isOpened():
                print(f"[CAMERA] CONTECTADO À CAMERA {self.id if self.id else self.url}")
                return True
            else:
                print(f"[CAMERA] FALHA AO CONECTAR À CAMERA {self.id if self.id else self.url}")
                return False
        return True
    
    def check_stream(self):
        return self.cap.isOpened()

    def ler_frame(self):

        if not self.cap.isOpened():
            print(f"[CAMERA] FALHA AO CONECTAR À CAMERA {self.id if self.id else self.url}" )
            return None

        ret, frame = self.cap.read()

        if not ret:
            print("Erro ao ler o frame")
            return None
        
        return frame

    