import sqlite3
import uuid

def ingest_who_medical_data():
    print("🔄 Lancement du pipeline ETL (Données Médicales OMS/ICD-10)...")
    conn = sqlite3.connect('lexicon_ultimate.db')
    cursor = conn.cursor()

    # Dataset statique représentant l'API ICD-10 de l'OMS en Arabe
    # (En production, remplacez ceci par requests.get("https://icd.who.int/..."))
    oms_arabic_dataset = [
        {"code": "I10", "en": "Essential (Primary) Hypertension", "ar": "ارتفاع ضغط الدم الأساسي (البدئي)"},
        {"code": "E11", "en": "Type 2 Diabetes Mellitus", "ar": "داء السكري من النوع 2"},
        {"code": "J45", "en": "Asthma", "ar": "الربو"},
        {"code": "K35", "en": "Acute Appendicitis", "ar": "التهاب الزائدة الدودية الحاد"},
        {"code": "C34", "en": "Malignant Neoplasm of Bronchus and Lung", "ar": "ورم خبيث في القصبات والرئة"},
        {"code": "G43", "en": "Migraine", "ar": "الشقيقة (الصداع النصفي)"}
    ]

    inserted = 0
    for item in oms_arabic_dataset:
        sigle = item["code"]
        en_name = item["en"]
        ar_name = item["ar"]

        # 1. Insertion du Terme
        cursor.execute("INSERT OR IGNORE INTO Termes (uuid, sigle, langue_origine, pays_origine) VALUES (?, ?, 'EN', 'WHO')", 
                       (str(uuid.uuid4()), sigle))
        terme_id = cursor.execute("SELECT id FROM Termes WHERE sigle=?", (sigle,)).fetchone()[0]

        # 2. Insertion de la Signification (L'Arabe est la définition courte principale)
        cursor.execute("""INSERT INTO Significations (terme_id, terme_developpe, definition_courte, definition_longue, niveau) 
                          VALUES (?, ?, ?, ?, ?)""", (terme_id, en_name, ar_name, f"تصنيف الأمراض الدولي (ICD-10): {en_name}", 'Expert'))
        sig_id = cursor.lastrowid

        # 3. Liaison Domaine Médical (ID 2)
        cursor.execute("INSERT OR IGNORE INTO Signification_Domaines (signification_id, domaine_id) VALUES (?, 2)", (sig_id,))
        
        # 4. Ajout Traduction Française
        cursor.execute("""INSERT OR IGNORE INTO Traductions (signification_id, langue_id, terme_developpe_tr, definition_tr) 
                          VALUES (?, 1, ?, ?)""", (sig_id, en_name, f"Classification CIM-10: {en_name}"))

        inserted += 1

    conn.commit()
    conn.close()
    print(f"✅ ETL Terminé : {inserted} entrées médicales officielles arabes injectées.")

if __name__ == "__main__":
    ingest_who_medical_data()