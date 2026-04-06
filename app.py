import streamlit as st
import sqlite3
import hashlib
import os
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance, ImageOps
import io
from datetime import date, timedelta
import calendar
import shutil

# ============================================================
# CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="Cabinet Traumatologie & Orthopédie",
    page_icon="🦴",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Utiliser un fichier temporaire sur Streamlit Cloud (ou local)
# Sur votre PC en local, vous pouvez mettre un chemin fixe comme "~/Documents/cabinet.db"
DB_PATH = "/tmp/cabinet.db"

# ============================================================
# FONCTIONS DE SAUVEGARDE / RESTAURATION
# ============================================================
def export_db():
    """Retourne le contenu du fichier DB pour téléchargement."""
    if os.path.exists(DB_PATH):
        with open(DB_PATH, "rb") as f:
            return f.read()
    else:
        return None

def import_db(uploaded_file):
    """Remplace la base actuelle par le fichier uploadé."""
    if uploaded_file is not None:
        # Sauvegarder l'ancienne base (au cas où)
        if os.path.exists(DB_PATH):
            shutil.copy(DB_PATH, DB_PATH + ".old")
        # Écrire le nouveau fichier
        with open(DB_PATH, "wb") as f:
            f.write(uploaded_file.getbuffer())
        # Recréer les tables si nécessaire (elles sont déjà dans le fichier)
        # On force la réinitialisation de la connexion
        st.success("✅ Base restaurée avec succès ! Redémarrage...")
        st.rerun()

# ============================================================
# CSS GLOBAL
# ============================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
* { font-family: 'Inter', sans-serif; }

.main-header {
    background: linear-gradient(135deg, #1a3a5c 0%, #2d6a9f 100%);
    padding: 1.5rem 2rem; border-radius: 12px;
    margin-bottom: 1.5rem; color: white;
    display: flex; align-items: center; gap: 1rem;
}
.main-header h1 { margin: 0; font-size: 1.6rem; font-weight: 700; }
.main-header p  { margin: 0; font-size: 0.85rem; opacity: 0.85; }
.role-badge {
    background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.3);
    padding: 0.3rem 0.8rem; border-radius: 20px;
    font-size: 0.75rem; font-weight: 600; margin-left: auto;
}
.card {
    background: white; border: 1px solid #e5e7eb;
    border-radius: 12px; padding: 1.5rem;
    margin-bottom: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.stat-card {
    background: linear-gradient(135deg, #1a3a5c, #2d6a9f);
    color: white; border-radius: 12px; padding: 1.2rem; text-align: center;
}
.stat-card .number { font-size: 2rem; font-weight: 700; }
.stat-card .label  { font-size: 0.8rem; opacity: 0.85; margin-top: 0.2rem; }
.stat-card.green  { background: linear-gradient(135deg, #065f46, #059669); }
.stat-card.orange { background: linear-gradient(135deg, #92400e, #d97706); }
.stat-card.purple { background: linear-gradient(135deg, #4c1d95, #7c3aed); }
.badge { display:inline-block; padding:0.2rem 0.6rem; border-radius:20px; font-size:0.72rem; font-weight:600; }
.badge-blue   { background:#dbeafe; color:#1d4ed8; }
.badge-green  { background:#d1fae5; color:#065f46; }
.badge-red    { background:#fee2e2; color:#991b1b; }
.badge-orange { background:#ffedd5; color:#9a3412; }
.badge-gray   { background:#f3f4f6; color:#374151; }
.rdv-card {
    border-left: 4px solid #2d6a9f; background: #f8fafc;
    padding: 0.8rem 1rem; border-radius: 0 8px 8px 0; margin-bottom: 0.5rem;
}
.section-title {
    font-size: 1.1rem; font-weight: 600; color: #1a3a5c;
    border-bottom: 2px solid #dbeafe; padding-bottom: 0.5rem; margin-bottom: 1rem;
}
.alert-box { padding: 0.8rem 1rem; border-radius: 8px; margin-bottom: 0.8rem; font-size: 0.9rem; }
.alert-info    { background:#dbeafe; border-left:4px solid #2563eb; color:#1e40af; }
.alert-success { background:#d1fae5; border-left:4px solid #059669; color:#065f46; }
.alert-warning { background:#fef3c7; border-left:4px solid #d97706; color:#92400e; }
div[data-testid="stSidebarNav"] { display: none; }
.stButton > button { border-radius: 8px; font-weight: 500; transition: all 0.2s; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# DATABASE
# ============================================================
def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL, password TEXT NOT NULL,
        role TEXT NOT NULL, full_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

    c.execute("""CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL, prenom TEXT NOT NULL,
        date_naissance TEXT, sexe TEXT, telephone TEXT,
        adresse TEXT, mutuelle TEXT, num_securite_sociale TEXT,
        antecedents TEXT, allergies TEXT, groupe_sanguin TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, created_by TEXT)""")

    c.execute("""CREATE TABLE IF NOT EXISTS rendez_vous (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER, date TEXT NOT NULL, heure TEXT NOT NULL,
        motif TEXT, statut TEXT DEFAULT 'planifié', notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(patient_id) REFERENCES patients(id))""")

    c.execute("""CREATE TABLE IF NOT EXISTS consultations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER, date TEXT NOT NULL,
        anamnese TEXT, examen_clinique TEXT, diagnostic TEXT,
        traitement TEXT, notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(patient_id) REFERENCES patients(id))""")

    c.execute("""CREATE TABLE IF NOT EXISTS ordonnances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER, consultation_id INTEGER, date TEXT NOT NULL,
        medicaments TEXT, instructions TEXT, duree TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(patient_id) REFERENCES patients(id))""")

    c.execute("""CREATE TABLE IF NOT EXISTS medicaments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL, dci TEXT, classe TEXT, forme TEXT,
        dosage TEXT, posologie_adulte TEXT, posologie_enfant TEXT,
        contre_indications TEXT, effets_indesirables TEXT,
        prix REAL, stock INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

    c.execute("""CREATE TABLE IF NOT EXISTS recettes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER, consultation_id INTEGER,
        date TEXT NOT NULL, acte TEXT, montant REAL,
        mode_paiement TEXT, paye INTEGER DEFAULT 0, notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(patient_id) REFERENCES patients(id))""")

    conn.commit()

    # Utilisateurs par défaut
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users (username,password,role,full_name) VALUES (?,?,?,?)",
                  ("medecin", hash_password("medecin123"), "medecin", "Dr. Bensalem Karim"))
        c.execute("INSERT INTO users (username,password,role,full_name) VALUES (?,?,?,?)",
                  ("secretaire", hash_password("secret123"), "secretaire", "Mme. Boudali Nadia"))
        conn.commit()

    # Médicaments par défaut
    c.execute("SELECT COUNT(*) FROM medicaments")
    if c.fetchone()[0] == 0:
        meds = [
            ("Ibuprofène 400mg","Ibuprofène","AINS","Comprimé","400mg",
             "400mg 3x/jour pendant les repas, max 1200mg/j","20-30mg/kg/j en 3 prises",
             "Ulcère gastrique, insuffisance rénale, grossesse T3","Douleurs gastriques, nausées",150.0,50),
            ("Diclofénac 50mg","Diclofénac sodique","AINS","Comprimé","50mg",
             "50mg 2-3x/jour, max 150mg/j","Non recommandé < 14 ans",
             "Insuffisance cardiaque, rénale, ATCD ulcère","Douleurs abdominales, éruption",180.0,40),
            ("Kétoprofène 100mg","Kétoprofène","AINS","Comprimé LP","100mg",
             "100-200mg/j en 1-2 prises, avec repas","Non recommandé < 15 ans",
             "Allergie AINS, ulcère actif","Nausées, photosensibilité",200.0,30),
            ("Célécoxib 200mg","Célécoxib","AINS Cox-2","Gélule","200mg",
             "200mg 1-2x/jour","Non recommandé enfant",
             "Allergie sulfonamides, insuffisance hépatique sévère","Douleurs abdominales, HTA",350.0,25),
            ("Paracétamol 1g","Paracétamol","Antalgique","Comprimé","1g",
             "1g 3-4x/jour, max 4g/j, toutes les 6h min","15mg/kg toutes les 6h",
             "Insuffisance hépatocellulaire","Rares si posologie respectée",80.0,100),
            ("Tramadol 50mg","Tramadol","Opioïde faible","Gélule","50mg",
             "50-100mg 3-4x/jour, max 400mg/j","Non recommandé < 12 ans",
             "Épilepsie non contrôlée, IMAOthérapie","Nausées, constipation, somnolence",220.0,30),
            ("Tramadol LP 100mg","Tramadol","Opioïde faible","Comprimé LP","100mg",
             "100-200mg 2x/jour à 12h d'intervalle","Non recommandé < 18 ans",
             "Épilepsie, dépression respiratoire","Somnolence, vertiges, nausées",280.0,20),
            ("Codéine + Paracétamol","Codéine/Paracétamol","Antalgique pallier 2","Comprimé","30/500mg",
             "1-2 cp 3-4x/jour, max 6 cp/j","Non recommandé < 12 ans",
             "Insuffisance hépatique, asthme, allaitement","Constipation, somnolence",190.0,25),
            ("Méthocarbamol 500mg","Méthocarbamol","Myorelaxant","Comprimé","500mg",
             "1500mg 4x/jour 1ère semaine, puis 750mg 4x/j","Non établi < 16 ans",
             "Épilepsie, myasthénie","Somnolence, vertiges",260.0,20),
            ("Thiocolchicoside 4mg","Thiocolchicoside","Myorelaxant","Comprimé","4mg",
             "4mg 2x/jour, max 7 jours","Non recommandé < 16 ans",
             "Grossesse, troubles convulsifs","Diarrhée, somnolence",300.0,20),
            ("Prednisone 5mg","Prednisone","Corticoïde","Comprimé","5mg",
             "0.5-1mg/kg/j en cure courte","0.5-2mg/kg/j",
             "Infections sévères non traitées","Prise de poids, HTA, hyperglycémie",120.0,40),
            ("Méthylprednisolone 16mg","Méthylprednisolone","Corticoïde","Comprimé","16mg",
             "16-32mg/j en 1-2 prises matin","Variable",
             "Idem prednisone","Idem corticoïdes",250.0,20),
            ("Énoxaparine 4000UI","Énoxaparine sodique","HBPM","Seringue SC","0.4mL",
             "1 inj SC/jour prophylaxie; 100UI/kg 2x/j curatif","Adapté au poids",
             "Hémorragie active, ATCD TIH","Hématome point injection",400.0,30),
            ("Rivaroxaban 10mg","Rivaroxaban","AOD","Comprimé","10mg",
             "10mg 1x/jour après chirurgie orthopédique","Non recommandé < 18 ans",
             "Hémorragie active, grossesse","Saignements, nausées",850.0,20),
            ("Alendronate 70mg","Alendronate sodique","Bisphosphonate","Comprimé","70mg",
             "70mg 1x/semaine à jeun, rester debout 30min","Non utilisé enfant",
             "Hypocalcémie, pathologies œsophagiennes","Douleurs osseuses, musculaires",320.0,15),
            ("Calcium + Vitamine D3","Calcium/Cholécalciférol","Supplément","Comprimé à croquer","1g/800UI",
             "1-2 cp/jour pendant ou après repas","500mg/400UI 1x/j selon âge",
             "Hypercalcémie, calculs rénaux","Constipation, flatulences",180.0,50),
            ("Oméprazole 20mg","Oméprazole","IPP","Gélule","20mg",
             "20mg 1x/jour à jeun, à prendre avec AINS","0.7-1.5mg/kg/j",
             "Allergie aux IPP","Céphalées, diarrhée, nausées",150.0,60),
            ("Pantoprazole 40mg","Pantoprazole","IPP","Comprimé","40mg",
             "40mg 1x/jour à jeun","Non recommandé < 12 ans",
             "Allergie benzimidazoles","Diarrhée, nausées, céphalées",160.0,50),
            ("Amoxicilline 1g","Amoxicilline","Antibiotique","Comprimé","1g",
             "1g 3x/jour 7-10 jours","50mg/kg/j en 3 prises",
             "Allergie pénicilline, mononucléose","Diarrhée, éruption, nausées",200.0,30),
            ("Amoxicilline/Ac.clavulanique 1g","Amoxicilline+Ac.clavulanique","Antibiotique","Comprimé","1g",
             "1g 3x/jour 7-10 jours","25-45mg/kg/j en 3 prises",
             "Allergie pénicilline, ictère cholestatique","Diarrhée, nausées, candidose",350.0,25),
            ("Ciprofloxacine 500mg","Ciprofloxacine","Fluoroquinolone","Comprimé","500mg",
             "500-750mg 2x/jour 7-10 jours","Non recommandé < 18 ans",
             "Grossesse, épilepsie, déficit G6PD","Tendinopathies, photosensibilité",280.0,20),
            ("Alpha-amylase 6000UI","Alpha-amylase","Antioedémateux","Comprimé","6000UI",
             "3 cp 3x/jour phase aiguë, puis 2 cp 3x/j","Adapté",
             "Allergie aux enzymes","Diarrhées légères",220.0,25),
            ("Diclofénac gel 1%","Diclofénac diéthylamine","AINS topique","Gel","1%",
             "4g 3-4x/jour sur zone douloureuse, masser doucement","Non recommandé < 14 ans",
             "Peau lésée, dermatose, grossesse T3","Prurit local, éruption",250.0,20),
            ("Kétoprofène gel 2.5%","Kétoprofène","AINS topique","Gel","2.5%",
             "2g 1-2x/jour, éviter exposition soleil","Non recommandé < 15 ans",
             "Exposition solaire, peau lésée","Photosensibilité, prurit",230.0,15),
        ]
        c.executemany("""INSERT INTO medicaments
            (nom,dci,classe,forme,dosage,posologie_adulte,posologie_enfant,
             contre_indications,effets_indesirables,prix,stock)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""", meds)
        conn.commit()
    conn.close()


# ============================================================
# AUTH
# ============================================================
def page_login():
    st.markdown("""
    <div style='text-align:center; margin-bottom:2rem;'>
        <div style='font-size:3rem;'>🦴</div>
        <h2 style='color:#1a3a5c; margin:0;'>Cabinet Médical</h2>
        <p style='color:#6b7280; font-size:0.9rem;'>Traumatologie & Orthopédie</p>
    </div>""", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container():
            st.markdown("### 🔐 Connexion")
            username = st.text_input("Identifiant", placeholder="Votre identifiant")
            password = st.text_input("Mot de passe", type="password", placeholder="••••••••")
            if st.button("Se connecter", use_container_width=True, type="primary"):
                if username and password:
                    conn = get_connection()
                    c = conn.cursor()
                    c.execute("SELECT * FROM users WHERE username=? AND password=?",
                              (username, hash_password(password)))
                    user = c.fetchone()
                    conn.close()
                    if user:
                        st.session_state.logged_in  = True
                        st.session_state.role       = user["role"]
                        st.session_state.username   = username
                        st.session_state.full_name  = user["full_name"]
                        st.rerun()
                    else:
                        st.error("Identifiant ou mot de passe incorrect")
                else:
                    st.warning("Veuillez remplir tous les champs")
            st.markdown("""
            <div style='text-align:center;margin-top:1rem;font-size:0.78rem;color:#9ca3af;'>
                <b>Médecin:</b> medecin / medecin123 &nbsp;|&nbsp;
                <b>Secrétaire:</b> secretaire / secret123
            </div>""", unsafe_allow_html=True)


# ============================================================
# PAGE : ACCUEIL / DASHBOARD
# ============================================================
def page_accueil():
    role = st.session_state.role
    name = st.session_state.full_name
    st.markdown(f"""
    <div class='main-header'>
        <div style='font-size:2rem;'>🦴</div>
        <div>
            <h1>{'Tableau de Bord' if role=='medecin' else 'Accueil Secrétariat'}</h1>
            <p>Bonjour, {name} · {date.today().strftime('%A %d %B %Y')}</p>
        </div>
        <div class='role-badge'>{'👨‍⚕️ Médecin' if role=='medecin' else '👩‍💼 Secrétaire'}</div>
    </div>""", unsafe_allow_html=True)

    conn = get_connection(); c = conn.cursor()
    today = date.today().isoformat()

    c.execute("SELECT COUNT(*) FROM patients"); total_patients = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM rendez_vous WHERE date=?", (today,)); rdv_today = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM rendez_vous WHERE statut='planifié' AND date>=?", (today,)); rdv_plan = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(montant),0) FROM recettes WHERE date=? AND paye=1", (today,)); recette = c.fetchone()[0]

    col1,col2,col3,col4 = st.columns(4)
    with col1: st.markdown(f"<div class='stat-card'><div class='number'>{total_patients}</div><div class='label'>👤 Patients enregistrés</div></div>", unsafe_allow_html=True)
    with col2: st.markdown(f"<div class='stat-card green'><div class='number'>{rdv_today}</div><div class='label'>📅 RDV aujourd'hui</div></div>", unsafe_allow_html=True)
    with col3: st.markdown(f"<div class='stat-card orange'><div class='number'>{rdv_plan}</div><div class='label'>⏳ RDV à venir</div></div>", unsafe_allow_html=True)
    with col4: st.markdown(f"<div class='stat-card purple'><div class='number'>{recette:,.0f} DA</div><div class='label'>💰 Recette du jour</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_l, col_r = st.columns([3, 2])

    with col_l:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>📅 Rendez-vous du jour</div>", unsafe_allow_html=True)
        c.execute("""SELECT r.heure,r.motif,r.statut,p.nom,p.prenom,p.telephone
                     FROM rendez_vous r JOIN patients p ON r.patient_id=p.id
                     WHERE r.date=? ORDER BY r.heure""", (today,))
        rdvs = c.fetchall()
        if rdvs:
            for rdv in rdvs:
                sc = {"planifié":"badge-blue","en cours":"badge-orange","terminé":"badge-green","annulé":"badge-red"}.get(rdv["statut"],"badge-gray")
                st.markdown(f"""<div class='rdv-card'>
                    <b>🕐 {rdv['heure']}</b> — <b>{rdv['prenom']} {rdv['nom']}</b>
                    <span class='badge {sc}'>{rdv['statut']}</span><br>
                    <span style='font-size:0.82rem;color:#374151;'>📌 {rdv['motif'] or '—'} | 📞 {rdv['telephone'] or '—'}</span>
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown("<div class='alert-info alert-box'>Aucun rendez-vous programmé pour aujourd'hui.</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_r:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>🆕 Derniers patients</div>", unsafe_allow_html=True)
        c.execute("SELECT nom,prenom,date_naissance FROM patients ORDER BY created_at DESC LIMIT 6")
        for p in c.fetchall():
            st.markdown(f"<div style='padding:0.5rem 0;border-bottom:1px solid #f3f4f6;'><b>👤 {p['prenom']} {p['nom']}</b><br><span style='font-size:0.78rem;color:#6b7280;'>Né(e) le {p['date_naissance'] or '—'}</span></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        if role == "medecin":
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown("<div class='section-title'>💊 Stock faible</div>", unsafe_allow_html=True)
            c.execute("SELECT nom,stock FROM medicaments WHERE stock<10 ORDER BY stock LIMIT 5")
            faibles = c.fetchall()
            if faibles:
                for m in faibles:
                    col = "#fee2e2" if m["stock"]<5 else "#fef3c7"
                    st.markdown(f"<div style='background:{col};padding:0.4rem 0.8rem;border-radius:6px;margin-bottom:0.3rem;font-size:0.85rem;'>💊 {m['nom']} — <b>{m['stock']} unités</b></div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='alert-success alert-box'>✅ Tous les stocks sont suffisants.</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
    conn.close()


# ============================================================
# PAGE : PATIENTS
# ============================================================
def page_patients():
    st.markdown("<div class='main-header'><div style='font-size:2rem;'>👤</div><div><h1>Gestion des Patients</h1><p>Enregistrement et suivi des dossiers patients</p></div></div>", unsafe_allow_html=True)
    tab1, tab2, tab3 = st.tabs(["📋 Liste des patients", "➕ Nouveau patient", "🔍 Dossier patient"])
    conn = get_connection(); c = conn.cursor()

    with tab1:
        col_s, col_f = st.columns([3,1])
        with col_s: search = st.text_input("🔍 Rechercher (nom, prénom, téléphone)", placeholder="Tapez pour rechercher...")
        with col_f: sf = st.selectbox("Sexe", ["Tous","Masculin","Féminin"])
        q = "SELECT * FROM patients WHERE 1=1"; p = []
        if search: q += " AND (nom LIKE ? OR prenom LIKE ? OR telephone LIKE ?)"; p += [f"%{search}%"]*3
        if sf != "Tous": q += " AND sexe=?"; p.append(sf)
        c.execute(q + " ORDER BY created_at DESC", p)
        patients = c.fetchall()
        st.markdown(f"<p style='color:#6b7280;font-size:0.85rem;'>{len(patients)} patient(s)</p>", unsafe_allow_html=True)
        for pat in patients:
            with st.expander(f"👤 {pat['prenom']} {pat['nom']} — {pat['telephone'] or 'N° non renseigné'}"):
                c1,c2,c3 = st.columns(3)
                with c1:
                    st.write(f"**Naissance:** {pat['date_naissance'] or '—'}")
                    st.write(f"**Sexe:** {pat['sexe'] or '—'}")
                    st.write(f"**Groupe sanguin:** {pat['groupe_sanguin'] or '—'}")
                with c2:
                    st.write(f"**Téléphone:** {pat['telephone'] or '—'}")
                    st.write(f"**Adresse:** {pat['adresse'] or '—'}")
                    st.write(f"**Mutuelle:** {pat['mutuelle'] or '—'}")
                with c3:
                    st.write(f"**N° SS:** {pat['num_securite_sociale'] or '—'}")
                    st.write(f"**Allergies:** {pat['allergies'] or 'Aucune connue'}")
                    st.write(f"**Antécédents:** {pat['antecedents'] or '—'}")
                b1,b2 = st.columns(2)
                with b1:
                    if st.button("📅 Prendre RDV", key=f"rdv_{pat['id']}"):
                        st.session_state.rdv_patient_id = pat['id']
                        st.session_state.current_page = "rendez_vous"; st.rerun()
                with b2:
                    if st.session_state.role == "medecin":
                        if st.button("📋 Consulter", key=f"cons_{pat['id']}"):
                            st.session_state.consult_patient_id = pat['id']
                            st.session_state.current_page = "ordonnances"; st.rerun()

    with tab2:
        st.markdown("<div class='section-title'>➕ Nouveau patient</div>", unsafe_allow_html=True)
        c1,c2 = st.columns(2)
        with c1:
            nom    = st.text_input("Nom *")
            prenom = st.text_input("Prénom *")
            dob    = st.date_input("Date de naissance", value=None, min_value=date(1920,1,1), max_value=date.today())
            sexe   = st.selectbox("Sexe", ["","Masculin","Féminin"])
            gs     = st.selectbox("Groupe sanguin", ["","A+","A-","B+","B-","AB+","AB-","O+","O-"])
        with c2:
            tel    = st.text_input("Téléphone")
            adr    = st.text_area("Adresse", height=68)
            mut    = st.text_input("Mutuelle / Assurance")
            nss    = st.text_input("N° Sécurité Sociale")
        ant  = st.text_area("Antécédents médicaux", height=80)
        all_ = st.text_area("Allergies connues", height=80)
        if st.button("💾 Enregistrer le patient", type="primary"):
            if nom and prenom:
                c.execute("""INSERT INTO patients
                    (nom,prenom,date_naissance,sexe,telephone,adresse,mutuelle,
                     num_securite_sociale,antecedents,allergies,groupe_sanguin,created_by)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (nom.upper(),prenom,str(dob) if dob else None,sexe or None,
                     tel,adr,mut,nss,ant,all_,gs or None,st.session_state.username))
                conn.commit()
                st.success(f"✅ Patient {prenom} {nom.upper()} enregistré !")
                st.rerun()
            else: st.error("⚠️ Nom et prénom obligatoires.")

    with tab3:
        c.execute("SELECT id,nom,prenom FROM patients ORDER BY nom")
        all_p = c.fetchall()
        if all_p:
            opts = {f"{p['prenom']} {p['nom']}": p['id'] for p in all_p}
            sel  = st.selectbox("Sélectionner un patient", list(opts.keys()))
            pid  = opts[sel]
            c.execute("SELECT * FROM patients WHERE id=?", (pid,))
            pat  = c.fetchone()
            if pat:
                c1,c2 = st.columns([2,1])
                with c1:
                    st.markdown(f"""<div class='card'>
                        <div class='section-title'>🪪 Informations</div>
                        <table style='width:100%;'>
                        <tr><td style='color:#6b7280;'>Nom complet</td><td><b>{pat['prenom']} {pat['nom']}</b></td></tr>
                        <tr><td style='color:#6b7280;'>Naissance</td><td>{pat['date_naissance'] or '—'}</td></tr>
                        <tr><td style='color:#6b7280;'>Sexe</td><td>{pat['sexe'] or '—'}</td></tr>
                        <tr><td style='color:#6b7280;'>Groupe sanguin</td><td><b style='color:#dc2626;'>{pat['groupe_sanguin'] or '—'}</b></td></tr>
                        <tr><td style='color:#6b7280;'>Téléphone</td><td>{pat['telephone'] or '—'}</td></tr>
                        <tr><td style='color:#6b7280;'>Mutuelle</td><td>{pat['mutuelle'] or '—'}</td></tr>
                        </table></div>""", unsafe_allow_html=True)
                with c2:
                    st.markdown(f"""<div class='card' style='background:#fef2f2;border-color:#fecaca;'>
                        <div class='section-title' style='color:#dc2626;'>⚠️ Alertes</div>
                        <p style='font-size:0.85rem;'><b>Allergies:</b><br>{pat['allergies'] or 'Aucune connue'}</p>
                        <p style='font-size:0.85rem;'><b>Antécédents:</b><br>{pat['antecedents'] or '—'}</p>
                    </div>""", unsafe_allow_html=True)
                if st.session_state.role == "medecin":
                    st.markdown("<div class='section-title'>📋 Historique consultations</div>", unsafe_allow_html=True)
                    c.execute("SELECT * FROM consultations WHERE patient_id=? ORDER BY date DESC", (pid,))
                    for cons in c.fetchall():
                        with st.expander(f"📋 {cons['date']} — {cons['diagnostic'] or 'Consultation'}"):
                            st.write(f"**Anamnèse:** {cons['anamnese'] or '—'}")
                            st.write(f"**Examen:** {cons['examen_clinique'] or '—'}")
                            st.write(f"**Diagnostic:** {cons['diagnostic'] or '—'}")
                            st.write(f"**Traitement:** {cons['traitement'] or '—'}")
        else:
            st.info("Aucun patient enregistré.")
    conn.close()


# ============================================================
# PAGE : RENDEZ-VOUS
# ============================================================
MOTIFS_RDV = ["Consultation initiale","Fracture / Traumatisme","Entorse / Luxation",
    "Lombalgie / Dorsalgie","Cervicalgie","Gonarthrose / Coxarthrose","Hernie discale",
    "Suivi post-opératoire","Contrôle radiologique","Rééducation / Kinésithérapie",
    "Prothèse articulaire","Tendinopathie","Ostéoporose","Certificat médical","Autre motif"]

def page_rendez_vous():
    st.markdown("<div class='main-header'><div style='font-size:2rem;'>📅</div><div><h1>Gestion des Rendez-vous</h1><p>Planning et agenda du cabinet</p></div></div>", unsafe_allow_html=True)
    tab1, tab2, tab3 = st.tabs(["📅 Agenda du jour", "📆 Planning semaine", "➕ Nouveau RDV"])
    conn = get_connection(); c = conn.cursor()

    with tab1:
        sel_date = st.date_input("📅 Sélectionner une date", value=date.today())
        c.execute("""SELECT r.*,p.nom,p.prenom,p.telephone FROM rendez_vous r
                     JOIN patients p ON r.patient_id=p.id
                     WHERE r.date=? ORDER BY r.heure""", (str(sel_date),))
        rdvs = c.fetchall()
        if rdvs:
            for rdv in rdvs:
                sc = {"planifié":"badge-blue","en cours":"badge-orange","terminé":"badge-green","annulé":"badge-red"}.get(rdv["statut"],"badge-gray")
                col_r, col_s = st.columns([4,1])
                with col_r:
                    st.markdown(f"""<div class='rdv-card'>
                        <b>🕐 {rdv['heure']}</b> — <b>{rdv['prenom']} {rdv['nom']}</b>
                        <span class='badge {sc}'>{rdv['statut']}</span><br>
                        <span style='font-size:0.8rem;color:#374151;'>📌 {rdv['motif'] or '—'} | 📞 {rdv['telephone'] or '—'}</span>
                    </div>""", unsafe_allow_html=True)
                with col_s:
                    ns = st.selectbox("", ["planifié","en cours","terminé","annulé"],
                        index=["planifié","en cours","terminé","annulé"].index(rdv['statut']),
                        key=f"st_{rdv['id']}")
                    if ns != rdv['statut']:
                        if st.button("✅", key=f"upd_{rdv['id']}"):
                            c.execute("UPDATE rendez_vous SET statut=? WHERE id=?", (ns, rdv['id']))
                            conn.commit(); st.rerun()
        else:
            st.markdown("<div class='alert-info alert-box'>Aucun rendez-vous pour cette date.</div>", unsafe_allow_html=True)

    with tab2:
        today_dt = date.today()
        week_start = today_dt - timedelta(days=today_dt.weekday())
        days = [week_start + timedelta(days=i) for i in range(6)]
        cols = st.columns(6)
        for col, day in zip(cols, days):
            c.execute("SELECT COUNT(*) FROM rendez_vous WHERE date=? AND statut!='annulé'", (str(day),))
            cnt = c.fetchone()[0]
            bg = "#1a3a5c" if day == today_dt else "#f8fafc"
            cl = "white" if day == today_dt else "#1a3a5c"
            with col:
                st.markdown(f"""<div style='background:{bg};color:{cl};padding:0.8rem;border-radius:8px;text-align:center;border:1px solid #e5e7eb;'>
                    <div style='font-size:0.7rem;font-weight:600;'>{day.strftime('%A')[:3].upper()}</div>
                    <div style='font-size:1.4rem;font-weight:700;'>{day.day}</div>
                    <div style='font-size:0.72rem;'>{cnt} RDV</div>
                </div>""", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        for day in days:
            c.execute("""SELECT r.heure,r.motif,p.nom,p.prenom FROM rendez_vous r
                         JOIN patients p ON r.patient_id=p.id
                         WHERE r.date=? AND r.statut!='annulé' ORDER BY r.heure""", (str(day),))
            drdvs = c.fetchall()
            if drdvs:
                with st.expander(f"📅 {day.strftime('%A %d/%m')} — {len(drdvs)} RDV"):
                    for r in drdvs:
                        st.write(f"• **{r['heure']}** — {r['prenom']} {r['nom']} _{r['motif'] or '—'}_")

    with tab3:
        c.execute("SELECT id,nom,prenom FROM patients ORDER BY nom")
        all_p = c.fetchall()
        if not all_p:
            st.warning("⚠️ Aucun patient enregistré."); conn.close(); return
        opts = {f"{p['prenom']} {p['nom']}": p['id'] for p in all_p}
        def_idx = 0
        if "rdv_patient_id" in st.session_state:
            for i,(k,v) in enumerate(opts.items()):
                if v == st.session_state.rdv_patient_id: def_idx = i; break
            del st.session_state.rdv_patient_id
        c1,c2 = st.columns(2)
        with c1:
            sel_p  = st.selectbox("👤 Patient *", list(opts.keys()), index=def_idx)
            rdv_dt = st.date_input("📅 Date *", value=date.today(), min_value=date.today())
            motif  = st.selectbox("📌 Motif *", MOTIFS_RDV)
        with c2:
            heures = [f"{h:02d}:{m:02d}" for h in range(8,18) for m in [0,15,30,45]]
            heure  = st.selectbox("🕐 Heure *", heures, index=heures.index("09:00"))
            statut = st.selectbox("Statut", ["planifié","en cours","terminé","annulé"])
            notes  = st.text_area("Notes", height=80)
        if st.button("💾 Enregistrer le RDV", type="primary"):
            c.execute("SELECT id FROM rendez_vous WHERE date=? AND heure=? AND statut!='annulé'", (str(rdv_dt),heure))
            if c.fetchone():
                st.error(f"⚠️ Créneau {heure} déjà pris le {rdv_dt.strftime('%d/%m/%Y')}.")
            else:
                c.execute("INSERT INTO rendez_vous (patient_id,date,heure,motif,statut,notes) VALUES (?,?,?,?,?,?)",
                          (opts[sel_p],str(rdv_dt),heure,motif,statut,notes))
                conn.commit()
                st.success(f"✅ RDV enregistré pour {sel_p} le {rdv_dt.strftime('%d/%m/%Y')} à {heure}")
                st.rerun()
    conn.close()


# ============================================================
# PAGE : RADIOLOGIE
# ============================================================
def apply_clahe_manual(img_array, clip_limit=20, tile_size=32):
    def clahe_ch(ch, cl, ts):
        h,w = ch.shape
        res = np.zeros_like(ch, dtype=np.float64)
        for i in range(0,h,ts):
            for j in range(0,w,ts):
                tile = ch[i:i+ts, j:j+ts]
                hist,_ = np.histogram(tile.flatten(),256,[0,256])
                excess = np.sum(np.maximum(hist - cl*hist.mean(), 0))
                hist = np.minimum(hist, cl*hist.mean())
                hist += excess/256
                cdf = hist.cumsum()
                cdf_min = cdf[cdf>0].min() if cdf[cdf>0].size>0 else 0
                cdf_n = ((cdf-cdf_min)/(tile.size-cdf_min+1e-7)*255).astype(np.uint8)
                res[i:i+ts,j:j+ts] = cdf_n[tile]
        return res.astype(np.uint8)
    if len(img_array.shape)==3:
        return np.stack([clahe_ch(img_array[:,:,k],clip_limit,tile_size) for k in range(3)],axis=2)
    return clahe_ch(img_array,clip_limit,tile_size)

def process_radio(img, p):
    if p.get("mode_radio"): img = img.convert("L")
    arr = np.array(img)
    if p.get("clahe"):
        try:
            import cv2
            if len(arr.shape)==3:
                lab=cv2.cvtColor(arr,cv2.COLOR_RGB2LAB)
                cl=cv2.createCLAHE(clipLimit=p.get("clahe_clip",2.0),tileGridSize=(8,8))
                lab[:,:,0]=cl.apply(lab[:,:,0]); arr=cv2.cvtColor(lab,cv2.COLOR_LAB2RGB)
            else:
                cl=cv2.createCLAHE(clipLimit=p.get("clahe_clip",2.0),tileGridSize=(8,8)); arr=cl.apply(arr)
        except ImportError:
            arr=apply_clahe_manual(arr,clip_limit=p.get("clahe_clip",2.0)*10,tile_size=32)
    img=Image.fromarray(arr)
    if p.get("contraste",1.0)!=1.0: img=ImageEnhance.Contrast(img).enhance(p["contraste"])
    if p.get("luminosite",1.0)!=1.0: img=ImageEnhance.Brightness(img).enhance(p["luminosite"])
    if p.get("nettete",1.0)!=1.0: img=ImageEnhance.Sharpness(img).enhance(p["nettete"])
    if p.get("debruitage"): img=img.filter(ImageFilter.GaussianBlur(radius=p.get("denoise_r",0.8)))
    if p.get("detail_osseux"): img=img.filter(ImageFilter.UnsharpMask(radius=2,percent=150,threshold=3))
    if p.get("egalisation"):
        if img.mode=="L": img=ImageOps.equalize(img)
        else:
            r,g,b=img.split(); img=Image.merge("RGB",(ImageOps.equalize(r),ImageOps.equalize(g),ImageOps.equalize(b)))
    if p.get("negatif"): img=ImageOps.invert(img.convert("RGB")); img=img.convert("L") if p.get("mode_radio") else img
    gamma=p.get("gamma",1.0)
    if gamma!=1.0:
        lut=[int(((i/255.0)**(1.0/gamma))*255) for i in range(256)]
        img=img.point(lut) if img.mode=="L" else img.point(lut*3)
    return img

def page_radiologie():
    st.markdown("<div class='main-header'><div style='font-size:2rem;'>🩻</div><div><h1>Traitement des Images Radiologiques</h1><p>Amélioration de la qualité des clichés conventionnels</p></div></div>", unsafe_allow_html=True)
    col_l, col_r = st.columns([1,2])

    with col_l:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>⚙️ Paramètres</div>", unsafe_allow_html=True)
        uf = st.file_uploader("📁 Charger une image radiologique", type=["jpg","jpeg","png","tif","tiff","bmp"])
        if uf:
            mode_radio  = st.checkbox("🩻 Mode radiologie (niveaux de gris)", value=True)
            use_clahe   = st.checkbox("CLAHE (contraste adaptatif)", value=True)
            use_denoise = st.checkbox("Débruitage", value=False)
            use_detail  = st.checkbox("Détail osseux", value=False)
            use_egal    = st.checkbox("Égalisation histogramme", value=False)
            use_neg     = st.checkbox("Négatif / Inversé", value=False)
            contraste   = st.slider("Contraste",    0.5, 3.0, 1.2, 0.1)
            luminosite  = st.slider("Luminosité",   0.5, 2.0, 1.0, 0.1)
            nettete     = st.slider("Netteté",       0.5, 3.0, 1.3, 0.1)
            gamma       = st.slider("Gamma",         0.3, 2.5, 1.0, 0.1)
            clahe_clip  = st.slider("Clip CLAHE",    1.0, 5.0, 2.0, 0.5) if use_clahe else 2.0
            denoise_r   = st.slider("Force débruitage",0.3,3.0,0.8,0.1) if use_denoise else 0.8
            params = {"mode_radio":mode_radio,"clahe":use_clahe,"clahe_clip":clahe_clip,
                      "contraste":contraste,"luminosite":luminosite,"nettete":nettete,"gamma":gamma,
                      "debruitage":use_denoise,"denoise_r":denoise_r,"detail_osseux":use_detail,
                      "negatif":use_neg,"egalisation":use_egal}
            col_b1,col_b2=st.columns(2)
            with col_b1:
                if st.button("🚀 Traiter", type="primary", use_container_width=True):
                    st.session_state.radio_img = process_radio(Image.open(uf), params)
                    st.session_state.radio_preset = "Personnalisé"
            with col_b2:
                if st.button("🔄 Reset", use_container_width=True):
                    if "radio_img" in st.session_state: del st.session_state.radio_img
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>⚡ Préréglages</div>", unsafe_allow_html=True)
        presets = {
            "🦴 Os / Fracture": {"mode_radio":True,"clahe":True,"clahe_clip":3.0,"contraste":1.8,"nettete":2.5,"luminosite":1.0,"gamma":0.9},
            "🦵 Articulaire":   {"mode_radio":True,"clahe":True,"clahe_clip":2.0,"contraste":1.5,"nettete":1.8,"luminosite":1.1,"gamma":1.0},
            "🔲 Négatif radio": {"mode_radio":True,"clahe":True,"clahe_clip":2.0,"contraste":1.5,"nettete":1.5,"negatif":True,"luminosite":1.0,"gamma":1.0},
            "✨ Haute qualité": {"mode_radio":True,"clahe":True,"clahe_clip":2.5,"contraste":2.0,"nettete":2.0,"debruitage":True,"denoise_r":0.5,"detail_osseux":True,"luminosite":1.0,"gamma":1.0},
            "☁️ Sous-exposé":  {"mode_radio":True,"clahe":True,"clahe_clip":3.0,"contraste":1.6,"luminosite":1.4,"nettete":1.5,"gamma":0.7},
        }
        for name,pp in presets.items():
            if st.button(name, use_container_width=True):
                if uf:
                    full = {"mode_radio":False,"clahe":False,"clahe_clip":2.0,"contraste":1.0,"luminosite":1.0,
                            "nettete":1.0,"gamma":1.0,"debruitage":False,"denoise_r":0.8,
                            "detail_osseux":False,"negatif":False,"egalisation":False}
                    full.update(pp)
                    st.session_state.radio_img = process_radio(Image.open(uf), full)
                    st.session_state.radio_preset = name; st.rerun()
                else: st.warning("Chargez d'abord une image.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_r:
        if uf:
            orig = Image.open(uf)
            c1,c2 = st.columns(2)
            with c1:
                st.markdown("<div style='background:#1a3a5c;color:white;padding:0.5rem;border-radius:8px 8px 0 0;text-align:center;font-size:0.85rem;font-weight:600;'>📷 Image originale</div>", unsafe_allow_html=True)
                st.image(orig, use_container_width=True)
                st.markdown(f"<div style='background:#f8fafc;padding:0.4rem;border-radius:0 0 8px 8px;font-size:0.75rem;color:#6b7280;text-align:center;'>{orig.size[0]}×{orig.size[1]}px · {orig.mode}</div>", unsafe_allow_html=True)
            with c2:
                if "radio_img" in st.session_state:
                    proc = st.session_state.radio_img
                    label = st.session_state.get("radio_preset","Traitement personnalisé")
                    st.markdown(f"<div style='background:#065f46;color:white;padding:0.5rem;border-radius:8px 8px 0 0;text-align:center;font-size:0.85rem;font-weight:600;'>✨ {label}</div>", unsafe_allow_html=True)
                    st.image(proc, use_container_width=True)
                    buf=io.BytesIO(); proc.save(buf,format="PNG")
                    st.download_button("⬇️ Télécharger", buf.getvalue(),
                        f"radio_traitee.png","image/png", use_container_width=True)
                else:
                    st.markdown("<div style='background:#f3f4f6;border:2px dashed #d1d5db;border-radius:8px;padding:4rem;text-align:center;color:#9ca3af;'><div style='font-size:3rem;'>🩻</div><p>Cliquez sur Traiter<br>ou choisissez un préréglage</p></div>", unsafe_allow_html=True)
            st.markdown("""<div class='card' style='margin-top:1rem;'>
                <div class='section-title'>💡 Conseils</div>
                <div style='display:grid;grid-template-columns:1fr 1fr;gap:0.5rem;font-size:0.82rem;'>
                    <div>🦴 <b>Fractures:</b> CLAHE + forte netteté + contraste élevé</div>
                    <div>🦵 <b>Arthrose:</b> Contraste modéré + détail osseux</div>
                    <div>🔲 <b>Surexposé:</b> Réduire luminosité + gamma &lt; 1</div>
                    <div>☁️ <b>Sous-exposé:</b> Préréglage "Sous-exposé"</div>
                </div></div>""", unsafe_allow_html=True)
        else:
            st.markdown("<div style='background:#f8fafc;border:2px dashed #d1d5db;border-radius:12px;padding:5rem;text-align:center;color:#9ca3af;margin-top:1rem;'><div style='font-size:4rem;'>🩻</div><h3 style='color:#374151;'>Traitement radiologique</h3><p>Chargez un cliché (JPG, PNG, TIFF) pour commencer</p></div>", unsafe_allow_html=True)


# ============================================================
# PAGE : PHARMACIE
# ============================================================
CLASSES_MED = ["Tous","AINS","AINS Cox-2","AINS topique","Antalgique","Opioïde faible",
               "Antalgique pallier 2","Myorelaxant","Corticoïde","HBPM","AOD",
               "Bisphosphonate","Supplément","IPP","Antibiotique","Fluoroquinolone","Antioedémateux","Autre"]

def page_pharmacie():
    st.markdown("<div class='main-header'><div style='font-size:2rem;'>💊</div><div><h1>ePharmacie</h1><p>Bibliothèque médicamenteuse — Traumatologie & Orthopédie</p></div></div>", unsafe_allow_html=True)
    tab1,tab2,tab3 = st.tabs(["💊 Catalogue","➕ Ajouter médicament","📦 Stocks"])
    conn=get_connection(); c=conn.cursor()

    with tab1:
        cs,cc=st.columns([3,1])
        with cs: search=st.text_input("🔍 Rechercher (nom, DCI, classe)")
        with cc: cls_f=st.selectbox("Classe", CLASSES_MED)
        q="SELECT * FROM medicaments WHERE 1=1"; p=[]
        if search: q+=" AND (nom LIKE ? OR dci LIKE ? OR classe LIKE ?)"; p+=[f"%{search}%"]*3
        if cls_f!="Tous": q+=" AND classe=?"; p.append(cls_f)
        c.execute(q+" ORDER BY classe,nom", p)
        meds=c.fetchall()
        st.markdown(f"<p style='color:#6b7280;font-size:0.85rem;'>{len(meds)} médicament(s)</p>", unsafe_allow_html=True)
        classes=list(dict.fromkeys(m["classe"] for m in meds))
        for cls in classes:
            cms=[m for m in meds if m["classe"]==cls]
            st.markdown(f"<div style='background:#1a3a5c;color:white;padding:0.5rem 1rem;border-radius:8px;margin-top:1rem;margin-bottom:0.5rem;font-weight:600;font-size:0.9rem;'>💊 {cls} ({len(cms)})</div>", unsafe_allow_html=True)
            for med in cms:
                sc={"badge-red" if med["stock"]<5 else "badge-orange" if med["stock"]<15 else "badge-green"}
                stock_l=f"❌ Rupture" if med["stock"]==0 else f"⚠️ {med['stock']}" if med["stock"]<10 else f"✅ {med['stock']}"
                with st.expander(f"💊 {med['nom']} — {med['dci']} · {med['dosage']}"):
                    c1,c2=st.columns([3,1])
                    with c1:
                        st.markdown(f"""<table style='width:100%;font-size:0.85rem;'>
                        <tr><td style='color:#6b7280;width:180px;'>DCI</td><td><b>{med['dci']}</b></td></tr>
                        <tr><td style='color:#6b7280;'>Classe</td><td><span class='badge badge-blue'>{med['classe']}</span></td></tr>
                        <tr><td style='color:#6b7280;'>Forme/Dosage</td><td>{med['forme']} — {med['dosage']}</td></tr>
                        <tr><td style='color:#6b7280;'>📋 Adulte</td><td style='color:#065f46;font-weight:500;'>{med['posologie_adulte'] or '—'}</td></tr>
                        <tr><td style='color:#6b7280;'>👶 Enfant</td><td>{med['posologie_enfant'] or '—'}</td></tr>
                        <tr><td style='color:#6b7280;'>⛔ Contre-indications</td><td style='color:#dc2626;'>{med['contre_indications'] or '—'}</td></tr>
                        <tr><td style='color:#6b7280;'>⚠️ Effets indésirables</td><td style='color:#d97706;'>{med['effets_indesirables'] or '—'}</td></tr>
                        </table>""", unsafe_allow_html=True)
                    with c2:
                        st.markdown(f"""<div style='text-align:center;background:#f8fafc;padding:1rem;border-radius:8px;'>
                            <div style='font-size:1.5rem;font-weight:700;color:#1a3a5c;'>{med['prix'] or 0:.0f} DA</div>
                            <div style='font-size:0.75rem;color:#6b7280;'>Prix unitaire</div>
                            <div style='margin-top:0.8rem;font-size:0.82rem;font-weight:600;'>Stock: {stock_l}</div>
                        </div>""", unsafe_allow_html=True)
                        if st.button("➕ Ordonnance", key=f"ordo_{med['id']}", use_container_width=True):
                            if "ordo_meds" not in st.session_state: st.session_state.ordo_meds=[]
                            entry={"nom":med["nom"],"posologie":med["posologie_adulte"],"duree":"À définir","instructions":""}
                            if entry["nom"] not in [x["nom"] for x in st.session_state.ordo_meds]:
                                st.session_state.ordo_meds.append(entry)
                            st.session_state.current_page="ordonnances"; st.rerun()

    with tab2:
        st.markdown("<div class='section-title'>➕ Nouveau médicament</div>", unsafe_allow_html=True)
        c1,c2=st.columns(2)
        with c1:
            nom=st.text_input("Nom commercial *"); dci=st.text_input("DCI *")
            cls=st.selectbox("Classe *", CLASSES_MED[1:]); forme_m=st.selectbox("Forme", ["Comprimé","Comprimé LP","Gélule","Seringue SC","Gel","Sirop","Autre"])
            dos=st.text_input("Dosage")
        with c2:
            prix=st.number_input("Prix (DA)",min_value=0.0,value=0.0,step=10.0)
            stk=st.number_input("Stock initial",min_value=0,value=0)
            pos_a=st.text_area("Posologie adulte *",height=80)
            pos_e=st.text_area("Posologie enfant",height=60)
        ci=st.text_area("Contre-indications",height=68); ei=st.text_area("Effets indésirables",height=68)
        if st.button("💾 Enregistrer", type="primary"):
            if nom and dci and pos_a:
                c.execute("INSERT INTO medicaments (nom,dci,classe,forme,dosage,posologie_adulte,posologie_enfant,contre_indications,effets_indesirables,prix,stock) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                          (nom,dci,cls,forme_m,dos,pos_a,pos_e,ci,ei,prix,stk))
                conn.commit(); st.success(f"✅ {nom} ajouté !"); st.rerun()
            else: st.error("⚠️ Nom, DCI et posologie adulte obligatoires.")

    with tab3:
        c.execute("SELECT * FROM medicaments ORDER BY stock ASC,nom")
        all_m=c.fetchall()
        col_a,col_b,col_c=st.columns(3)
        with col_a: st.metric("Total médicaments",len(all_m))
        with col_b: st.metric("En rupture",sum(1 for m in all_m if m["stock"]==0))
        with col_c: st.metric("Stock faible (<10)",sum(1 for m in all_m if 0<m["stock"]<10))
        st.markdown("---")
        for med in all_m:
            ic="🔴" if med["stock"]==0 else "🟡" if med["stock"]<10 else "🟢"
            c1,c2,c3=st.columns([3,1,1])
            with c1: st.write(f"{ic} **{med['nom']}** ({med['dosage']})")
            with c2: ns=st.number_input("",min_value=0,value=med["stock"],key=f"st_{med['id']}",label_visibility="collapsed")
            with c3:
                if st.button("💾",key=f"sv_{med['id']}"):
                    c.execute("UPDATE medicaments SET stock=? WHERE id=?",(ns,med["id"])); conn.commit(); st.rerun()
    conn.close()


# ============================================================
# PAGE : ORDONNANCES
# ============================================================
DIAGNOSTICS = ["Fracture du radius","Fracture du fémur","Fracture de la cheville","Fracture des côtes",
    "Entorse du genou","Entorse de la cheville","Luxation de l'épaule",
    "Hernie discale lombaire L4-L5","Hernie discale lombaire L5-S1",
    "Cervicalgie / Torticolis","Lombalgie aiguë","Lombalgie chronique",
    "Gonarthrose","Coxarthrose","Ostéoporose","Tendinite rotulienne",
    "Tendinite de la coiffe des rotateurs","Syndrome du canal carpien",
    "Suivi post-PTH","Suivi post-PTG","Contusion musculaire","Déchirure musculaire","Autre"]

PROTOCOLES = {
    "Fracture (douleur post-opératoire)": [
        {"nom":"Paracétamol 1g","posologie":"1g toutes les 6h","duree":"7 jours","instructions":""},
        {"nom":"Ibuprofène 400mg","posologie":"400mg 3x/jour pendant les repas","duree":"5 jours","instructions":""},
        {"nom":"Oméprazole 20mg","posologie":"20mg 1x/jour à jeun","duree":"7 jours","instructions":""},
    ],
    "Lombalgie aiguë": [
        {"nom":"Ibuprofène 400mg","posologie":"400mg 3x/jour pendant les repas","duree":"5 jours","instructions":""},
        {"nom":"Méthocarbamol 500mg","posologie":"1500mg 4x/jour","duree":"5 jours","instructions":""},
        {"nom":"Oméprazole 20mg","posologie":"20mg 1x/jour à jeun","duree":"5 jours","instructions":""},
    ],
    "Entorse (inflammation aiguë)": [
        {"nom":"Kétoprofène 100mg","posologie":"100mg 2x/jour avec repas","duree":"5 jours","instructions":""},
        {"nom":"Paracétamol 1g","posologie":"1g 3x/jour si douleurs","duree":"5 jours","instructions":""},
        {"nom":"Diclofénac gel 1%","posologie":"4g 3x/jour local","duree":"7 jours","instructions":"Masser doucement"},
    ],
    "Post-opératoire (anticoagulation)": [
        {"nom":"Énoxaparine 4000UI","posologie":"0.4mL SC 1x/jour","duree":"21 jours","instructions":"Injection sous-cutanée"},
        {"nom":"Paracétamol 1g","posologie":"1g 3x/jour","duree":"10 jours","instructions":""},
        {"nom":"Tramadol 50mg","posologie":"50mg 3x/jour si douleur forte","duree":"5 jours","instructions":""},
    ],
    "Ostéoporose (traitement de fond)": [
        {"nom":"Alendronate 70mg","posologie":"70mg 1x/semaine à jeun","duree":"3 mois","instructions":"Rester debout 30min après"},
        {"nom":"Calcium + Vitamine D3","posologie":"1 cp 2x/jour après repas","duree":"3 mois","instructions":""},
    ],
}

def gen_ordo_text(patient, meds, date_o, doctor):
    lines=["="*60,"ORDONNANCE MÉDICALE","Cabinet de Traumatologie & Orthopédie","="*60,
           f"Date: {date_o}",f"Médecin: {doctor}","─"*60,
           f"Patient: {patient.get('prenom','—')} {patient.get('nom','—')}",
           f"Date de naissance: {patient.get('date_naissance','—') or '—'}"]
    if patient.get('allergies'):
        lines.append(f"⚠️ ALLERGIES: {patient['allergies']}")
    lines+=["─"*60,"","PRESCRIPTION:",""]
    for i,m in enumerate(meds,1):
        lines+=[f"{i}. {m['nom']}",f"   Posologie: {m['posologie']}",f"   Durée: {m['duree']}"]
        if m.get("instructions"): lines.append(f"   Instructions: {m['instructions']}")
        lines.append("")
    lines+=["─"*60,"Signature du médecin: ___________________","="*60]
    return "\n".join(lines)

def page_ordonnances():
    st.markdown("<div class='main-header'><div style='font-size:2rem;'>📋</div><div><h1>Ordonnances & Consultations</h1><p>Génération automatique depuis la bibliothèque médicamenteuse</p></div></div>", unsafe_allow_html=True)
    tab1,tab2,tab3=st.tabs(["📝 Nouvelle consultation","⚡ Ordonnance express","📚 Historique"])
    conn=get_connection(); c=conn.cursor()
    c.execute("SELECT id,nom,prenom,date_naissance,allergies FROM patients ORDER BY nom")
    all_p=c.fetchall()
    if not all_p: st.warning("⚠️ Aucun patient enregistré."); conn.close(); return
    opts={f"{p['prenom']} {p['nom']}":p['id'] for p in all_p}

    with tab1:
        c1,c2=st.columns([1,2])
        with c1:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown("<div class='section-title'>👤 Patient & Consultation</div>", unsafe_allow_html=True)
            def_idx=0
            if "consult_patient_id" in st.session_state:
                for i,(k,v) in enumerate(opts.items()):
                    if v==st.session_state.consult_patient_id: def_idx=i; break
            sel=st.selectbox("Patient *",list(opts.keys()),index=def_idx)
            pid=opts[sel]
            c.execute("SELECT * FROM patients WHERE id=?",(pid,)); pat=c.fetchone()
            if pat and pat["allergies"]:
                st.markdown(f"<div class='alert-warning alert-box'>⚠️ <b>Allergies:</b> {pat['allergies']}</div>", unsafe_allow_html=True)
            dt=st.date_input("Date consultation",value=date.today())
            diag=st.selectbox("Diagnostic",DIAGNOSTICS)
            anam=st.text_area("Anamnèse",height=80)
            exam=st.text_area("Examen clinique",height=80)
            notes=st.text_area("Notes",height=68)
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown("<div class='section-title'>⚡ Protocoles rapides</div>", unsafe_allow_html=True)
            for pname in PROTOCOLES:
                if st.button(f"📋 {pname}",key=f"proto_{pname}",use_container_width=True):
                    st.session_state.ordo_meds=PROTOCOLES[pname]; st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        with c2:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown("<div class='section-title'>💊 Prescription</div>", unsafe_allow_html=True)
            c.execute("SELECT * FROM medicaments ORDER BY classe,nom"); all_m=c.fetchall()
            med_opts={m["nom"]:dict(m) for m in all_m}
            ms=st.text_input("🔍 Rechercher médicament")
            filt={k:v for k,v in med_opts.items() if not ms or ms.lower() in k.lower() or ms.lower() in v.get("dci","").lower()}
            if filt:
                sel_med=st.selectbox("Médicament",list(filt.keys()))
                sm=filt[sel_med]
                if sm:
                    st.markdown(f"<div style='background:#f0f9ff;padding:0.6rem;border-radius:6px;font-size:0.82rem;margin-bottom:0.5rem;'><b>Posologie recommandée:</b> {sm['posologie_adulte']}<br>{'<span style=\"color:#dc2626;\">⛔ CI: '+sm['contre_indications']+'</span>' if sm['contre_indications'] else ''}</div>", unsafe_allow_html=True)
                pos=st.text_input("Posologie",value=sm.get("posologie_adulte","") if sm else "")
                dur=st.text_input("Durée",placeholder="Ex: 5 jours, 1 mois")
                inst=st.text_input("Instructions spéciales",placeholder="Ex: À jeun, avec repas...")
                if st.button("➕ Ajouter à l'ordonnance",type="primary",use_container_width=True):
                    if "ordo_meds" not in st.session_state: st.session_state.ordo_meds=[]
                    st.session_state.ordo_meds.append({"nom":sel_med,"posologie":pos,"duree":dur,"instructions":inst})
                    st.rerun()
            st.markdown("---")
            st.markdown("**📋 Ordonnance en cours:**")
            if "ordo_meds" not in st.session_state: st.session_state.ordo_meds=[]
            if st.session_state.ordo_meds:
                for i,med in enumerate(st.session_state.ordo_meds):
                    cm,cd=st.columns([5,1])
                    with cm:
                        st.markdown(f"<div style='background:#f8fafc;padding:0.6rem;border-radius:6px;margin-bottom:0.3rem;font-size:0.85rem;border-left:3px solid #2d6a9f;'><b>{i+1}. {med['nom']}</b><br>📋 {med['posologie']} · ⏱️ {med['duree']}{('<br>💬 '+med['instructions']) if med['instructions'] else ''}</div>", unsafe_allow_html=True)
                    with cd:
                        if st.button("🗑️",key=f"del_{i}"):
                            st.session_state.ordo_meds.pop(i); st.rerun()
                if st.button("🗑️ Vider",use_container_width=True):
                    st.session_state.ordo_meds=[]; st.rerun()
                st.markdown("---")
                pat_dict=dict(pat) if pat else {"prenom":"—","nom":"—","date_naissance":"—","allergies":""}
                ordo_txt=gen_ordo_text(pat_dict,st.session_state.ordo_meds,str(dt),st.session_state.full_name)
                with st.expander("👁️ Aperçu"): st.code(ordo_txt,language=None)
                cb1,cb2=st.columns(2)
                with cb1:
                    if st.button("💾 Sauvegarder consultation",type="primary",use_container_width=True):
                        meds_str="\n".join([f"{m['nom']} — {m['posologie']} — {m['duree']}" for m in st.session_state.ordo_meds])
                        c.execute("INSERT INTO consultations (patient_id,date,anamnese,examen_clinique,diagnostic,traitement,notes) VALUES (?,?,?,?,?,?,?)",
                                  (pid,str(dt),anam,exam,diag,meds_str,notes))
                        cid=c.lastrowid
                        c.execute("INSERT INTO ordonnances (patient_id,consultation_id,date,medicaments,duree) VALUES (?,?,?,?,?)",
                                  (pid,cid,str(dt),meds_str,"Voir détails"))
                        conn.commit(); st.success("✅ Consultation et ordonnance enregistrées !")
                        st.session_state.ordo_meds=[]; st.rerun()
                with cb2:
                    st.download_button("⬇️ Télécharger (.txt)",ordo_txt.encode("utf-8"),
                        f"ordonnance_{sel.replace(' ','_')}_{dt}.txt","text/plain",use_container_width=True)
            else:
                st.markdown("<div class='alert-info alert-box'>💡 Ajoutez des médicaments ou choisissez un protocole.</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    with tab2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        sel_q=st.selectbox("Patient",list(opts.keys()),key="qp")
        pid_q=opts[sel_q]
        c.execute("SELECT * FROM patients WHERE id=?",(pid_q,)); pat_q=c.fetchone()
        sel_proto=st.selectbox("Protocole",list(PROTOCOLES.keys()))
        proto_meds=PROTOCOLES[sel_proto]
        for m in proto_meds:
            st.markdown(f"<div style='background:#f0f9ff;padding:0.5rem 1rem;border-radius:6px;margin-bottom:0.3rem;font-size:0.85rem;border-left:3px solid #2563eb;'>💊 <b>{m['nom']}</b> — {m['posologie']} — {m['duree']}</div>", unsafe_allow_html=True)
        ordo_txt_q=gen_ordo_text(dict(pat_q) if pat_q else {},proto_meds,str(date.today()),st.session_state.full_name)
        st.download_button("⬇️ Télécharger l'ordonnance",ordo_txt_q.encode("utf-8"),
            f"ordonnance_{sel_q.replace(' ','_')}_{date.today()}.txt","text/plain")
        st.markdown("</div>", unsafe_allow_html=True)

    with tab3:
        pf=st.selectbox("Filtrer par patient",["Tous"]+list(opts.keys()),key="hfp")
        if pf=="Tous":
            c.execute("SELECT o.*,p.nom,p.prenom FROM ordonnances o JOIN patients p ON o.patient_id=p.id ORDER BY o.date DESC LIMIT 50")
        else:
            c.execute("SELECT o.*,p.nom,p.prenom FROM ordonnances o JOIN patients p ON o.patient_id=p.id WHERE o.patient_id=? ORDER BY o.date DESC",(opts[pf],))
        for o in c.fetchall():
            with st.expander(f"💊 {o['prenom']} {o['nom']} — {o['date']}"):
                for line in (o['medicaments'] or '').split('\n'):
                    if line.strip(): st.write(f"• {line}")
    conn.close()


# ============================================================
# PAGE : RECETTES
# ============================================================
ACTES = {"Consultation initiale":2000,"Consultation de suivi":1500,"Consultation d'urgence":2500,
    "Infiltration articulaire":3000,"Infiltration épidural":4000,"Plâtre / Immobilisation":2500,
    "Réduction fracture (consult)":3500,"Certificat médical":500,"Certificat de reprise":500,
    "Ponction articulaire":2000,"Pansement / Soin local":800,"Ablation de plâtre":500,
    "Compte rendu opératoire":1500,"Bilan radiologique (lecture)":1000,
    "Consultation pré-opératoire":2000,"Acte autre":0}
MODES = ["Espèces","Chèque","CCP","Virement","Mutuelle (tiers payant)","Gratuité"]

def page_recettes():
    st.markdown("<div class='main-header'><div style='font-size:2rem;'>🧾</div><div><h1>Gestion des Recettes</h1><p>Facturation et suivi financier du cabinet</p></div></div>", unsafe_allow_html=True)
    tab1,tab2,tab3=st.tabs(["➕ Nouvelle recette","📊 Tableau financier","📜 Historique"])
    conn=get_connection(); c=conn.cursor()
    c.execute("SELECT id,nom,prenom FROM patients ORDER BY nom"); all_p=c.fetchall()
    opts={f"{p['prenom']} {p['nom']}":p['id'] for p in all_p}

    with tab1:
        if not all_p: st.warning("Aucun patient enregistré."); conn.close(); return
        c1,c2=st.columns(2)
        with c1:
            sel=st.selectbox("👤 Patient *",list(opts.keys()))
            dt=st.date_input("📅 Date",value=date.today())
            acte=st.selectbox("🩺 Acte médical *",list(ACTES.keys()))
            montant=st.number_input("💰 Montant (DA) *",min_value=0.0,value=float(ACTES.get(acte,0)),step=100.0)
        with c2:
            mode=st.selectbox("💳 Mode de paiement",MODES)
            paye=st.checkbox("✅ Paiement reçu / Acquitté",value=True)
            notes=st.text_area("📝 Notes",height=100)
        if st.button("💾 Enregistrer la recette",type="primary",use_container_width=True):
            c.execute("INSERT INTO recettes (patient_id,date,acte,montant,mode_paiement,paye,notes) VALUES (?,?,?,?,?,?,?)",
                      (opts[sel],str(dt),acte,montant,mode,int(paye),notes))
            conn.commit(); st.success(f"✅ Recette de {montant:.0f} DA enregistrée !"); st.rerun()

    with tab2:
        today=date.today()
        cd1,cd2=st.columns(2)
        with cd1: d1=st.date_input("Du",value=today.replace(day=1))
        with cd2: d2=st.date_input("Au",value=today)
        c.execute("SELECT COALESCE(SUM(montant),0) FROM recettes WHERE date=? AND paye=1",(str(today),)); today_t=c.fetchone()[0]
        c.execute("SELECT COALESCE(SUM(montant),0) FROM recettes WHERE strftime('%Y-%m',date)=? AND paye=1",(today.strftime('%Y-%m'),)); month_t=c.fetchone()[0]
        c.execute("SELECT COALESCE(SUM(montant),0) FROM recettes WHERE strftime('%Y',date)=? AND paye=1",(str(today.year),)); year_t=c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM recettes WHERE date BETWEEN ? AND ? AND paye=1",(str(d1),str(d2))); nb=c.fetchone()[0]
        col1,col2,col3,col4=st.columns(4)
        with col1: st.markdown(f"<div class='stat-card'><div class='number'>{today_t:,.0f}</div><div class='label'>DA aujourd'hui</div></div>", unsafe_allow_html=True)
        with col2: st.markdown(f"<div class='stat-card green'><div class='number'>{month_t:,.0f}</div><div class='label'>DA ce mois</div></div>", unsafe_allow_html=True)
        with col3: st.markdown(f"<div class='stat-card orange'><div class='number'>{year_t:,.0f}</div><div class='label'>DA cette année</div></div>", unsafe_allow_html=True)
        with col4: st.markdown(f"<div class='stat-card purple'><div class='number'>{nb}</div><div class='label'>Actes sur période</div></div>", unsafe_allow_html=True)
        # Impayés
        c.execute("SELECT r.*,p.nom,p.prenom FROM recettes r JOIN patients p ON r.patient_id=p.id WHERE r.paye=0 ORDER BY r.date DESC")
        unpaid=c.fetchall()
        if unpaid:
            total_u=sum(r["montant"] for r in unpaid)
            st.markdown(f"<div class='alert-warning alert-box' style='margin-top:1rem;'>⚠️ <b>{len(unpaid)} facture(s) non payée(s)</b> — Total: <b>{total_u:,.0f} DA</b></div>", unsafe_allow_html=True)
            for r in unpaid:
                cc1,cc2=st.columns([4,1])
                with cc1: st.markdown(f"<div style='background:#fef3c7;padding:0.5rem 1rem;border-radius:6px;font-size:0.85rem;border-left:3px solid #d97706;'>👤 <b>{r['prenom']} {r['nom']}</b> · {r['date']} · {r['acte']} · <b style='color:#d97706;'>{r['montant']:,.0f} DA</b></div>", unsafe_allow_html=True)
                with cc2:
                    if st.button("✅ Payé",key=f"pay_{r['id']}"):
                        c.execute("UPDATE recettes SET paye=1 WHERE id=?",(r["id"],)); conn.commit(); st.rerun()

    with tab3:
        cs2,cp=st.columns([2,2])
        with cs2: sh=st.text_input("🔍 Rechercher")
        with cp: pf=st.selectbox("Patient",["Tous"]+list(opts.keys()),key="hf")
        q="SELECT r.*,p.nom,p.prenom FROM recettes r JOIN patients p ON r.patient_id=p.id WHERE 1=1"; pm=[]
        if pf!="Tous": q+=" AND r.patient_id=?"; pm.append(opts[pf])
        if sh: q+=" AND (p.nom LIKE ? OR p.prenom LIKE ? OR r.acte LIKE ?)"; pm+=[f"%{sh}%"]*3
        c.execute(q+" ORDER BY r.date DESC LIMIT 100",pm)
        for r in c.fetchall():
            pb="<span class='badge badge-green'>✅ Payé</span>" if r['paye'] else "<span class='badge badge-orange'>⏳ En attente</span>"
            st.markdown(f"<div class='card' style='padding:0.8rem 1rem;margin-bottom:0.4rem;'><div style='display:flex;justify-content:space-between;align-items:center;'><div><b>👤 {r['prenom']} {r['nom']}</b> · 📅 {r['date']}<br><span style='font-size:0.82rem;color:#374151;'>🩺 {r['acte']} · 💳 {r['mode_paiement']}</span></div><div style='text-align:right;'><div style='font-size:1.1rem;font-weight:700;color:#1a3a5c;'>{r['montant']:,.0f} DA</div>{pb}</div></div></div>", unsafe_allow_html=True)
    conn.close()


# ============================================================
# PAGE : STATISTIQUES
# ============================================================
def page_statistiques():
    st.markdown("<div class='main-header'><div style='font-size:2rem;'>📊</div><div><h1>Statistiques du Cabinet</h1><p>Analyse des activités médicales et financières</p></div></div>", unsafe_allow_html=True)
    conn=get_connection(); c=conn.cursor()
    today=date.today(); year=today.year; month=today.month

    c.execute("SELECT COUNT(*) FROM patients"); tp=c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM patients WHERE strftime('%Y-%m',created_at)=?",(today.strftime('%Y-%m'),)); npm=c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM consultations"); tc=c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM rendez_vous WHERE statut='terminé'"); tr=c.fetchone()[0]
    col1,col2,col3,col4=st.columns(4)
    with col1: st.metric("Total patients",tp)
    with col2: st.metric("Nouveaux ce mois",npm)
    with col3: st.metric("Consultations totales",tc)
    with col4: st.metric("RDV honorés",tr)

    col_l,col_r=st.columns(2)
    with col_l:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>📅 Activité mensuelle</div>", unsafe_allow_html=True)
        monthly=[]
        for m in range(1,month+1):
            ms=f"{year}-{m:02d}"
            c.execute("SELECT COUNT(*) FROM consultations WHERE strftime('%Y-%m',date)=?",(ms,)); cc=c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM patients WHERE strftime('%Y-%m',created_at)=?",(ms,)); pc=c.fetchone()[0]
            monthly.append({"mois":calendar.month_abbr[m],"consult":cc,"patients":pc})
        max_c=max((d["consult"] for d in monthly),default=1) or 1
        for d in monthly:
            pct=d["consult"]/max_c*100
            st.markdown(f"<div style='margin-bottom:0.5rem;'><div style='display:flex;justify-content:space-between;font-size:0.82rem;margin-bottom:0.2rem;'><span><b>{d['mois']}</b></span><span>{d['consult']} consultations · {d['patients']} patients</span></div><div style='background:#e5e7eb;border-radius:4px;height:10px;'><div style='background:linear-gradient(90deg,#1a3a5c,#2d6a9f);width:{pct}%;height:10px;border-radius:4px;'></div></div></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_r:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>💰 Recettes mensuelles</div>", unsafe_allow_html=True)
        rec_data=[]
        for m in range(1,month+1):
            ms=f"{year}-{m:02d}"
            c.execute("SELECT COALESCE(SUM(montant),0) FROM recettes WHERE strftime('%Y-%m',date)=? AND paye=1",(ms,)); t=c.fetchone()[0]
            rec_data.append({"mois":calendar.month_abbr[m],"total":t})
        max_r=max((d["total"] for d in rec_data),default=1) or 1
        for d in rec_data:
            pct=d["total"]/max_r*100
            st.markdown(f"<div style='margin-bottom:0.5rem;'><div style='display:flex;justify-content:space-between;font-size:0.82rem;margin-bottom:0.2rem;'><span><b>{d['mois']}</b></span><span><b>{d['total']:,.0f} DA</b></span></div><div style='background:#e5e7eb;border-radius:4px;height:10px;'><div style='background:linear-gradient(90deg,#065f46,#059669);width:{pct}%;height:10px;border-radius:4px;'></div></div></div>", unsafe_allow_html=True)
        c.execute("SELECT COALESCE(SUM(montant),0) FROM recettes WHERE strftime('%Y',date)=? AND paye=1",(str(year),)); ty=c.fetchone()[0]
        st.markdown(f"<div style='background:#d1fae5;padding:0.8rem;border-radius:8px;margin-top:1rem;text-align:center;'><b>Total {year}: {ty:,.0f} DA</b></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>🩺 Diagnostics les plus fréquents</div>", unsafe_allow_html=True)
    c.execute("SELECT diagnostic,COUNT(*) as cnt FROM consultations WHERE diagnostic IS NOT NULL AND diagnostic!='' GROUP BY diagnostic ORDER BY cnt DESC LIMIT 10")
    diags=c.fetchall()
    if diags:
        max_d=diags[0]["cnt"] or 1; colors=["#1a3a5c","#2d6a9f","#3b82f6","#60a5fa","#93c5fd","#bfdbfe"]
        cc1,cc2=st.columns(2)
        for i,d in enumerate(diags):
            pct=d["cnt"]/max_d*100
            with (cc1 if i%2==0 else cc2):
                st.markdown(f"<div style='margin-bottom:0.6rem;'><div style='display:flex;justify-content:space-between;font-size:0.82rem;margin-bottom:0.2rem;'><span>{d['diagnostic']}</span><span><b>{d['cnt']} cas</b></span></div><div style='background:#e5e7eb;border-radius:4px;height:8px;'><div style='background:{colors[min(i,5)]};width:{pct}%;height:8px;border-radius:4px;'></div></div></div>", unsafe_allow_html=True)
    else:
        st.info("Aucune donnée de diagnostic.")
    st.markdown("</div>", unsafe_allow_html=True)
    conn.close()


# ============================================================
# NOUVELLE PAGE : ADMINISTRATION (sauvegarde/restauration)
# ============================================================
def page_admin():
    st.markdown("<div class='main-header'><div style='font-size:2rem;'>💾</div><div><h1>Administration des données</h1><p>Sauvegarde et restauration de la base</p></div></div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>⬇️ Sauvegarder</div>", unsafe_allow_html=True)
        st.write("Téléchargez la base de données actuelle sur votre disque dur.")
        db_content = export_db()
        if db_content:
            st.download_button(
                label="💾 Télécharger la base (cabinet.db)",
                data=db_content,
                file_name=f"cabinet_backup_{date.today()}.db",
                mime="application/octet-stream",
                use_container_width=True
            )
        else:
            st.warning("Aucune base trouvée.")
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>⬆️ Restaurer</div>", unsafe_allow_html=True)
        st.write("Chargez une sauvegarde précédente (fichier .db).")
        uploaded_file = st.file_uploader("Choisir un fichier .db", type=["db"])
        if uploaded_file is not None:
            if st.button("🔄 Restaurer cette sauvegarde", type="primary", use_container_width=True):
                import_db(uploaded_file)
        st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("""
    <div class='card'>
        <div class='section-title'>📌 Astuce</div>
        <p>Avant d'éteindre votre PC, cliquez sur "Télécharger la base" pour sauvegarder toutes vos données.<br>
        Au prochain démarrage de l'application, cliquez sur "Restaurer" et sélectionnez le fichier sauvegardé.<br>
        Vos patients, rendez-vous, ordonnances seront alors récupérés.</p>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# MAIN — ROUTING
# ============================================================
init_db()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role      = None
    st.session_state.username  = None

if not st.session_state.logged_in:
    page_login()
else:
    role = st.session_state.role

    with st.sidebar:
        st.markdown(f"""<div style='background:linear-gradient(135deg,#1a3a5c,#2d6a9f);padding:1.2rem;border-radius:10px;color:white;margin-bottom:1.2rem;'>
            <div style='font-size:1.5rem;'>🦴</div>
            <div style='font-weight:700;font-size:1rem;margin-top:0.3rem;'>Dr. Cabinet</div>
            <div style='font-size:0.75rem;opacity:0.8;'>Traumatologie & Orthopédie</div>
            <div style='background:rgba(255,255,255,0.2);padding:0.2rem 0.6rem;border-radius:20px;font-size:0.7rem;margin-top:0.5rem;display:inline-block;'>
                {'👨‍⚕️ Médecin' if role=='medecin' else '👩‍💼 Secrétaire'}
            </div>
        </div>""", unsafe_allow_html=True)

        pages_secretaire = [("🏠 Accueil","accueil"),("👤 Patients","patients"),("📅 Rendez-vous","rendez_vous"),("🧾 Recettes","recettes")]
        pages_medecin    = pages_secretaire + [("🩻 Radiologie","radiologie"),("💊 ePharmacie","pharmacie"),("📋 Ordonnances","ordonnances"),("📊 Statistiques","statistiques")]
        pages = pages_medecin if role=="medecin" else pages_secretaire
        
        # Ajouter la page Admin pour tout le monde (ou seulement pour le médecin)
        pages.append(("💾 Administration","admin"))

        if "current_page" not in st.session_state: st.session_state.current_page="accueil"

        st.markdown("**Navigation**")
        for label,key in pages:
            if st.button(label, key=f"nav_{key}", use_container_width=True):
                st.session_state.current_page=key
                st.rerun()

        st.markdown("---")
        if st.button("🚪 Déconnexion", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

    page = st.session_state.current_page
    if   page=="accueil":      page_accueil()
    elif page=="patients":     page_patients()
    elif page=="rendez_vous":  page_rendez_vous()
    elif page=="radiologie"  and role=="medecin": page_radiologie()
    elif page=="pharmacie"   and role=="medecin": page_pharmacie()
    elif page=="ordonnances" and role=="medecin": page_ordonnances()
    elif page=="recettes":     page_recettes()
    elif page=="statistiques" and role=="medecin": page_statistiques()
    elif page=="admin":        page_admin()
    else: st.warning("Page non autorisée.")
