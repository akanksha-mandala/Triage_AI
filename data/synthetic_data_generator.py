import pandas as pd
import numpy as np
import random

np.random.seed(42)

num_samples = 3000

symptom_options = [
    "Chest Pain",
    "Seizure",
    "Shortness of Breath",
    "Severe Headache",
    "Fever",
    "Cough"
]

condition_options = [
    "Diabetes",
    "Hypertension",
    "Heart Disease",
    "Asthma",
    "None"
]

data = []

for i in range(num_samples):

    age = np.random.randint(18, 90)
    gender = random.choice(["Male", "Female"])
    bp = np.random.randint(100, 190)
    hr = np.random.randint(55, 140)
    temp = round(np.random.uniform(97, 103), 1)

    symptom = random.choice(symptom_options)
    pre_existing = random.choice(condition_options)

    risk_score = 0

    # Age factor
    if age > 60:
        risk_score += 2
    elif age > 40:
        risk_score += 1

    # BP factor
    if bp > 160:
        risk_score += 2
    elif bp > 140:
        risk_score += 1

    # HR factor
    if hr > 120:
        risk_score += 2
    elif hr > 100:
        risk_score += 1

    # Temperature factor
    if temp > 101:
        risk_score += 2
    elif temp > 99:
        risk_score += 1

    # Symptom factor
    if symptom in ["Chest Pain", "Seizure"]:
        risk_score += 3
    elif symptom in ["Shortness of Breath", "Severe Headache"]:
        risk_score += 2
    else:
        risk_score += 1

    # Condition factor
    if pre_existing == "Heart Disease":
        risk_score += 2
    elif pre_existing in ["Diabetes", "Hypertension", "Asthma"]:
        risk_score += 1

    # Final Risk Level
    if risk_score >= 8:
        risk = "High"
    elif risk_score >= 4:
        risk = "Medium"
    else:
        risk = "Low"

    data.append([
        f"P{i+1}",
        age,
        gender,
        symptom,
        bp,
        hr,
        temp,
        pre_existing,
        risk
    ])

df = pd.DataFrame(data, columns=[
    "patient_id",
    "age",
    "gender",
    "symptom",
    "bp",
    "hr",
    "temp",
    "pre_existing",
    "risk"
])

df.to_csv("data/synthetic_triage_data.csv", index=False)
print("Dataset Generated Successfully!")