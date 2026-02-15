def translate(text, language="English"):

    translations = {

        # ---------------- UI Labels ----------------
        "Age": {
            "Hindi": "आयु",
            "Telugu": "వయస్సు",
            "Tamil": "வயது",
            "Kannada": "ವಯಸ್ಸು"
        },

        "Gender": {
            "Hindi": "लिंग",
            "Telugu": "లింగం",
            "Tamil": "பாலினம்",
            "Kannada": "ಲಿಂಗ"
        },

        "Symptoms": {
            "Hindi": "लक्षण",
            "Telugu": "లక్షణాలు",
            "Tamil": "அறிகுறிகள்",
            "Kannada": "ಲಕ್ಷಣಗಳು"
        },

        "Blood Pressure": {
            "Hindi": "रक्तचाप",
            "Telugu": "రక్తపోటు",
            "Tamil": "இரத்த அழுத்தம்",
            "Kannada": "ರಕ್ತದ ಒತ್ತಡ"
        },

        "Heart Rate": {
            "Hindi": "हृदय गति",
            "Telugu": "హృదయ స్పందన",
            "Tamil": "இதய துடிப்பு",
            "Kannada": "ಹೃದಯ ಬಡಿತ"
        },

        "Temperature": {
            "Hindi": "तापमान",
            "Telugu": "ఉష్ణోగ్రత",
            "Tamil": "வெப்பநிலை",
            "Kannada": "ತಾಪಮಾನ"
        },

        "Pre-Existing Condition": {
            "Hindi": "पूर्व रोग",
            "Telugu": "ముందస్తు వ్యాధి",
            "Tamil": "முன் நோய்",
            "Kannada": "ಹಿಂದಿನ ಕಾಯಿಲೆ"
        },

        "Submit": {
            "Hindi": "जमा करें",
            "Telugu": "సమర్పించండి",
            "Tamil": "சமர்ப்பிக்கவும்",
            "Kannada": "ಸಲ್ಲಿಸು"
        },

        "Results": {
            "Hindi": "परिणाम",
            "Telugu": "ఫలితాలు",
            "Tamil": "முடிவுகள்",
            "Kannada": "ಫಲಿತಾಂಶ"
        },

        "Risk Level": {
            "Hindi": "जोखिम स्तर",
            "Telugu": "ప్రమాద స్థాయి",
            "Tamil": "அபாய நிலை",
            "Kannada": "ಅಪಾಯ ಮಟ್ಟ"
        },

        "Department": {
            "Hindi": "विभाग",
            "Telugu": "విభాగం",
            "Tamil": "துறை",
            "Kannada": "ವಿಭಾಗ"
        },

        "Priority": {
            "Hindi": "प्राथमिकता",
            "Telugu": "ప్రాధాన్యత",
            "Tamil": "முன்னுரிமை",
            "Kannada": "ಪ್ರಾಥಮ್ಯ"
        },

        "Estimated Wait Time": {
            "Hindi": "अनुमानित प्रतीक्षा समय",
            "Telugu": "అంచనా వేచి సమయం",
            "Tamil": "மதிப்பிடப்பட்ட காத்திருப்பு நேரம்",
            "Kannada": "ಅಂದಾಜು ಕಾಯುವ ಸಮಯ"
        },

        "Model Explainability": {
            "Hindi": "मॉडल व्याख्या",
            "Telugu": "మోడల్ వివరణ",
            "Tamil": "மாதிரி விளக்கம்",
            "Kannada": "ಮಾದರಿ ವಿವರಣೆ"
        },

        # ---------------- Risk Values ----------------
        "High": {
            "Hindi": "उच्च",
            "Telugu": "అధిక",
            "Tamil": "உயர்",
            "Kannada": "ಹೆಚ್ಚು"
        },

        "Medium": {
            "Hindi": "मध्यम",
            "Telugu": "మధ్యస్థ",
            "Tamil": "நடுத்தரம்",
            "Kannada": "ಮಧ್ಯಮ"
        },

        "Low": {
            "Hindi": "कम",
            "Telugu": "తక్కువ",
            "Tamil": "குறைவு",
            "Kannada": "ಕಡಿಮೆ"
        }
    }

    if language == "English":
        return text

    if text in translations and language in translations[text]:
        return translations[text][language]

    return text