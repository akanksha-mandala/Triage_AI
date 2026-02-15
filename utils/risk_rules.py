def apply_safety_rules(age, bp, hr, temp, symptom, pre_existing):
    """
    Safety override rules for critical medical conditions.
    Returns:
        "High"  -> Immediate high-risk override
        None    -> No override, allow ML prediction
    """

    # -----------------------------
    # 1️⃣ Extreme Vital Overrides
    # -----------------------------

    # Very High Blood Pressure
    if bp >= 180:
        return "High"

    # Dangerously Low Blood Pressure
    if bp <= 80:
        return "High"

    # Very High Heart Rate
    if hr >= 130:
        return "High"

    # Dangerously Low Heart Rate
    if hr <= 40:
        return "High"

    # Very High Fever
    if temp >= 103:
        return "High"

    # Hypothermia
    if temp <= 95:
        return "High"

    # -----------------------------
    # 2️⃣ Critical Symptoms
    # -----------------------------

    critical_symptoms = [
        "Chest Pain",
        "Seizure",
        "Shortness of Breath",
        "Unconsciousness"
    ]

    if symptom in critical_symptoms:
        # High priority for elderly
        if age >= 60:
            return "High"

        # High priority if pre-existing heart condition
        if pre_existing in ["Heart Disease", "Hypertension"]:
            return "High"

    # -----------------------------
    # 3️⃣ Vulnerable Age Groups
    # -----------------------------

    # Very young + fever risk
    if age <= 5 and temp >= 101:
        return "High"

    # Elderly + moderate vitals
    if age >= 70 and (bp > 160 or hr > 110):
        return "High"

    # -----------------------------
    # No override
    # -----------------------------
    return None