# drugs/constants.py

# Standard history presets for prescription notes
HISTORY_PRESETS = [
    'Diabetes Mellitus',
    'Hypertension',
    'Tuberculosis (past)',
    'Asthma',
    'Epilepsy',
    'Rheumatic Fever',
    'Stroke / TIA',
    'Myocardial Infarction',
    'Jaundice / Hepatitis',
    'Thyroid Disorder',
    'Surgical History',
    'Allergies (Drug/Food)',
    'Family History of Cancer',
    'Psychiatric Illness',
    'Recent Hospitalization',
    'Vaccination History',
    'Substance Use (Alcohol/Drugs)',
    'Trauma / Injury',
    'Autoimmune Disorders',
    'Chronic Kidney Disease',
]

# Standard symptom presets for prescription notes
SYMPTOM_PRESETS = [
    'Fever',
    'Cough',
    'Headache',
    'Fatigue',
    'Body ache',
    'Chills',
    'Nausea',
    'Vomiting',
    'Diarrhea',
    'Dizziness',
    'Shortness of breath',
    'Chest pain',
    'Wheezing',
    'Sore throat',
    'Nasal congestion',
    'Sneezing',
    'Confusion',
    'Seizures',
    'Numbness',
    'Tingling',
    'Loss of consciousness',
    'Slurred speech',
    'Palpitations',
    'Chest tightness',
    'Swelling in legs',
    'Syncope (fainting)',
    'Joint pain',
    'Muscle weakness',
    'Back pain',
    'Stiffness',
    'Abdominal pain',
    'Burning sensation during urination',
    'Skin rash',
    'Itching',
    'Weight loss',
    'Loss of appetite',
]

# Standard general clinical findings presets
FINDINGS_PRESETS = [
    'Elevated temperature',
    'Tachycardia',
    'Hypotension',
    'Pallor',
    'Edema',
    'Cyanosis',
    'Dehydration',
    'Lymphadenopathy',
    'Clubbing',
    'Jaundice',
    'Bilateral crepitations',
    'Wheezing',
    'Decreased breath sounds',
    'Bronchial breath sounds',
    'Intercostal retractions',
    'Murmur (e.g., systolic, diastolic)',
    'Gallop rhythm',
    'Raised jugular venous pressure (JVP)',
    'Peripheral pulses weak',
    'Apex beat displaced',
    'Joint swelling',
    'Restricted range of motion',
    'Muscle tenderness',
    'Spinal deformity',
    'Positive straight leg raise',
    'Tenderness in right iliac fossa',
    'Guarding and rigidity',
    'Hepatomegaly',
    'Splenomegaly',
    'Ascites',
    'Positive Babinski sign',
    'Hyperreflexia',
    'Muscle weakness',
    'Cranial nerve palsy',
    'Altered sensorium',
]

# Standard general advice presets
GENERAL_ADVICE_PRESETS = [
    # 🧘‍♂️ Lifestyle & Wellness Advice
    'Maintain a balanced diet',
    'Increase fluid intake',
    'Avoid spicy and oily foods',
    'Get adequate sleep',
    'Practice regular physical activity',
    'Reduce screen time',
    'Avoid smoking and alcohol',
    'Manage stress through relaxation techniques',

    # 🩺 Condition-Specific Advice
    'Monitor blood pressure regularly',
    'Check blood sugar levels as advised',
    'Use inhaler as instructed',
    'Avoid allergens and triggers',
    'Take medications at the same time daily',
    'Follow up with specialist if symptoms persist',
    'Limit salt intake for hypertension',
    'Avoid strenuous activity during recovery',

    # 💊 Medication & Compliance Advice
    'Complete the full course of antibiotics',
    'Do not skip doses',
    'Store medicines in a cool, dry place',
    'Report any side effects immediately',
    'Do not self-medicate',
    'Keep a medication diary if needed',

    # 🧒 Pediatric & Geriatric Advice
    'Ensure proper hydration',
    'Monitor for signs of dehydration or fatigue',
    'Maintain hygiene and handwashing',
    'Use age-appropriate dosing tools',
    'Supervise medication intake',
]
DOSAGE_PRESETS = ['250 mg', '500 mg', '750 mg', '1 g', '2 g',  ]
FREQUENCY_PRESETS = ['OD', 'BD', 'TDS', 'QID', 'HS', 'STAT',]
DURATION_PRESETS = ['3 days', '5 days', '7 days', '10 days', '14 days',]
# Main PRESETS dictionary used by notes_autocomplete and template
FOOD_ORDER_PRESETS = [
    'Before Food',
    'After Food',
    'With Food',
    'Empty Stomach'
]

PRESETS = {
    # Newly added note categories:
    'history': HISTORY_PRESETS,
    'symptoms': SYMPTOM_PRESETS,
    'findings': FINDINGS_PRESETS,
    'general_advice' : GENERAL_ADVICE_PRESETS,

    # Existing preset groups:
    'dosage': DOSAGE_PRESETS,
    'frequency': FREQUENCY_PRESETS,
    'duration': DURATION_PRESETS ,
    'food_order': FOOD_ORDER_PRESETS,
}
