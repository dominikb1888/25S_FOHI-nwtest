from fastapi import FastAPI

import redis
from redis.commands.json.path import Path

import json
import os

app = FastAPI()

# Connect to Redis
r = redis.Redis(host="redis", port=6379, decode_responses=True)

folder_path = "fhir"
for file in os.listdir(folder_path):
    fhir_patient_file = os.path.join(folder_path, file)
    with open(fhir_patient_file, 'rb') as f:
        fhir_patient = json.load(f)

    uuid = fhir_patient["entry"][0]["fullUrl"]
    r.json().set(uuid, Path.rootPath(), fhir_patient)


@app.get("/")
def read_root():
    keys = r.keys()
    return [r.get(key) for key in keys]


