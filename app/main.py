from fastapi import FastAPI, HTTPException, Response, Body
from typing import List
import redis
from redis.commands.json.path import Path
import json
import os
from uuid import UUID

from fhir.resources.R4B.bundle import Bundle
from fhir.resources.R4B.patient import Patient

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
def get_patients(response: Response):
    response.headers["Content-Type"] = "application/fhir+json"
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


@app.post("/patient/new") # Do we need a response model?
def create_patient(data: str = Body()): # Can we be more precise here?
    uuid = "a14258f7-4baf-5c34-9264-b1f585f3092c" #TODO: hard-coded UUID for testing!!!
    # Validate as FHIR Bundle
    bundle = Patient.model_validate(data)
    return r.json().set(f"fhir:{uuid}", "$", bundle.json())


@app.get("/patients/{id}", response_model=Bundle)
def get_patient_by_id(response: Response, id: UUID):
    response.headers["Content-Type"] = "application/fhir+json"
    key = f"fhir:{id}"
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


# endpoint: https://pacs.hospital.org (-> Get from actual app context)
# route: /wado-rs/
# paraemeters:
# - studies/1.2.250.1.59.40211.12345678.678910 (study_uuid)
# - series/1.2.250.1.59.40211.789001276.14556172.67789 (series_uuid)
# - /thumbnail
@app.get("/wado-rs/studies/{study_uuid}/series/{series_uuid}/thumbnail", response_model=List)
def get_images(study_uuid: UUID, series_uuid: UUID):
    # retrieve dicom image based on three uuids (study, series, instance)
    # r.get("dicom:studies:1938d290dxc0su0eue2e9:series:2198349ejs90an09:*)
    # pixel array data, convert and store on disk
    # Display images on site using HTML Template
    pass
