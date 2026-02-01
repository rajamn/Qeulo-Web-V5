STD_HISTORY_PHRASES = [

    # ===============================
    # Medical History
    # ===============================
    {
        "id": "HIS_DM",
        "text": "Known diabetic on treatment.",
        "category": "Medical History",
        "specialties": ["general", "medicine"],
        "priority": 1
    },
    {
        "id": "HIS_HTN",
        "text": "Known hypertensive on regular medication.",
        "category": "Medical History",
        "specialties": ["general", "medicine"],
        "priority": 1
    },
    {
        "id": "HIS_ASTHMA",
        "text": "History of bronchial asthma.",
        "category": "Medical History",
        "specialties": ["general", "medicine", "pediatrics"],
        "priority": 2
    },
    {
        "id": "HIS_COPD",
        "text": "Known case of chronic obstructive pulmonary disease (COPD).",
        "category": "Medical History",
        "specialties": ["medicine", "pulmonology"],
        "priority": 2
    },
    {
        "id": "HIS_THYROID",
        "text": "History of thyroid disorder.",
        "category": "Medical History",
        "specialties": ["general", "medicine"],
        "priority": 2
    },
    {
        "id": "HIS_EPILEPSY",
        "text": "Known case of epilepsy on treatment.",
        "category": "Medical History",
        "specialties": ["medicine", "neurology"],
        "priority": 2
    },
    {
        "id": "HIS_HEART_DZ",
        "text": "History of heart disease.",
        "category": "Medical History",
        "specialties": ["medicine", "cardiology"],
        "priority": 1
    },
    {
        "id": "HIS_TB_PAST",
        "text": "Past history of tuberculosis.",
        "category": "Medical History",
        "specialties": ["general", "medicine"],
        "priority": 2
    },
    {
        "id": "HIS_HEPATITIS",
        "text": "History of hepatitis or jaundice.",
        "category": "Medical History",
        "specialties": ["medicine", "gastroenterology"],
        "priority": 2
    },
    {
        "id": "HIS_CANCER",
        "text": "History of malignancy.",
        "category": "Medical History",
        "specialties": ["medicine", "oncology"],
        "priority": 1
    },
    {
        "id": "HIS_CKD",
        "text": "Known case of chronic kidney disease.",
        "category": "Medical History",
        "specialties": ["medicine", "nephrology"],
        "priority": 1
    },

    # ===============================
    # Surgical History
    # ===============================
    {
        "id": "HIS_APPENDIX",
        "text": "History of appendectomy.",
        "category": "Surgical History",
        "specialties": ["general", "surgery"],
        "priority": 2
    },
    {
        "id": "HIS_CSECTION",
        "text": "History of cesarean section.",
        "category": "Surgical History",
        "specialties": ["gynecology"],
        "priority": 1
    },
    {
        "id": "HIS_CARDIAC_SURG",
        "text": "History of cardiac surgery.",
        "category": "Surgical History",
        "specialties": ["cardiology", "cardiothoracic"],
        "priority": 1
    },
    {
        "id": "HIS_ORTHO_SURG",
        "text": "History of orthopedic surgery.",
        "category": "Surgical History",
        "specialties": ["orthopedics"],
        "priority": 2
    },
    {
        "id": "HIS_MAJOR_SURG",
        "text": "History of other major surgery.",
        "category": "Surgical History",
        "specialties": ["general"],
        "priority": 2
    },

    # ===============================
    # Allergies
    # ===============================
    {
        "id": "HIS_DRUG_ALLERGY",
        "text": "History of drug allergy.",
        "category": "Allergies",
        "specialties": ["general"],
        "priority": 1
    },
    {
        "id": "HIS_FOOD_ALLERGY",
        "text": "History of food allergy.",
        "category": "Allergies",
        "specialties": ["general"],
        "priority": 2
    },
    {
        "id": "HIS_ENV_ALLERGY",
        "text": "History of environmental allergy.",
        "category": "Allergies",
        "specialties": ["general"],
        "priority": 2
    },
    {
        "id": "HIS_NO_ALLERGY",
        "text": "No known allergies.",
        "category": "Allergies",
        "specialties": ["general"],
        "priority": 1
    },

    # ===============================
    # Family History
    # ===============================
    {
        "id": "HIS_FH_DM",
        "text": "Family history of diabetes mellitus.",
        "category": "Family History",
        "specialties": ["general"],
        "priority": 2
    },
    {
        "id": "HIS_FH_HTN",
        "text": "Family history of hypertension.",
        "category": "Family History",
        "specialties": ["general"],
        "priority": 2
    },
    {
        "id": "HIS_FH_HEART",
        "text": "Family history of heart disease.",
        "category": "Family History",
        "specialties": ["general"],
        "priority": 2
    },
    {
        "id": "HIS_FH_CANCER",
        "text": "Family history of malignancy.",
        "category": "Family History",
        "specialties": ["general"],
        "priority": 1
    },
    {
        "id": "HIS_FH_PSYCH",
        "text": "Family history of psychiatric illness.",
        "category": "Family History",
        "specialties": ["general", "psychiatry"],
        "priority": 2
    },
    {
        "id": "HIS_FH_GENETIC",
        "text": "Family history of genetic disorder.",
        "category": "Family History",
        "specialties": ["general"],
        "priority": 1
    },

    # ===============================
    # Medication History
    # ===============================
    {
        "id": "HIS_CURR_MEDS",
        "text": "On regular long-term medications.",
        "category": "Medication History",
        "specialties": ["general"],
        "priority": 1
    },
    {
        "id": "HIS_PAST_MEDS",
        "text": "History of past long-term medication use.",
        "category": "Medication History",
        "specialties": ["general"],
        "priority": 2
    },
    {
        "id": "HIS_STEROIDS",
        "text": "History of steroid use.",
        "category": "Medication History",
        "specialties": ["general", "medicine"],
        "priority": 1
    },
    {
        "id": "HIS_CHEMO_RAD",
        "text": "History of chemotherapy or radiotherapy.",
        "category": "Medication History",
        "specialties": ["oncology"],
        "priority": 1
    },

    # ===============================
    # Social History
    # ===============================
    {
        "id": "HIS_SMOKING",
        "text": "History of smoking.",
        "category": "Social History",
        "specialties": ["general", "medicine"],
        "priority": 2
    },
    {
        "id": "HIS_ALCOHOL",
        "text": "History of alcohol consumption.",
        "category": "Social History",
        "specialties": ["general"],
        "priority": 2
    },
    {
        "id": "HIS_SUBSTANCE",
        "text": "History of substance abuse.",
        "category": "Social History",
        "specialties": ["general", "psychiatry"],
        "priority": 1
    },
    {
        "id": "HIS_OCC_EXPOSURE",
        "text": "History of occupational exposure.",
        "category": "Social History",
        "specialties": ["general"],
        "priority": 2
    },
    {
        "id": "HIS_DIET",
        "text": "Dietary habits noted.",
        "category": "Social History",
        "specialties": ["general"],
        "priority": 3
    },
    {
        "id": "HIS_EXERCISE",
        "text": "Exercise habits noted.",
        "category": "Social History",
        "specialties": ["general"],
        "priority": 3
    },

    # ===============================
    # Recent / Special History
    # ===============================
    {
        "id": "HIS_RECENT_HOSP",
        "text": "History of recent hospitalization.",
        "category": "Recent History",
        "specialties": ["general"],
        "priority": 1
    },
    {
        "id": "HIS_VACCINATION",
        "text": "Vaccination status reviewed.",
        "category": "Recent History",
        "specialties": ["general"],
        "priority": 2
    },
    {
        "id": "HIS_TRAUMA",
        "text": "History of recent trauma or injury.",
        "category": "Recent History",
        "specialties": ["general", "orthopedics"],
        "priority": 1
    },
    {
        "id": "HIS_AUTOIMMUNE",
        "text": "History of autoimmune disorder.",
        "category": "Recent History",
        "specialties": ["medicine", "rheumatology"],
        "priority": 1
    },
    {
        "id": "HIS_PREG_OBS",
        "text": "Relevant pregnancy or obstetric history noted.",
        "category": "Recent History",
        "specialties": ["gynecology"],
        "priority": 1
    }
]
