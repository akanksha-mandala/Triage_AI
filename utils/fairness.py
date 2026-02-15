import pandas as pd


def evaluate_gender_fairness(model, X, y_true, gender_column="gender"):
    """
    Evaluates whether model predictions are disproportionately
    labeling one gender as High risk.

    Parameters:
        model: trained ML model
        X: feature dataframe
        y_true: actual labels (optional, for extension)
        gender_column: column name for gender

    Returns:
        {
            "male_high_rate": float,
            "female_high_rate": float,
            "difference": float,
            "fair": bool
        }
    """

    # Make predictions
    predictions = model.predict(X)

    # Attach predictions to dataframe
    df = X.copy()
    df["prediction"] = predictions

    # High risk assumed label = 2
    HIGH_LABEL = 2

    male_data = df[df[gender_column] == 1]
    female_data = df[df[gender_column] == 0]

    male_high_rate = (
        (male_data["prediction"] == HIGH_LABEL).mean()
        if len(male_data) > 0 else 0
    )

    female_high_rate = (
        (female_data["prediction"] == HIGH_LABEL).mean()
        if len(female_data) > 0 else 0
    )

    difference = abs(male_high_rate - female_high_rate)

    # Threshold of concern (10%)
    fairness_threshold = 0.10

    return {
        "male_high_rate": round(male_high_rate, 3),
        "female_high_rate": round(female_high_rate, 3),
        "difference": round(difference, 3),
        "fair": difference < fairness_threshold
    }