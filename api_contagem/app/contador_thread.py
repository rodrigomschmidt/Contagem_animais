import cv2
import os
from datetime import datetime
import torch
import time
import gc
from utilitarios import trigger_manual_correction, copiar_para_rede, load_config, crop_para_5x4
from state_threads import EstadoContador, yolo_lock  # Importa yolo_lock de state

def contador(modelo, caminho_output_base, caminho_output_rede, placa, sequencial,
             ordem_entrada, data_abate, ip, rampa, get_frame_func=None, set_frame_callback=None, camera_id=None):
    gc.collect()
    torch.cuda.empty_cache()
    resultados = None
    state = EstadoContador[camera_id]
    state.parar_event.clear()

    config = load_config("config/config_contagem.txt")

    crop_configs = {
        "P1": {"top": 0, "bottom": 70},
        "P5": {"top": 70, "bottom": 0},
    }

    def converter_data_(data):
        try:
            data_obj = datetime.strptime(data, "%d/%m/%Y")
            return data_obj.strftime("%d.%m.%Y")
        except ValueError as e:
            print(f"Erro ao converter a data: {e}")
            return None

    print(f"[CONTADOR] Aguardando primeiro frame válido para {camera_id}...")

    tentativas = 0
    while tentativas < 10:
        frame = get_frame_func()
        if frame is not None and frame.size != 0:
            break
        time.sleep(0.1)
        tentativas += 1

    if frame is None or frame.size == 0:
        print(f"[CONTADOR] Não foi possível obter um frame válido para {camera_id}. Abortando contagem.")
        return None

    del frame
    gc.collect()

    print(f"[CONTADOR] Primeiro frame válido recebido para {camera_id}. Iniciando inferência.")

    data_abate_ajustada = converter_data_(data_abate)
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

    nome_video_rede = f"{caminho_output_rede2}/{placa}-{sequencial}_{ordem_entrada}.mp4"
    print(f"Salvando vídeo em: {nome_video}")

    object_crossing = {}
    in_count = 0
    out_count = 0
    LINE_1 = 420
    LINE_2 = 460

    w = int(config["w"])
    h = int(config["h"])

    video_writer = None
    video_writer2 = None

    LIMITE_MAXIMO = 0.6 * w * h
    FRAME_CHECK_INTERVAL = 1200
    frame_count = 0
    parar_pendente = False

    try:
        while True:
            time.sleep(0.09)

            if state.parar_event.is_set():
                print(f"[CONTADOR] Sinal de parada recebido para {camera_id}. Aguardando objetos saírem...")
                parar_pendente = True
                state.parar_event.clear()

            frame = get_frame_func()

            if frame is None or frame.size == 0:
                print(f"[CONTADOR] Frame inválido recebido para {camera_id}. Pulando frame.")
                continue

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
                        conf=0.7,
                        iou=0.7,
                        tracker="config/trackers/bytetrack.yaml",
                        persist=True,
                        imgsz=640
                    )

            objetos_presentes = resultados[0].boxes is not None and len(resultados[0].boxes) > 0

            if parar_pendente and not objetos_presentes:
                print(f"[CONTADOR] Nenhum objeto detectado e parada pendente para {camera_id}. Encerrando contagem.")
                break

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

            if set_frame_callback:
                set_frame_callback(frame)

            del resultados, frame
            gc.collect()
            
            if frame_count % FRAME_CHECK_INTERVAL == 0:
                torch.cuda.empty_cache()

    finally:
        if video_writer:
            video_writer.release()
        if video_writer2:
            video_writer2.release()
        if 'resultados' in locals():
            del resultados
        del object_crossing
        gc.collect()
        torch.cuda.empty_cache()
        torch.cuda.synchronize()

    contagem = in_count - out_count
    print(f"A contagem foi de {contagem} para {camera_id}")

    copiar_para_rede(nome_video, nome_video_rede)
    copiar_para_rede(nome_video2, nome_video_rede)

    return contagem