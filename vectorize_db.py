import sqlite3
import chromadb
from sentence_transformers import SentenceTransformer

def vectorize_database():
    print("🔄 Chargement du modèle IA multilingue (Cela peut prendre quelques minutes la première fois)...")
    # Modèle léger et ultra-rapide, comprenant l'Arabe, Français, Anglais
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    
    print("🗄️ Connexion à ChromaDB...")
    chroma_client = chromadb.PersistentClient(path="./chroma_data")
    # Supprimer l'ancienne collection si on relance le script pour mettre à jour
    try:
        chroma_client.delete_collection(name="lexique_semantique")
    except:
        pass
        
    collection = chroma_client.get_or_create_collection(name="lexique_semantique")
    
    conn = sqlite3.connect('lexicon_ultimate.db')
    cursor = conn.cursor()
    
    print("📊 Extraction des données SQLite...")
    cursor.execute("""
        SELECT s.id, s.terme_developpe, s.definition_courte, t.sigle 
        FROM Significations s JOIN Termes t ON s.terme_id = t.id
    """)
    rows = cursor.fetchall()
    
    ids = []
    documents = []
    metadatas = []
    
    for row in rows:
        sig_id, terme, def_ar, sigle = row
        # On combine le terme développé et la définition arabe pour un vecteur riche
        text_to_vectorize = f"{terme}. {def_ar}" if def_ar else terme
        
        ids.append(str(sig_id))
        documents.append(text_to_vectorize)
        metadatas.append({"sigle": sigle})
        
    print(f"🧠 Génération des embeddings pour {len(documents)} entrées...")
    embeddings = model.encode(documents, show_progress_bar=True).tolist()
    
    print("💾 Injection dans ChromaDB...")
    # Injection par batch de 1000 pour éviter les surcharges mémoire
    batch_size = 1000
    for i in range(0, len(ids), batch_size):
        end = i + batch_size
        collection.upsert(
            ids=ids[i:end],
            embeddings=embeddings[i:end],
            documents=documents[i:end],
            metadatas=metadatas[i:end]
        )
    
    conn.close()
    print(f"✅ Vectorisation terminée ! {len(ids)} vecteurs stockés dans ChromaDB.")

if __name__ == "__main__":
    vectorize_database()