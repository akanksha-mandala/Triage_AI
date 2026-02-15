def route_patient(risk_level, symptom, pre_existing):
    """
    Determines optimal department routing based on
    risk level, symptoms, and medical history.
    
    Returns:
        {
            "department": str,
            "priority": str,
            "estimated_wait": int (minutes)
        }
    """

    # -------------------------
    # 1️⃣ Department Mapping
    # -------------------------

    symptom_department_map = {
        "Chest Pain": "Cardiology",
        "Shortness of Breath": "Pulmonology",
        "Fever": "General Medicine",
        "Seizure": "Neurology",
        "Head Injury": "Emergency",
        "Pregnancy Complication": "Gynecology",
        "Abdominal Pain": "Gastroenterology",
        "Unconsciousness": "Emergency"
    }

    department = symptom_department_map.get(symptom, "General Medicine")

    # Pre-existing condition override
    if pre_existing == "Heart Disease":
        department = "Cardiology"

    if pre_existing == "Diabetes":
        department = "Endocrinology"

    # -------------------------
    # 2️⃣ Priority Logic
    # -------------------------

    if risk_level == "High":
        priority = "Immediate"
        estimated_wait = 0

    elif risk_level == "Medium":
        priority = "Urgent"
        estimated_wait = 15

    else:
        priority = "Standard"
        estimated_wait = 30

    # Emergency override
    if department == "Emergency":
        priority = "Immediate"
        estimated_wait = 0

    # -------------------------
    # 3️⃣ Return Structured Output
    # -------------------------

    return {
        "department": department,
        "priority": priority,
        "estimated_wait": estimated_wait
    }