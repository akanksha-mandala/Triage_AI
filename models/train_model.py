import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix

# Load dataset
df = pd.read_csv("../data/synthetic_triage_data.csv")

# Encode categorical variables
le_gender = LabelEncoder()
le_symptom = LabelEncoder()
le_condition = LabelEncoder()
le_risk = LabelEncoder()

df["gender"] = le_gender.fit_transform(df["gender"])
df["symptom"] = le_symptom.fit_transform(df["symptom"])
df["pre_existing"] = le_condition.fit_transform(df["pre_existing"])
df["risk"] = le_risk.fit_transform(df["risk"])

# Features & target
X = df.drop(["patient_id", "risk"], axis=1)
y = df["risk"]

# Split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Train model
model = RandomForestClassifier(
    n_estimators=150,
    random_state=42
)

model.fit(X_train, y_train)

# Evaluate
y_pred = model.predict(X_test)

print("Confusion Matrix:")
print(confusion_matrix(y_test, y_pred))

print("\nClassification Report:")
print(classification_report(y_test, y_pred))

# Save model
joblib.dump(model, "risk_model.pkl")

# Save encoders
joblib.dump({
    "gender": le_gender,
    "symptom": le_symptom,
    "pre_existing": le_condition,
    "risk": le_risk
}, "label_encoders.pkl")

print("\nModel and encoders saved successfully!")