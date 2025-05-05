from fastapi import FastAPI
import redis
from redis.commands.json.path import Path
import json
import os

app = FastAPI()

# Connect to Redis
r = redis.Redis(host="redis", port=6379, decode_responses=True)

@app.on_event("startup")
def load_fhir_data():
    folder_path = "./fhir"
    for file in os.listdir(folder_path):
        try:
            fhir_patient_file = os.path.join(folder_path, file)
            with open(fhir_patient_file, 'rb') as f:
                fhir_patient = json.load(f)
            uuid = fhir_patient["entry"][0]["fullUrl"]
            r.json().set(f"fhir:{uuid}", "$", fhir_patient)
        except Exception as e:
            print(f"Error loading {file}: {e}")

@app.get("/")
def read_root():
    keys = r.keys("fhir:*")
    return [r.json().get(key) for key in keys]
