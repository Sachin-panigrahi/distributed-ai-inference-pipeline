````md
# Distributed AI Inference Pipeline

An event-driven AI image processing pipeline built using FastAPI, Kafka, gRPC, Docker, Kubernetes, MySQL, MongoDB, and AWS S3.

The project simulates a production-style distributed system where uploaded images are processed asynchronously through multiple microservices. The pipeline stores images in S3, sends metadata through Kafka, performs object detection using a gRPC inference service, and stores results in MongoDB while maintaining audit tracking in MySQL.

---

## Architecture Overview

```text
User Upload
    ↓
FastAPI Frontend
    ↓
Upload Image to AWS S3
    ↓
Insert Audit Record into MySQL
    ↓
Kafka Topic: image_upload
    ↓
Preprocessor + gRPC Client
    ↓
Download Image from S3
    ↓
gRPC AI Detection Service
    ↓
Kafka Topic: classification_result
    ↓
MongoDB Consumer
    ↓
Store Results in MongoDB
    ↓
Update MySQL Status
````

---

## Tech Stack

### Backend & APIs

* FastAPI
* gRPC
* Protocol Buffers

### Messaging & Streaming

* Apache Kafka

### Databases

* MySQL
* MongoDB

### Cloud & Storage

* AWS S3

### Containerization & Orchestration

* Docker
* Kubernetes

### AI / ML

* YOLOv8 Object Detection

---

# Features

* Upload images through FastAPI UI
* Store uploaded images in S3
* Generate unique audit IDs for every request
* Kafka-based asynchronous communication
* Distributed microservices architecture
* gRPC-based inference communication
* Object detection with confidence scores and bounding boxes
* Store inference results in MongoDB
* Track processing status in MySQL
* Dockerized services
* Kubernetes-ready deployments
* Environment variable based configuration

---

# Project Structure

```text
project/
│
├── frontend/
│   ├── frontend.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── preprocessor/
│   ├── pre_processor_and_client.py
│   ├── detector_pb2.py
│   ├── detector_pb2_grpc.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── grpc-detector/
│   ├── detector.proto
│   ├── detector_server.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── mongodb-consumer/
│   ├── mongodump.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── kubernetes/
│   ├── frontend.yaml
│   ├── preprocessor.yaml
│   ├── grpc.yaml
│   ├── mongodb-consumer.yaml
│   ├── secrets.yaml
│   └── namespace.yaml
│
└── README.md
```

---

# Workflow

## 1. Image Upload

The frontend service accepts image uploads through a FastAPI web interface.

## 2. S3 Upload

Uploaded images are stored in AWS S3 using a generated file name:

```text
AUDITID_TIMESTAMP.jpg
```

Example:

```text
AB12X_20260527153022.jpg
```

## 3. Audit Tracking

A MySQL entry is created with:

* audit_id
* image_name
* processed status

Initially:

```text
processed = NULL
```

## 4. Kafka Event

The frontend publishes image metadata to Kafka.

Example message:

```json
{
  "audit_id": "AB12X",
  "image_name": "AB12X_20260527153022.jpg",
  "timestamp": "20260527153022"
}
```

## 5. Preprocessor Service

The preprocessor service:

* consumes Kafka messages
* downloads the image from S3
* sends image bytes to the gRPC detection service

## 6. AI Detection

The gRPC service performs object detection using YOLOv8 and returns:

* class name
* confidence score
* bounding box coordinates

## 7. Result Storage

The final detection result is:

* published to Kafka
* stored in MongoDB
* MySQL status updated to `completed`

---


# Environment Variables

## Frontend

```env
BOOTSTRAP_SERVER=
PRODUCING_TOPIC=
CONSUMING_TOPIC=

MYSQL_HOST=
MYSQL_USER=
MYSQL_PASSWORD=
MYSQL_DATABASE=
MYSQL_TABLE=

S3_BUCKET=
S3_FOLDER=

AWS_ACCESS_KEY=
AWS_SECRET_KEY=
AWS_REGION=
```

---

## Preprocessor

```env
BOOTSTRAP_SERVER=
CONSUMING_TOPIC=
PRODUCING_TOPIC=

S3_BUCKET=
S3_FOLDER=

AWS_ACCESS_KEY=
AWS_SECRET_KEY=
AWS_REGION=

GRPC_SERVER=
```

---

## MongoDB Consumer

```env
BOOTSTRAP_SERVER=

MONGO_URI=

MYSQL_HOST=
MYSQL_USER=
MYSQL_PASSWORD=
MYSQL_DATABASE=
MYSQL_TABLE=
```

---

# Docker

## Build Images

### Frontend

```bash
docker build -t frontend .
```

### Preprocessor

```bash
docker build -t preprocessor-client .
```

### gRPC Detector

```bash
docker build -t grpc-detector .
```

### MongoDB Consumer

```bash
docker build -t mongodb-consumer .
```

---

# Kubernetes Deployment

Apply manifests:

```bash
kubectl apply -f kubernetes_manifests/
```

Check resources:

```bash
kubectl get pods -n ai-pipeline
```

---

# Sample Detection Result

```json
{
  "audit_id": "AB12X",
  "image_name": "AB12X_20260527153022.jpg",
  "timestamp": "20260527153022",
  "detections": [
    {
      "class_name": "person",
      "confidence": 0.94,
      "x1": 120,
      "y1": 90,
      "x2": 560,
      "y2": 700
    }
  ]
}
```

---

# Why Two Databases?

MySQL is used for structured workflow tracking and audit management.

MongoDB is used for storing flexible AI inference results where the number of detected objects and nested bounding box data can vary between images.

This keeps the pipeline simpler and avoids unnecessary relational complexity for inference data.

---

# Notes

This project was built to explore:

* distributed systems
* event-driven architecture
* cloud-native application design
* AI inference pipelines
* DevOps and MLOps workflows

It is designed as a learning-focused production-style system rather than a simple demo application.

```
```
