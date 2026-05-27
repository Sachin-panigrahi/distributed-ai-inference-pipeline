import json
import boto3
import grpc
from kafka import KafkaConsumer, KafkaProducer
import os
import detector_pb2
import detector_pb2_grpc

print("Started gRPC Client")

BOOTSTRAP_SERVER = os.getenv("BOOTSTRAP_SERVER", "my-cluster-kafka-bootstrap.kafka.svc.cluster.local:9092")
CONSUMING_TOPIC = os.getenv("CONSUMING_TOPIC", "image_upload")
consumer = KafkaConsumer(
    CONSUMING_TOPIC,
    group_id="image_group",
    bootstrap_servers=BOOTSTRAP_SERVER
)
PRODUCING_TOPIC = os.getenv("PRODUCING_TOPIC", "classification_result")
producer = KafkaProducer(
    bootstrap_servers=BOOTSTRAP_SERVER,
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

# S3 Config
S3_BUCKET = os.getenv("S3_BUCKET", "my-imageclass")
S3_FOLDER = os.getenv("S3_FOLDER", "datasets")

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY", "")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY", "")
AWS_REGION = os.getenv("AWS_REGION", "")

# S3 Client
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION
)

# gRPC Client
GRPC_SERVER = os.getenv("GRPC_SERVER", "localhost:50051")
channel = grpc.insecure_channel(GRPC_SERVER)
stub = detector_pb2_grpc.DetectorStub(channel)

for msg in consumer:

    try:
        # Kafka Metadata
        data = json.loads(msg.value.decode("utf-8"))

        audit_id = data["audit_id"]
        image_name = data["image_name"]
        timestamp = data["timestamp"]

        # Download image from S3
        s3_key = f"{S3_FOLDER}/{image_name}"

        response = s3_client.get_object(
            Bucket=S3_BUCKET,
            Key=s3_key
        )

        image_bytes = response["Body"].read()

        # Call gRPC AI server
        grpc_request = detector_pb2.ImageRequest(
            image=image_bytes
        )

        grpc_response = stub.DetectObjects(grpc_request)

        result = {
            "audit_id": audit_id,
            "image_name": image_name,
            "timestamp": timestamp,
            "detections": []
        }

        for detection in grpc_response.detections:
            result["detections"].append({
                "class_name": detection.class_name,
                "confidence": detection.confidence,
                "x1": detection.x1,
                "y1": detection.y1,
                "x2": detection.x2,
                "y2": detection.y2
            })

        # Publish final result
        producer.send(
            PRODUCING_TOPIC,
            result
        )

        print("Processed:", result)

    except Exception as e:
        print("Error:", str(e))