from concurrent import futures
import grpc
import detector_pb2
import detector_pb2_grpc

import cv2
import numpy as np
from ultralytics import YOLO

# Load YOLOv8 model
model = YOLO("yolov8n.pt")

class DetectorService(detector_pb2_grpc.DetectorServicer):

    def DetectObjects(self, request, context):

        # Convert bytes to image
        np_arr = np.frombuffer(request.image, np.uint8)
        image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        # Run inference
        results = model(image)

        detections = []

        for result in results:

            boxes = result.boxes

            for box in boxes:

                cls_id = int(box.cls[0])
                class_name = model.names[cls_id]

                confidence = float(box.conf[0])

                x1, y1, x2, y2 = map(
                    int,
                    box.xyxy[0].tolist()
                )

                detection = detector_pb2.Detection(
                    class_name=class_name,
                    confidence=confidence,
                    x1=x1,
                    y1=y1,
                    x2=x2,
                    y2=y2
                )

                detections.append(detection)

        return detector_pb2.DetectionResponse(
            detections=detections
        )

def serve():

    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10)
    )

    detector_pb2_grpc.add_DetectorServicer_to_server(
        DetectorService(),
        server
    )

    server.add_insecure_port("[::]:50051")

    server.start()

    print("gRPC YOLOv8 Server Running on 50051")

    server.wait_for_termination()

if __name__ == "__main__":
    serve()