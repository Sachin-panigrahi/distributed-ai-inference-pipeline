import json
from kafka import KafkaConsumer
from pymongo import MongoClient
import pymysql
import os

# Kafka Consumer
BOOTSTRAP_SERVER = os.getenv("BOOTSTRAP_SERVER", "my-cluster-kafka-bootstrap.kafka.svc.cluster.local:9092")
CONSUMING_TOPIC = os.getenv("CONSUMING_TOPIC", "classification_result")
consumer = KafkaConsumer(
    CONSUMING_TOPIC,
    group_id="mongodb_group",  
    bootstrap_servers=BOOTSTRAP_SERVER
)


# MongoDB Config
MONGO_CONNECTION_STRING = os.getenv("MONGO_CONNECTION_STRING", "mongodb://username:password@localhost:27017/detection_results?authSource=detection_results")
MONGO_URI = MONGO_CONNECTION_STRING

DB_NAME = os.getenv("DB_NAME", "detection_results")
DATABASE_NAME = DB_NAME

COLL_NAME = os.getenv("COLL_NAME", "results")
COLLECTION_NAME = COLL_NAME 

mongo_client = MongoClient(MONGO_URI)

db = mongo_client[DATABASE_NAME]

collection = db[COLLECTION_NAME]


# MySQL Config

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_USER = os.getenv("MYSQL_USER", "username")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "password")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "db")
MYSQL_TABLE = os.getenv("MYSQL_TABLE", "table")

def get_db_connection():
    return pymysql.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE
    )

print("MongoDB Consumer Started...")

for msg in consumer:

    try:
        # Decode Kafka Message
        data = json.loads(msg.value.decode("utf-8"))

    
        # Insert into MongoDB

        result = collection.insert_one(data)

        print(f"Inserted Document ID: {result.inserted_id}")


        # Update MySQL Status
        audit_id = data["audit_id"]

        connection = get_db_connection()

        cursor = connection.cursor()

        update_query = f"""
        UPDATE {MYSQL_TABLE}
        SET processed = %s
        WHERE audit_id = %s
        """

        cursor.execute(
            update_query,
            (
                "completed",
                audit_id
            )
        )

        connection.commit()

        cursor.close()
        connection.close()

        print(f"Updated audit_id {audit_id} as completed")

    except Exception as e:
        print("Error:", str(e))