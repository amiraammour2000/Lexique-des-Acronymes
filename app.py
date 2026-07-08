import streamlit as st
import sqlite3

# --- GESTION ROBUSTE DE L'IA ---
AI_ENABLED = True
try:
    import chromadb
    from sentence_transformers import SentenceTransformer
except Exception:
    AI_ENABLED = False

# --- CONFIGURATION ---
st.set_page_config(page_title="الموسوعة العالمية للاختصارات", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;900&display=swap');
    * { font-family: 'Tajawal', sans-serif; }
    .stApp, .stTextInput, .stSelectbox, .stMarkdown, .stButton, label, .stRadio div { direction: rtl !important; text-align: right !important; }
    
    .encyclopedia-card { background: #fff; border-radius: 15px; padding: 25px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); border-top: 6px solid var(--card-color, #333); margin-bottom: 25px; }
    .header-row { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #f0f0f0; padding-bottom: 10px; margin-bottom: 20px; }
    .main-title { font-size: 40px; font-weight: 900; color: #1a1a1a; }
    .main-term { font-size: 24px; color: var(--card-color); font-weight: 700; }
    .domain-badge { display: inline-block; padding: 5px 12px; border-radius: 20px; font-size: 13px; font-weight: bold; color: white; background: var(--card-color); }
    
    .section-title { font-size: 18px; font-weight: 700; color: #2c3e50; border-right: 4px solid var(--card-color); padding-right: 10px; margin-top: 20px; margin-bottom: 10px;}
    .content-text { font-size: 16px; line-height: 1.8; color: #34495e; }
</style>
""", unsafe_allow_html=True)

# --- INITIALISATION BDD & IA ---
DB_NAME = "lexicon_ultimate.db"

@st.cache_resource
def get_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

@st.cache_resource
def load_semantic_engine():
    if not AI_ENABLED:
        return None, None, "Bibliothèques IA non installées"
    
    try:
        # 1. Charger le modèle
        model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        
        # 2. Se connecter à ChromaDB
        chroma_client = chromadb.PersistentClient(path="./chroma_data")
        
        # 3. Vérifier si la collection existe déjà et est remplie
        try:
            collection = chroma_client.get_collection(name="lexique_semantique")
            if collection.count() > 0:
                return model, collection, None # Tout est prêt !
        except Exception:
            pass # La collection n'existe pas, on va la créer ci-dessous
        
        # 4. SI ON ARRIVE ICI : La base vectorielle est vide ou inexistante. On la génère !
        with st.spinner("🧠 Première initialisation de l'IA sur le cloud (30 secondes)... Cela ne se produira qu'une seule fois !"):
            collection = chroma_client.get_or_create_collection(name="lexique_semantique")
            
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT s.id, s.terme_developpe, s.definition_courte, t.sigle FROM Significations s JOIN Termes t ON s.terme_id = t.id")
            rows = cursor.fetchall()
            
            if rows:
                ids = [str(row[0]) for row in rows]
                documents = [f"{row[1]}. {row[2]}" if row[2] else row[1] for row in rows]
                embeddings = model.encode(documents).tolist()
                collection.upsert(ids=ids, embeddings=embeddings, documents=documents)
        
        return model, collection, None

    except Exception as e:
        return None, None, str(e)

# Chargement de l'IA au démarrage
if AI_ENABLED:
    with st.spinner('⏳ جاري تحميل محرك الذكاء الاصطناعي...'):
        model, collection, ai_error = load_semantic_engine()
        if not model:
            AI_ENABLED = False
            if ai_error:
                st.error(f"❌ Erreur IA: {ai_error}")

# --- FONCTIONS DE RECHERCHE ---
def search_fts(query: str, domain_id: int = None):
    conn = get_db()
    cursor = conn.cursor()
    try:
        fts_query = f"{query}*"
        base_query = """
            SELECT s.id AS sig_id, t.sigle, s.terme_developpe, s.definition_courte, s.definition_longue, 
                   s.niveau, t.langue_origine, t.annee_creation
            FROM Significations s JOIN Termes t ON s.terme_id = t.id
            WHERE s.id IN (SELECT rowid FROM Lexique_FTS WHERE Lexique_FTS MATCH ?)
        """
        params = [fts_query]
        if domain_id:
            base_query += " AND s.id IN (SELECT signification_id FROM Signification_Domaines WHERE domaine_id = ?)"
            params.append(domain_id)
        cursor.execute(base_query, params)
        results = [dict(row) for row in cursor.fetchall()]
        if results:
            return results
    except Exception:
        pass

    # PLAN B : Recherche SQL classique (LIKE)
    base_query = """
        SELECT s.id AS sig_id, t.sigle, s.terme_developpe, s.definition_courte, s.definition_longue, 
               s.niveau, t.langue_origine, t.annee_creation
        FROM Significations s JOIN Termes t ON s.terme_id = t.id
        WHERE (t.sigle LIKE ? OR s.terme_developpe LIKE ? OR s.definition_courte LIKE ?)
    """
    like_param = f"%{query}%"
    params = [like_param, like_param, like_param]
    if domain_id:
        base_query += " AND s.id IN (SELECT signification_id FROM Signification_Domaines WHERE domaine_id = ?)"
        params.append(domain_id)
    cursor.execute(base_query, params)
    return [dict(row) for row in cursor.fetchall()]

def semantic_search(query: str, top_k=5):
    if not AI_ENABLED:
        return []
    try:
        query_embedding = model.encode([query]).tolist()
        results = collection.query(query_embeddings=query_embedding, n_results=top_k)
        return [int(id_str) for id_str in results['ids'][0]]
    except Exception:
        return []

def get_rich_data(sig_ids: list):
    conn = get_db()
    cursor = conn.cursor()
    placeholders = ','.join(['?']*len(sig_ids))
    
    cursor.execute(f"""SELECT sd.signification_id, d.nom_arabe, d.icon, d.couleur 
                       FROM Signification_Domaines sd JOIN Domaines d ON sd.domaine_id = d.id 
                       WHERE sd.signification_id IN ({placeholders})""", sig_ids)
    domains = {}
    for row in cursor.fetchall():
        domains.setdefault(row[0], []).append(dict(nom_arabe=row[1], icon=row[2], couleur=row[3]))
    
    cursor.execute(f"""SELECT t.signification_id, t.terme_developpe_tr, t.definition_tr 
                       FROM Traductions t WHERE t.langue_id=1 AND t.signification_id IN ({placeholders})""", sig_ids)
    translations = {}
    for row in cursor.fetchall():
        translations.setdefault(row[0], []).append(dict(terme=row[1], def_tr=row[2]))
        
    return {"domains": domains, "translations": translations}

# --- INTERFACE UTILISATEUR ---
st.markdown("<h1 style='text-align: center;'>🌐 الموسوعة العالمية للاختصارات والمصطلحات</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #27AE60;'>✅ مركز الغات</p>", unsafe_allow_html=True)

if AI_ENABLED:
    st.markdown("<p style='text-align: center; color: #27AE60;'>✅ بحث هجين نشط: دقيق (SQL) + دلالي بالذكاء الاصطناعي (ChromaDB)</p>", unsafe_allow_html=True)
else:
    st.markdown("<p style='text-align: center; color: #E67E22;'>⚠️ وضع SQL نشط فقط (الذكاء الاصطناعي معطل بواسطة أمان Windows)</p>", unsafe_allow_html=True)

# Sélection du domaine par cartes
if 'selected_domain' not in st.session_state:
    st.session_state.selected_domain = None

conn = get_db()
cursor = conn.cursor()
cursor.execute("SELECT id, nom_arabe, icon, couleur FROM Domaines")
db_domains = [dict(row) for row in cursor.fetchall()]

cols = st.columns(5)
for i, d in enumerate(db_domains):
    with cols[i % 5]:
        if st.button(f"{d['icon']} {d['nom_arabe']}", key=f"d_{d['id']}", use_container_width=True):
            st.session_state.selected_domain = d['id'] if st.session_state.selected_domain != d['id'] else None

st.markdown("---")

# Barre de recherche
search_value = st.text_input("🔍 ابحث عن اختصار، مرض، أو تقنية...", placeholder="مثال: ارتفاع ضغط الدم، GDPR، SAST")

if search_value:
    domain_id = st.session_state.selected_domain
    
    # 1. RECHERCHE EXACTE (FTS5)
    fts_results = search_fts(search_value, domain_id)
    
    if fts_results:
        st.success(f"✅ نتائج البحث الدقيق (SQL FTS5): {len(fts_results)} وجدت")
        sig_ids = [r['sig_id'] for r in fts_results]
        rich_data = get_rich_data(sig_ids)
        
        for row in fts_results:
            dom = rich_data["domains"].get(row['sig_id'], [{}])[0]
            color = dom.get('couleur', '#333')
            icon = dom.get('icon', '📄')
            dom_name = dom.get('nom_arabe', 'غير مصنف')
            
            st.markdown(f"""
            <div class="encyclopedia-card" style="--card-color: {color}">
                <div class="header-row">
                    <div>
                        <div class="main-title">{row['sigle']}</div>
                        <div class="main-term">{row['terme_developpe']}</div>
                    </div>
                    <div style="text-align: left;">
                        <div style="font-size:30px;">{icon}</div>
                        <div class="domain-badge">{dom_name}</div>
                    </div>
                </div>
                <div class="section-title">📖 التعريف</div>
                <div class="content-text">{row['definition_longue'] or row['definition_courte']}</div>
                {"<div class='section-title'>🇫🇷 الترجمة الفرنسية</div><div class='content-text'>"+ rich_data['translations'].get(row['sig_id'], [{}])[0].get('def_tr','') +"</div>" if rich_data['translations'].get(row['sig_id']) else ""}
            </div>
            """, unsafe_allow_html=True)
    
    elif not AI_ENABLED:
        st.error("🚫 لا توجد نتائج دقيقة لهذا البحث، والبحث بالذكاء الاصطناعي معطل حالياً على جهازك.")
        
    else:
        # 2. RECHERCHE SÉMANTIQUE (IA ChromaDB)
        st.info("🧪 لم يتم العثور على تطابق دقيق. البحث بالمعنى عبر الذكاء الاصطناعي...")
        try:
            semantic_ids = semantic_search(search_value)
            if semantic_ids:
                placeholders = ','.join(['?']*len(semantic_ids))
                cursor = get_db().cursor()
                cursor.execute(f"""SELECT s.id AS sig_id, t.sigle, s.terme_developpe, s.definition_courte, s.definition_longue 
                                   FROM Significations s JOIN Termes t ON s.terme_id = t.id 
                                   WHERE s.id IN ({placeholders})""", semantic_ids)
                ai_results = [dict(row) for row in cursor.fetchall()]
                rich_data = get_rich_data(semantic_ids)
                
                st.success(f"🧠 نتائج البحث الدلالي (IA): {len(ai_results)} وجدت")
                for row in ai_results:
                    dom = rich_data["domains"].get(row['sig_id'], [{}])[0]
                    color = dom.get('couleur', '#9b59b6')
                    st.markdown(f"""
                    <div class="encyclopedia-card" style="--card-color: {color}">
                        <div class="header-row">
                            <div>
                                <div class="main-title">{row['sigle']}</div>
                                <div class="main-term">{row['terme_developpe']}</div>
                            </div>
                            <div style="text-align: left;">
                                <div class="domain-badge" style="background:#9b59b6;">اقتراح الذكاء الاصطناعي</div>
                            </div>
                        </div>
                        <div class="content-text">{row['definition_longue'] or row['definition_courte']}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.error("🚫 لا توجد نتائج حتى بالبحث الدلالي.")
        except Exception as e:
            st.error(f"Erreur IA : {str(e)}")
