from collections import Counter
import csv
from datetime import datetime, timedelta
import json
import os
from typing import List
from uuid import UUID

from fastapi import FastAPI, HTTPException, Response, Body

from fhir.resources.R4B.bundle import Bundle
from fhir.resources.R4B.patient import Patient
from fhir.resources.R4B.sampleddata import SampledData
from fhir.resources.R4B.observation import Observation
from fhir.resources.R4B.quantity import Quantity

import redis
from redis.commands.json.path import Path



app = FastAPI()

# Connect to Redis
r = redis.Redis(host="redis", port=6379, decode_responses=True)


def clean_heartrate_data(filename) -> dict:
    heartrates = []
    timestamps = []

    with open(filename) as f:
        csvdata = csv.reader(f, delimiter=',', quotechar='"')
        next(csvdata)
        for row in csvdata:
            timestamps.append(datetime.strptime(row[0], '%Y-%m-%dT%H:%M:%S.%f%z'))
            heartrates.append(int(row[1]))

    intervals = [(timestamps[i+1] - timestamps[i]).seconds for i in range(0, len(timestamps)-1)]
    count = Counter(intervals)
    default_interval, _ = count.most_common()[0]

    for j, interval in enumerate(intervals):
        gapsum = 0
        delta = interval - default_interval
        if interval != default_interval:
            for i in range(1, interval-delta+1):
                offset = j + gapsum + i
                existing = timestamps[j + gapsum]
                timestamps.insert(offset,
                                  datetime(existing.year,
                                           existing.month,
                                           existing.day,
                                           existing.hour,
                                           existing.minute,
                                           existing.second + i,
                                           existing.microsecond,
                                           existing.tzinfo
                                           ))
                heartrates.insert(offset, 'E')

        gapsum += delta

    timestamps = [dt.isoformat() for dt in timestamps]

    return dict(zip(timestamps, heartrates))


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

@app.get("/heartrates", response_model=dict)
def get_heartrates():
    # {
    # "2025-06-23T08:57:58.297356Z": 60
    # ...
    #}
    return clean_heartrate_data("csv/heart_rate.csv")
    # 1. load data from csv
    # 2. send it through the data cleaner, which pads the data with symbols for missing values (
    # - E: error - no valid measurement available for this data point
    # - L: below detection point - the value was below the device's detection limit (lowerLimit, which must be provided if this code is used)
    # - U: above detection point - the value was above the device's detection limit (upperLimit, which must be provided if this code is used))

@app.get("/fhir_heartrates", response_model=SampledData)
def get_fhir_heartrates():
    csv_data = clean_heartrate_data("csv/heart_rate.csv")
    string_values = " ".join([str(i) for i in csv_data.values()])
    return SampledData(
        data=string_values,
        period=1000,
        dimensions=1,
        origin=Quantity()
    )

