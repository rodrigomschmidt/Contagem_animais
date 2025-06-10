import cv2

class Camera():
    
    def __init__(self, url, id=None):
        """Passar id no construtor apenas em caso das cameras novas, onde a api é uma só"""
        self.id = id
        self.url = url
        self.cap = None

    def conectar(self):
        if self.cap is None or not self.cap.isOpened():
            self.cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
        return self.cap
    
    def ler_frame(self):
        
        if not self.cap.isOpened():
            print(f"Erro ao conectar à câmera {self.id}" )
            return None
        
        ret, frame = self.cap.read()

        if not ret:
            print("Erro ao ler o frame")
            return None
        
        return frame

    