import cv2
import os
from utilitarios import trigger_manual_correction, copiar_para_rede, load_config, crop_para_5x4, converter_data
import torch
from states import yolo_lock, estados_cameras
import gc
import time

config = load_config("config\config_contagem.txt")

crop_configs = {
        "P1": {"top": 0, "bottom": 70},
        "P5": {"top": 70, "bottom": 0},
    }

def contagem(camera_id, modelo, url):
    
    executando_anterior = False
    
    w = int(config["w"])
    h = int(config["h"])

    LINE_1 = 420
    LINE_2 = 460
    LIMITE_MAXIMO = 0.6 * w * h
    FRAME_CHECK_INTERVAL = 1200
    MAX_TENTATIVAS = 20

    video_writer = None
    video_writer2 = None
    falhas_consecutivas = 0

    # Tenta abrir a conexão
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)

    # Verifica se abriu corretamente
    if not cap.isOpened():
        print("[ERRO] Não foi possível abrir o stream.")
        return

    print("[INFO] Conectado ao stream. Pressione 'q' para sair.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[AVISO] Falha ao ler frame. Tentando reconexão")
            cap.release()
            time.sleep(1)
            cap= cv2.VideoCapture(url, cv2.CAP_FFMPEG)
            if not cap.isOpened():
                falhas_consecutivas += 1
                print(f"[ERRO] RECONEXÃO FALHOU {falhas_consecutivas}/{MAX_TENTATIVAS}")
                if falhas_consecutivas >= MAX_TENTATIVAS:
                    estados_cameras[camera_id].reset()
                    gc.collect()
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
                    cap.release()
                    return
            else:
                print("CONEXÃO RESTABELECIDA")
                falhas_consecutivas = 0 
            continue

        if estados_cameras[camera_id].get_executando():

            if not executando_anterior:
                print("[INFO] Iniciando nova contagem com parâmetros recebidos...")
                parametros = estados_cameras[camera_id].parametros
                if parametros is None:
                    print("[ERRO] Nenhum parâmetro foi definido via /iniciar.")
                    continue

                # Extrair parâmetros e montar caminhos, nomes de vídeo, etc.
                placa = parametros["placa"]
                sequencial = parametros["sequencial"]
                ordem_entrada = parametros["ordem_entrada"]
                data_abate = parametros["data_abate"]
                rampa = parametros["rampa"]
                caminho_output_base = parametros["caminho_video_local"]
                caminho_output_rede = parametros["caminho_video_rede"]

                # Preparar diretórios e nomes
                data_abate_ajustada = converter_data(data_abate)
                caminho_output = os.path.join(caminho_output_base, data_abate_ajustada)
                caminho_output_rede2 = os.path.join(caminho_output_rede, data_abate_ajustada)
                os.makedirs(caminho_output, exist_ok=True)

                
                nome_video = f"{caminho_output}/{rampa}_{placa}-{sequencial}_{ordem_entrada}.mp4"
                nome_video2 = f"{caminho_output}/{rampa}_INF_{placa}-{sequencial}_{ordem_entrada}.mp4"

                n = 1
                while os.path.exists(nome_video):
                    nome_video = f"{caminho_output}/{rampa}_{placa}-{sequencial}_{ordem_entrada}({n}).mp4"
                    nome_video2 = f"{caminho_output}/{rampa}_INF_{placa}-{sequencial}_{ordem_entrada}({n}).mp4"
                    n += 1

                nome_video_rede = os.path.join(caminho_output_rede2, f"{placa}-{sequencial}_{ordem_entrada}.mp4")

                #Reseta variaveis de contagem
                object_crossing = {}
                in_count = 0
                out_count = 0
                video_writer = None
                video_writer2 = None
                frame_count = 0

                executando_anterior = True  # Marcar que já iniciamos

            frame = crop_para_5x4(frame, crop_configs[rampa])
            frame = cv2.resize(frame, (640, 512))

            if video_writer is None and video_writer2 is None:
                h_final, w_final = frame.shape[:2]
                video_writer = cv2.VideoWriter(nome_video, cv2.VideoWriter_fourcc(*"mp4v"), 10, (w_final, h_final))
                video_writer2 = cv2.VideoWriter(nome_video2, cv2.VideoWriter_fourcc(*"mp4v"), 10, (w_final, h_final))

            frame_count += 1
            video_writer.write(frame)
            
            
            with torch.no_grad():
                with yolo_lock:  # Usa yolo_lock de state
                    resultados = modelo.track(
                        half=True,
                        source=frame,
                        conf=0.6,
                        iou=0.5,
                        tracker="config/trackers/bytetrack.yaml",
                        persist=True,
                        imgsz=640
                    )

            objetos_presentes = resultados[0].boxes is not None and len(resultados[0].boxes) > 0

            if estados_cameras[camera_id].parar_event.is_set() and not objetos_presentes:
                print(f"[CONTADOR] Nenhum objeto detectado e parada pendente para. Encerrando contagem.")
                
                contagem = in_count - out_count
                estados_cameras[camera_id].resultado = contagem
                print(f"[CONTADOR] Contagem final: {contagem} (Entradas: {in_count} / Saídas: {out_count})")

                #cv2.destroyAllWindows()

                # Liberação dos recursos
                if video_writer:
                    video_writer.release()
                if video_writer2:
                    video_writer2.release()

                # Copiar vídeos para rede
                if nome_video and nome_video_rede:
                    copiar_para_rede(nome_video, nome_video_rede)
                if nome_video2 and nome_video_rede:
                    copiar_para_rede(nome_video2, nome_video_rede)

                gc.collect()
                torch.cuda.empty_cache()
                torch.cuda.synchronize()

                estados_cameras[camera_id].reset()
                executando_anterior = False
                continue  # Volta para o início do loop aguardando novo iniciar

            if objetos_presentes:
                for box in resultados[0].boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    obj_id = int(box.id[0]) if box.id is not None else None
                    obj_conf = f"{float(box.conf[0]):.02f}" if box.conf is not None else None

                    obj_area = (x2 - x1) * (y2 - y1)
                    if obj_area > LIMITE_MAXIMO:
                        continue

                    if obj_id is not None:
                        centro_x = (x1 + x2) // 2
                        centro_y = (y1 + y2) // 2
                        if obj_id not in object_crossing:
                            if centro_x < LINE_1:
                                object_crossing[obj_id] = "linha_1"
                            elif centro_x >= LINE_2:
                                object_crossing[obj_id] = "linha_2"
                            else:
                                object_crossing[obj_id] = "entre_linhas"

                        if object_crossing[obj_id] == "linha_1" and centro_x >= LINE_2:
                            out_count += 1
                            object_crossing[obj_id] = "linha_2"
                        elif object_crossing[obj_id] == "linha_2" and centro_x <= LINE_1:
                            in_count += 1
                            object_crossing[obj_id] = "linha_1"

                        cv2.circle(frame, (centro_x, centro_y), radius=5, color=(255, 0, 0))

                    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                    cv2.putText(frame, f"ID: {obj_id} {obj_conf}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

            cv2.line(frame, (LINE_1, 0), (LINE_1, frame.shape[0]), (0, 255, 0), 2)
            cv2.line(frame, (LINE_2, 0), (LINE_2, frame.shape[0]), (0, 0, 255), 2)
            cv2.putText(frame, f"Entradas: {in_count}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, f"Saidas: {out_count}", (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, f"Contagem: {in_count - out_count}", (50, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            video_writer2.write(frame)
            
            #cv2.imshow("Stream RTSP", frame)
            #cv2.waitKey(1)

            contagem = in_count - out_count
            estados_cameras[camera_id].resultado = contagem
            
            if frame_count % FRAME_CHECK_INTERVAL == 0:
                torch.cuda.empty_cache()

                # Sai se apertar 'q'
        else: 
            executando_anterior = False
            


            

    


