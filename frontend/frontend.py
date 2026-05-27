from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
from jinja2 import Template
from kafka import KafkaProducer, KafkaConsumer
import threading
import asyncio
import boto3
import pymysql
import random
import string
from datetime import datetime
import json
import os

app = FastAPI()

# Kafka setup
BOOTSTRAP_SERVER = os.getenv("BOOTSTRAP_SERVER", "my-cluster-kafka-bootstrap.kafka.svc.cluster.local:9092")
producer = KafkaProducer(
    bootstrap_servers=BOOTSTRAP_SERVER
)

CONSUMING_TOPIC = os.getenv("CONSUMING_TOPIC", "classification_result")
PRODUCING_TOPIC = os.getenv("PRODUCING_TOPIC", "image_upload")

consumer = KafkaConsumer(
    CONSUMING_TOPIC,
    group_id="result_group",
    bootstrap_servers=BOOTSTRAP_SERVER
)

classification_result = ""


# MYSQL CONFIG
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_USER = os.getenv("MYSQL_USER", "username")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "password")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "db")
MYSQL_TABLE = os.getenv("MYSQL_TABLE", "table")


# S3 CONFIG
S3_BUCKET = os.getenv("S3_BUCKET", "my-imageclass")
S3_FOLDER = os.getenv("S3_FOLDER", "datasets")

# AWS Credentials (or use IAM Role)
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

# MySQL Connection Function
def get_db_connection():
    return pymysql.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE
    )

# Generate unique audit ID of length 5
def generate_audit_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

# Function to consume classification results
def consume_results():
    global classification_result
    for msg in consumer:
        classification_result = msg.value.decode("utf-8")

# Run Kafka consumer in a separate thread
thread = threading.Thread(target=consume_results, daemon=True)
thread.start()

# TailwindCSS Styled HTML Template
html_template = Template("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Image Classifier</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-900 text-white flex items-center justify-center min-h-screen">

    <div class="bg-gray-800 p-6 rounded-xl shadow-lg w-full max-w-md text-center">
        <h1 class="text-3xl font-bold text-blue-400">Image Classifier</h1>
        <p class="text-gray-400 mt-2">Upload an image and get the classification result instantly!</p>

        <form action="/upload/" enctype="multipart/form-data" method="post" class="mt-6">
            <label class="block text-gray-300 text-sm mb-2">Select an image:</label>
            <input type="file" name="file" class="block w-full text-sm text-gray-400 bg-gray-700 p-2 rounded-md border border-gray-600">
            <button type="submit" class="mt-4 bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded-md w-full transition-all duration-300">Upload</button>
        </form>

        <div class="mt-6">
            <h2 class="text-lg font-semibold text-gray-300">Classification Result:</h2>
            <p class="text-2xl font-bold text-green-400 mt-2">{{ result }}</p>
        </div>
    </div>

</body>
</html>
""")

@app.get("/", response_class=HTMLResponse)
async def home():
    return html_template.render(result=classification_result)

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    global classification_result

    try:
        # Read uploaded image
        image_data = await file.read()

        # Generate audit ID
        audit_id = generate_audit_id()

        # Timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

        # File extension
        extension = file.filename.split(".")[-1]

        # New image name
        image_name = f"{audit_id}_{timestamp}.{extension}"

        
        # Upload to S3
        
        s3_key = f"{S3_FOLDER}/{image_name}"

        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=image_data
        )

        
        # Insert into MySQL
        
        connection = get_db_connection()
        cursor = connection.cursor()

        insert_query = f"""
        INSERT INTO {MYSQL_TABLE} (
            audit_id,
            image_name,
            processed
        )
        VALUES (%s, %s, %s)
        """

        cursor.execute(
            insert_query,
            (
                audit_id,
                image_name,
                None
            )
        )

        connection.commit()

        cursor.close()
        connection.close()

        
        # Send metadata to Kafka
        
        message = {
            "audit_id": audit_id,
            "image_name": image_name,
            "timestamp": timestamp
        }
        
        producer.send(
            PRODUCING_TOPIC,
            value=json.dumps(message).encode("utf-8")
        )

        # Wait for classification result
        for _ in range(10):
            await asyncio.sleep(1)
            if classification_result:
                break

        return HTMLResponse(
            html_template.render(
                result=f"{classification_result} | Audit ID: {audit_id}"
            )
        )

    except Exception as e:
        return HTMLResponse(
            html_template.render(
                result=f"Error: {str(e)}"
            )
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)