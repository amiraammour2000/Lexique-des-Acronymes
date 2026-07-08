PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

-- ==============================================================
-- TABLES PRINCIPALES
-- ==============================================================
CREATE TABLE IF NOT EXISTS Termes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE,
    sigle TEXT NOT NULL,
    langue_origine TEXT DEFAULT 'EN',
    pays_origine TEXT,
    annee_creation INTEGER,
    statut TEXT DEFAULT 'Actif'
);

CREATE TABLE IF NOT EXISTS Significations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    terme_id INTEGER NOT NULL,
    terme_developpe TEXT NOT NULL,
    definition_courte TEXT,
    definition_longue TEXT,
    definition_scientifique TEXT,
    niveau TEXT,
    validateur TEXT,
    date_creation DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (terme_id) REFERENCES Termes(id)
);

-- ==============================================================
-- DOMAINES (Les 10 piliers)
-- ==============================================================
CREATE TABLE IF NOT EXISTS Domaines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom_arabe TEXT UNIQUE,
    nom_francais TEXT UNIQUE,
    nom_anglais TEXT UNIQUE,
    icon TEXT,
    couleur TEXT,
    description TEXT
);

CREATE TABLE IF NOT EXISTS Signification_Domaines (
    signification_id INTEGER NOT NULL,
    domaine_id INTEGER NOT NULL,
    PRIMARY KEY (signification_id, domaine_id)
);

-- ==============================================================
-- TRADUCTIONS, NORMES, IA, STATS
-- ==============================================================
CREATE TABLE IF NOT EXISTS Langues (id INTEGER PRIMARY KEY, code TEXT UNIQUE, nom TEXT);
INSERT OR IGNORE INTO Langues (code, nom) VALUES ('fr', 'Français'), ('en', 'Anglais');

CREATE TABLE IF NOT EXISTS Traductions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signification_id INTEGER NOT NULL,
    langue_id INTEGER NOT NULL,
    terme_developpe_tr TEXT,
    definition_tr TEXT,
    exemple_utilisation_tr TEXT,
    FOREIGN KEY (signification_id) REFERENCES Significations(id),
    FOREIGN KEY (langue_id) REFERENCES Langues(id)
);

CREATE TABLE IF NOT EXISTS Organisations (id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT UNIQUE, type TEXT);
INSERT OR IGNORE INTO Organisations (nom, type) VALUES ('ISO', 'Standard'), ('OMS', 'Médical'), ('OTAN', 'Militaire'), ('IETF', 'Standard');

CREATE TABLE IF NOT EXISTS Normes_References (id INTEGER PRIMARY KEY AUTOINCREMENT, code_norme TEXT UNIQUE, organisation_id INTEGER);
INSERT OR IGNORE INTO Normes_References (code_norme, organisation_id) VALUES ('ISO 27001', 1), ('ICD-10', 2), ('STANAG', 3), ('RFC 7231', 4);

CREATE TABLE IF NOT EXISTS Signification_Normes (signification_id INTEGER NOT NULL, norme_id INTEGER NOT NULL, PRIMARY KEY (signification_id, norme_id));

CREATE TABLE IF NOT EXISTS IA_Metadata (signification_id INTEGER PRIMARY KEY, mots_cles TEXT, resume_ia TEXT);
CREATE TABLE IF NOT EXISTS Statistiques (signification_id INTEGER PRIMARY KEY, vues INTEGER DEFAULT 0, score_qualite REAL DEFAULT 0.0);

-- ==============================================================
-- INDEXATION FTS5 (CORRIGÉ : content et content_rowid)
-- ==============================================================
CREATE VIRTUAL TABLE IF NOT EXISTS Lexique_FTS USING fts5(
    sigle, terme_developpe, definition_courte, mots_cles, 
    content='Significations', content_rowid='id', tokenize="porter unicode61"
);

CREATE TRIGGER fts_insert AFTER INSERT ON Significations BEGIN
    INSERT INTO Lexique_FTS(rowid, sigle, terme_developpe, definition_courte, mots_cles) 
    VALUES (new.id, (SELECT sigle FROM Termes WHERE id=new.terme_id), new.terme_developpe, new.definition_courte, (SELECT mots_cles FROM IA_Metadata WHERE signification_id=new.id));
END;

-- ==============================================================
-- PEUPLEMENT INITIAL DES 10 DOMAINES
-- ==============================================================
INSERT INTO Domaines (id, nom_arabe, nom_francais, nom_anglais, icon, couleur, description) VALUES 
(1, 'الطاقة والهندسة', 'Energie et Ingenierie', 'Energy and Engineering', '⚡', '#E67E22', 'اختصارات ومصطلحات متعلقة بصناعة الطاقة والهندسة.'),
(2, 'الصحة والطب', 'Sante et Medecine', 'Health and Medicine', '🏥', '#E74C3C', 'مصطلحات طبية واختصارات سريرية وتشخيصية.'),
(3, 'تكنولوجيا المعلومات', 'Technologies de l Information', 'Information Technology', '💻', '#3498DB', 'اختصارات البرمجة والشبكات والأمن السيبراني.'),
(4, 'المالية والأعمال', 'Finance et Affaires', 'Finance and Business', '💰', '#27AE60', 'مصطلحات مالية ومحاسبية واستثمارية.'),
(5, 'الدفاع والأمن', 'Defense et Securite', 'Defense and Security', '🛡️', '#8E44AD', 'اختصارات عسكرية واستخباراتية.'),
(6, 'البيئة والزراعة', 'Environnement et Agriculture', 'Environment and Agriculture', '🌱', '#16A085', 'مصطلحات بيئية ومناخية.'),
(7, 'التعليم والبحث', 'Education et Recherche', 'Education and Research', '🎓', '#2980B9', 'اختصارات أكاديمية وبحثية.'),
(8, 'القانون والحوكمة', 'Droit et Gouvernance', 'Law and Governance', '⚖️', '#C0392B', 'مصطلحات قانونية وتشريعية دولية.'),
(9, 'النقل واللوجستيك', 'Transport et Logistique', 'Transport and Logistics', '🚛', '#D35400', 'اختصارات النقل واللوجستيك العالمي.'),
(10, 'الفضاء والفلك', 'Espace et Astronomie', 'Space and Astronomy', '🚀', '#2C3E50', 'مصطلحات فضائية واستكشاف الكون.');

-- PEUPLEMENT ACRONYMES
INSERT INTO Termes (uuid, sigle, langue_origine, annee_creation) VALUES 
(lower(hex(randomblob(4))), 'SCADA', 'EN', 1965), 
(lower(hex(randomblob(4))), 'COPD', 'EN', 1959), 
(lower(hex(randomblob(4))), 'SAST', 'EN', 2000), 
(lower(hex(randomblob(4))), 'EBITDA', 'EN', 1970), 
(lower(hex(randomblob(4))), 'SIGINT', 'EN', 1940), 
(lower(hex(randomblob(4))), 'GDPR', 'EN', 2016), 
(lower(hex(randomblob(4))), 'TEU', 'EN', 1960), 
(lower(hex(randomblob(4))), 'LEO', 'EN', 1960);

INSERT INTO Significations (terme_id, terme_developpe, definition_courte, definition_longue, niveau) VALUES 
(1, 'Supervisory Control and Data Acquisition', 'التحكم الإشرافي واكتساب البيانات', 'نظام للمراقبة والتحكم الصناعي.', 'Expert'),
(2, 'Chronic Obstructive Pulmonary Disease', 'مرض الانسداد الرئوي المزمن', 'مرض رئوي التهابي مزمن يسبب انسداداً مستمراً.', 'Avancé'),
(3, 'Static Application Security Testing', 'اختبار أمان التطبيقات الثابت', 'فحص شفرة المصدر للكشف عن الثغرات الأمنية.', 'Avancé'),
(4, 'Earnings Before Interest, Taxes, Depreciation, and Amortization', 'الأرباح قبل الفوائد والضرائب', 'مقياس مالي يقيس الأداء التشغيلي.', 'Intermédiaire'),
(5, 'Signals Intelligence', 'استخبارات الإشارات', 'جمع وتحليل الإشارات الأجنبية.', 'Expert'),
(6, 'General Data Protection Regulation', 'اللائحة العامة لحماية البيانات', 'لائحة حول حماية البيانات والخصوصية.', 'Intermédiaire'),
(7, 'Twenty-foot Equivalent Unit', 'وحدة مكافئة لعشرين قدماً', 'وحدة قياس لسعة حمولة حاويات الشحن.', 'Débutant'),
(8, 'Low Earth Orbit', 'مدار أرضي منخفض', 'مدار مركزية الأرض بارتفاع يتراوح بين 160 إلى 2000 كيلومتر.', 'Intermédiaire');

INSERT INTO Signification_Domaines VALUES (1,1), (2,2), (3,3), (4,4), (5,5), (6,8), (7,9), (8,10);
INSERT INTO Traductions (signification_id, langue_id, terme_developpe_tr, definition_tr) VALUES 
(1, 1, 'Supervision et Acquisition de Données', 'Système de contrôle industriel.'), 
(6, 1, 'RGPD', 'Règlement européen sur la confidentialité.');
INSERT INTO IA_Metadata (signification_id, mots_cles, resume_ia) VALUES 
(1, 'scada, iot, energy', 'Système nerveux central des infrastructures critiques.'),
(3, 'security, devsecops', 'Analyse statique du code source pour les vulnérabilités.');