from fastapi import FastAPI, HTTPException
from typing import List
import redis
from redis.commands.json.path import Path
import json
import os

from fhir.resources.bundle import Bundle
from fhir.resources.patient import Patient

app = FastAPI()

# Connect to Redis
r = redis.Redis(host="redis", port=6379, decode_responses=True)

@app.on_event("startup")
def load_fhir_data():
    folder_path = "./fhir"
    for file in os.listdir(folder_path):
        try:
            fhir_patient_file = os.path.join(folder_path, file)
            with open(fhir_patient_file, 'r', encoding='utf-8') as f:
                fhir_data = json.load(f)

            # Validate as FHIR Bundle
            bundle = Bundle.parse_obj(fhir_data)

            # Use first entry fullUrl as UUID key
            uuid = bundle.entry[0].fullUrl
            r.json().set(f"fhir:{uuid}", "$", fhir_data)
        except Exception as e:
            print(f"Error loading {file}: {e}")

@app.get("/patients", response_model=List[Bundle])
def get_patients():
    keys = r.keys("fhir:*")
    bundles = []
    for key in keys:
        data = r.json().get(key)
        try:
            bundle = Bundle.parse_obj(data)
            bundles.append(bundle)
        except Exception as e:
            print(f"Invalid FHIR bundle in Redis key {key}: {e}")
    return bundles

@app.get("/patients/{id}", response_model=Bundle)
def get_patient_by_id(id: str):
    key = f"fhir:urn:uuid:{id}"
    data = r.json().get(key)
    if not data:
        raise HTTPException(status_code=404, detail="Patient not found")
    try:
        bundle = Bundle.parse_obj(data)
        return bundle
    except Exception:
        raise HTTPException(status_code=500, detail="Invalid FHIR bundle format")

@app.get("/keys", response_model=List[str])
def get_patient_keys():
    return r.keys("fhir:*")
