import re
import random
import pandas as pd
import numpy as np
import csv
import os
from sklearn import preprocessing
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from difflib import get_close_matches
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

class HealthChatBotService:
    def __init__(self):
        self.severityDictionary = {}
        self.description_list = {}
        self.precautionDictionary = {}
        self.symptoms_dict = {}
        self.model = None
        self.le = None
        self.cols = None
        self.training_data = None
        
        # Load and Train immediately on initialization
        self.load_data_and_train()
        self.load_dictionaries()

    def load_data_and_train(self):
        # Determine base path relative to this file
        base_path = os.path.dirname(os.path.abspath(__file__))
        train_path = os.path.join(base_path, 'Data', 'Training.csv')
        
        self.training_data = pd.read_csv(train_path)
        
        # Clean duplicate column names
        self.training_data.columns = self.training_data.columns.str.replace(r"\.\d+$", "", regex=True)
        self.training_data = self.training_data.loc[:, ~self.training_data.columns.duplicated()]
        
        # Features and labels
        self.cols = self.training_data.columns[:-1]
        x = self.training_data[self.cols]
        y = self.training_data['prognosis']
        
        # Encode target
        self.le = preprocessing.LabelEncoder()
        y = self.le.fit_transform(y)
        
        # Train-test split (keeping split for consistency, though we just fit full/train here for prod usually, but sticking to original logic)
        x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.33, random_state=42)
        
        # Model
        self.model = RandomForestClassifier(n_estimators=300, random_state=42)
        self.model.fit(x_train, y_train)

        # Map symptoms to index
        self.symptoms_dict = {symptom: idx for idx, symptom in enumerate(x)}

    def load_dictionaries(self):
        base_path = os.path.dirname(os.path.abspath(__file__))
        
        # Description
        try:
            with open(os.path.join(base_path, 'MasterData', 'symptom_Description.csv')) as csv_file:
                for row in csv.reader(csv_file):
                    if len(row) >= 2:
                        self.description_list[row[0]] = row[1]
        except Exception as e:
            print(f"Error loading descriptions: {e}")

        # Severity
        try:
            with open(os.path.join(base_path, 'MasterData', 'symptom_severity.csv')) as csv_file:
                for row in csv.reader(csv_file):
                    try:
                        self.severityDictionary[row[0]] = int(row[1])
                    except:
                        pass
        except Exception as e:
            print(f"Error loading severity: {e}")

        # Precaution
        try:
            with open(os.path.join(base_path, 'MasterData', 'symptom_precaution.csv')) as csv_file:
                for row in csv.reader(csv_file):
                    if len(row) >= 5:
                        self.precautionDictionary[row[0]] = [row[1], row[2], row[3], row[4]]
        except Exception as e:
             print(f"Error loading precautions: {e}")

    def extract_symptoms(self, user_input):
        symptom_synonyms = {
            "stomach ache": "stomach_pain", "belly pain": "stomach_pain", "tummy pain": "stomach_pain",
            "loose motion": "diarrhea", "motions": "diarrhea",
            "high temperature": "fever", "temperature": "fever", "feaver": "fever",
            "coughing": "cough", "throat pain": "sore_throat",
            "cold": "chills", "breathing issue": "breathlessness", "shortness of breath": "breathlessness",
            "body ache": "muscle_pain",
        }
        
        extracted = []
        text = user_input.lower().replace("-", " ")

        # 1. Synonym replacement
        for phrase, mapped in symptom_synonyms.items():
            if phrase in text:
                extracted.append(mapped)

        # 2. Exact match
        for symptom in self.cols:
            if symptom.replace("_", " ") in text:
                extracted.append(symptom)

        # 3. Fuzzy match
        words = re.findall(r"\w+", text)
        for word in words:
            close = get_close_matches(word, [s.replace("_", " ") for s in self.cols], n=1, cutoff=0.8)
            if close:
                for sym in self.cols:
                    if sym.replace("_", " ") == close[0]:
                        extracted.append(sym)
        
        return list(set(extracted))

    def predict_disease(self, symptoms_list):
        input_vector = np.zeros(len(self.symptoms_dict))
        for symptom in symptoms_list:
            if symptom in self.symptoms_dict:
                input_vector[self.symptoms_dict[symptom]] = 1

        pred_proba = self.model.predict_proba([input_vector])[0]
        pred_class = np.argmax(pred_proba)
        disease = self.le.inverse_transform([pred_class])[0]
        confidence = round(pred_proba[pred_class] * 100, 2)
        return disease, confidence

    def get_related_symptoms(self, disease):
        # Get symptoms related to the disease for follow-up
        try:
            disease_symptoms = list(self.training_data[self.training_data['prognosis'] == disease].iloc[0][:-1].index[
                self.training_data[self.training_data['prognosis'] == disease].iloc[0][:-1] == 1
            ])
            return disease_symptoms
        except:
            return []

    def process_message(self, message, context):
        state = context.get('state', 'START')
        response = ""
        
        if state == 'START':
            response = "Hello! I am your AI Health Assistant. 🤖\nPlease answer a few questions so I can understand your condition.\n\n👉 What is your name?"
            context['state'] = 'ASK_AGE'
            
        elif state == 'ASK_AGE':
            context['name'] = message
            response = f"Nice to meet you, {message}. 👉 How old are you?"
            context['state'] = 'ASK_GENDER'
            
        elif state == 'ASK_GENDER':
            context['age'] = message
            response = "👉 What is your gender? (M/F/Other)"
            context['state'] = 'ASK_SYMPTOMS'
            
        elif state == 'ASK_SYMPTOMS':
            context['gender'] = message
            response = "👉 Please describe your symptoms (e.g., 'I have fever and headline')."
            context['state'] = 'PROCESS_SYMPTOMS'
            
        elif state == 'PROCESS_SYMPTOMS':
            symptoms_list = self.extract_symptoms(message)
            if not symptoms_list:
                response = "❌ I couldn't understand those symptoms. Please describe them differently or list more specific symptoms."
                # Keep state same
                return response, context
            
            context['symptoms_list'] = symptoms_list
            response = f"✅ Detected symptoms: {', '.join([s.replace('_', ' ') for s in symptoms_list])}.\n\n"
            
            # Initial prediction to find related symptoms
            disease, conf = self.predict_disease(symptoms_list)
            context['predicted_disease'] = disease
            
            # Get follow-up questions
            related = self.get_related_symptoms(disease)
            # Filter out already reported symptoms
            questions_to_ask = [sym for sym in related if sym not in symptoms_list]
            
            context['questions_queue'] = questions_to_ask[:8] # Max 8 questions just like original
            context['question_index'] = 0
            
            if context['questions_queue']:
                sym = context['questions_queue'][0]
                response += f"👉 Do you also have **{sym.replace('_', ' ')}**? (yes/no)"
                context['state'] = 'FOLLOW_UP'
            else:
                # No follow up needed (rare but possible), jump to result
                return self.finalize_diagnosis(context)

        elif state == 'FOLLOW_UP':
            ans = message.lower().strip()
            idx = context.get('question_index', 0)
            queue = context.get('questions_queue', [])
            
            if ans in ['yes', 'y', 'yeah']:
                current_sym = queue[idx]
                context['symptoms_list'].append(current_sym)
            
            context['question_index'] = idx + 1
            
            if context['question_index'] < len(queue):
                next_sym = queue[context['question_index']]
                response = f"👉 Do you also have **{next_sym.replace('_', ' ')}**? (yes/no)"
            else:
                return self.finalize_diagnosis(context)
                
        else:
            response = "I'm not sure what happened. Let's start over. 👉 What is your name?"
            context = {'state': 'ASK_AGE'}
            
        return response, context

    def finalize_diagnosis(self, context):
        symptoms = context.get('symptoms_list', [])
        disease, confidence = self.predict_disease(symptoms)
        
        desc = self.description_list.get(disease, "No description available.")
        
        response = f"---------------- Result ----------------\n"
        response += f"🩺 You may have: **{disease}**\n"
        response += f"🔎 Confidence: {confidence}%\n"
        response += f"📖 Description: {desc}\n\n"
        
        if disease in self.precautionDictionary:
            response += "🛡️ Suggested precautions:\n"
            for i, prec in enumerate(self.precautionDictionary[disease], 1):
                response += f"{i}. {prec.title()}\n"
        
        quotes = [
            "🌸 Health is wealth, take care of yourself.",
            "💪 A healthy outside starts from the inside.",
            "☀️ Every day is a chance to get stronger and healthier.",
            "🌿 Take a deep breath, your health matters the most.",
            "🌺 Remember, self-care is not selfish."
        ]
        response += f"\n💡 {random.choice(quotes)}"
        
        context['state'] = 'DONE' # End of flow
        return response, context
