from app import db
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, Float, Boolean
import enum

class WorkflowStatus(enum.Enum):
    CREATED = "Créé"
    DER_GENERATED = "DER Généré"
    DER_SENT = "DER Envoyé"
    DER_SIGNED = "DER Signé"
    DOCUMENTS_UPLOADED = "Documents Téléchargés"
    QUESTIONNAIRE_COMPLETED = "Questionnaire Complété" 
    DOCUMENTS_GENERATED = "Documents Générés"
    DOCUMENTS_SENT = "Documents Envoyés"
    DOCUMENTS_SIGNED = "Documents Signés"
    SUBSCRIPTION_SENT = "Bulletins Envoyés"
    COMPLETED = "Terminé"

class RiskTolerance(enum.Enum):
    FAIBLE = "Faible"
    MOYENNE = "Moyenne"
    ELEVEE = "Élevée"

class InvestmentHorizon(enum.Enum):
    COURT = "Court terme (< 2 ans)"
    MOYEN = "Moyen terme (2-5 ans)"
    LONG = "Long terme (> 5 ans)"


# Nouveaux enums pour le profil investisseur complet
class TypeInvestisseur(enum.Enum):
    NON_PROFESSIONNEL = "Investisseur non-professionnel"
    PROFESSIONNEL = "Investisseur professionnel"
    CONTREPARTIE_ELIGIBLE = "Contrepartie éligible"

class NiveauConnaissance(enum.Enum):
    FAIBLE_BASIQUE = "Faible / basique"
    INVESTISSEUR_INFORME = "Investisseur informé"
    INVESTISSEUR_CONFIRME = "Investisseur confirmé"

class ClassificationSFDR(enum.Enum):
    ARTICLE_6 = "Article 6"
    ARTICLE_8 = "Article 8"
    ARTICLE_9 = "Article 9"

class TypeSouscripteur(enum.Enum):
    PERSONNE_PHYSIQUE = "Personne physique"
    PERSONNE_MORALE = "Personne morale"

class ObjectifInvestissement(enum.Enum):
    CONSTITUER_VALORISER = "Constituer / valoriser un patrimoine"
    TRANSMETTRE_CAPITAL = "Transmettre un capital"
    REVENUS_COMPLEMENTAIRES = "Revenus complémentaires"
    PREPARER_RETRAITE = "Préparer la retraite"
    OPTIMISER_RENTABILITE = "Optimiser la rentabilité"
    DIVERSIFIER_PATRIMOINE = "Diversifier son patrimoine"
    OPTIMISER_FISCALITE = "Optimiser la fiscalité des revenus"
    PROTEGER_CONJOINT = "Protéger le conjoint survivant"
    PROTEGER_PROCHES = "Protéger ses proches"
    SECURISER_CAPITAL = "Sécuriser / préserver un capital"
    EPARGNE_PRECAUTION = "Épargne de précaution"
    PLACER_LIQUIDITES = "Placer des liquidités à court terme"

class Client(db.Model):
    __tablename__ = 'clients'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Informations personnelles (DER)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    telephone = db.Column(db.String(20))
    date_naissance = db.Column(db.Date)
    adresse = db.Column(db.Text)
    ville = db.Column(db.String(100))
    profession = db.Column(db.String(100))
    
    # Informations financières
    revenus_mensuels = db.Column(db.Float)
    patrimoine_total = db.Column(db.Float)
    charges_mensuelles = db.Column(db.Float)
    
    # Profil investisseur (questionnaire)
    tolerance_risque = db.Column(db.Enum(RiskTolerance))
    horizon_investissement = db.Column(db.Enum(InvestmentHorizon))
    experience_financiere = db.Column(db.String(50))
    objectifs_investissement = db.Column(db.Text)
    profil_score = db.Column(db.Integer)  # Score de 1 à 7
    
    # Workflow
    statut_workflow = db.Column(db.Enum(WorkflowStatus), default=WorkflowStatus.CREATED)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_derniere_maj = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    date_entree_relation = db.Column(db.Date)
    
    # Suivi des signatures
    date_envoi_der = db.Column(db.DateTime)
    date_signature_der = db.Column(db.DateTime)
    date_envoi_documents = db.Column(db.DateTime)
    date_signature_documents = db.Column(db.DateTime)
    date_envoi_souscription = db.Column(db.DateTime)
    
    # Relations
    documents = db.relationship('Document', backref='client', lazy=True, cascade='all, delete-orphan')
    questionnaire_responses = db.relationship('QuestionnaireResponse', backref='client', lazy=True, cascade='all, delete-orphan')

class DocumentType(enum.Enum):
    # Documents KYC
    PIECE_IDENTITE = "Pièce d'identité"
    JUSTIFICATIF_DOMICILE = "Justificatif de domicile"
    AVIS_IMPOSITION = "Avis d'imposition"
    RELEVE_BANCAIRE = "Relevé bancaire"
    # Documents générés
    DER = "Document d'Entrée en Relation"
    RAPPORT_ADEQUATION = "Rapport d'adéquation"
    LETTRE_MISSION = "Lettre de mission"
    PROFIL_INVESTISSEUR = "Profil investisseur"
    KYC_DOCUMENT = "Document KYC"
    BULLETIN_SOUSCRIPTION = "Bulletin de souscription"
    AUTRE = "Autre"

class Document(db.Model):
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    nom_fichier = db.Column(db.String(255), nullable=False)
    nom_original = db.Column(db.String(255), nullable=False)
    type_document = db.Column(db.Enum(DocumentType), nullable=False)
    chemin_fichier = db.Column(db.String(500), nullable=False)
    taille_fichier = db.Column(db.Integer)
    date_upload = db.Column(db.DateTime, default=datetime.utcnow)
    genere_automatiquement = db.Column(db.Boolean, default=False)
    # Suivi signature
    date_envoi_signature = db.Column(db.DateTime)
    date_signature = db.Column(db.DateTime)
    signe = db.Column(db.Boolean, default=False)

class QuestionnaireResponse(db.Model):
    __tablename__ = 'questionnaire_responses'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    question_id = db.Column(db.String(50), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    reponse = db.Column(db.Text, nullable=False)
    score = db.Column(db.Integer, default=0)
    date_reponse = db.Column(db.DateTime, default=datetime.utcnow)

# Modèle pour les DER (Documents d'Entrée en Relation)
class DER(db.Model):
    __tablename__ = 'der'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_entree_relation = db.Column(db.Date, nullable=False)
    date_envoi_signature = db.Column(db.DateTime)
    date_signature = db.Column(db.DateTime)
    statut = db.Column(db.Enum(WorkflowStatus), default=WorkflowStatus.CREATED)
    fichier_path = db.Column(db.String(255))
    
    # Relations
    client = db.relationship('Client', backref='der_documents')

# Modèle pour les pièces justificatives
class PieceJustificative(db.Model):
    __tablename__ = 'pieces_justificatives'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    type_piece = db.Column(db.Enum(
        'PIECE_IDENTITE', 
        'AVIS_IMPOSITION', 
        'JUSTIFICATIF_DOMICILE', 
        'RELEVE_COMPTE',
        name='type_piece_enum'
    ), nullable=False)
    nom_fichier = db.Column(db.String(255), nullable=False)
    fichier_path = db.Column(db.String(255), nullable=False)
    date_upload = db.Column(db.DateTime, default=datetime.utcnow)
    date_validation = db.Column(db.DateTime)
    statut = db.Column(db.Enum(WorkflowStatus), default=WorkflowStatus.CREATED)
    commentaire = db.Column(db.Text)
    
    # Relations
    client = db.relationship('Client', backref='pieces_justificatives')

# Modèle pour les profils investisseur
class ProfilInvestisseur(db.Model):
    __tablename__ = 'profils_investisseur'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    
    # Type d'investisseur
    type_investisseur = db.Column(db.Enum(TypeInvestisseur), nullable=False)
    
    # Connaissance et expérience
    niveau_connaissance = db.Column(db.Enum(NiveauConnaissance), nullable=False)
    
    # Capacité financière et tolérance au risque
    garantie_capital = db.Column(db.Boolean, default=False)
    risque_perte_capital = db.Column(db.Boolean, default=False)
    perte_limitee_capital = db.Column(db.Boolean, default=False)
    perte_excedant_capital = db.Column(db.Boolean, default=False)
    rendement_garanti = db.Column(db.Boolean, default=False)
    risque_evolution_rendement = db.Column(db.Boolean, default=False)
    risque_liquidite = db.Column(db.Boolean, default=False)
    liquidite_immediate = db.Column(db.Boolean, default=False)
    
    # Tolérance au risque et durée d'investissement
    tolerance_risque = db.Column(db.Enum(RiskTolerance), nullable=False)
    srri_score = db.Column(db.Integer)  # Score SRRI (1-7)
    horizon_investissement = db.Column(db.Enum(InvestmentHorizon), nullable=False)
    duree_investissement_annees = db.Column(db.Integer)
    
    # Critères et risques liés à la durabilité
    classification_sfdr = db.Column(db.Enum(ClassificationSFDR))
    objectif_investissement_durable = db.Column(db.Boolean, default=False)
    caracteristiques_env_sociales_pct = db.Column(db.Numeric(5, 2))  # Pourcentage
    taxonomie_environnementale = db.Column(db.Text)
    incidences_negatives = db.Column(db.Text)  # Risques environnementaux/sociaux
    activites_negatives_exclues = db.Column(db.Text)  # Liste des risques interdits
    
    # Objectifs et besoins du client
    type_souscripteur = db.Column(db.Enum(TypeSouscripteur), nullable=False)
    objectifs_investissement = db.Column(db.Text)  # Peut contenir plusieurs objectifs
    
    # Informations financières existantes
    situation_financiere = db.Column(db.Text)
    experience_financiere = db.Column(db.Text)
    revenus_annuels = db.Column(db.Numeric(12, 2))
    patrimoine_total = db.Column(db.Numeric(12, 2))
    
    # Dates de suivi
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_mise_a_jour = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    client = db.relationship('Client', backref='profil_investisseur', uselist=False)

# Modèle pour les documents générés
class DocumentGenere(db.Model):
    __tablename__ = 'documents_generes'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    type_document = db.Column(db.Enum(
        'LETTRE_MISSION',
        'RAPPORT_ADEQUATION', 
        'PROFIL_INVESTISSEUR',
        'DOCUMENT_KYC',
        'BULLETIN_SOUSCRIPTION',
        name='type_document_enum'
    ), nullable=False)
    nom_fichier = db.Column(db.String(255), nullable=False)
    fichier_path = db.Column(db.String(255), nullable=False)
    date_generation = db.Column(db.DateTime, default=datetime.utcnow)
    date_envoi_signature = db.Column(db.DateTime)
    date_signature = db.Column(db.DateTime)
    statut = db.Column(db.Enum(WorkflowStatus), default=WorkflowStatus.CREATED)
    version = db.Column(db.Integer, default=1)
    
    # Relations
    client = db.relationship('Client', backref='documents_generes')

# Modèle pour le suivi du workflow
class SuiviWorkflow(db.Model):
    __tablename__ = 'suivi_workflow'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    etape_courante = db.Column(db.Enum(
        'DER_CREATION',
        'DER_SIGNATURE', 
        'UPLOAD_PIECES',
        'COMPLETION_KYC',
        'COMPLETION_PROFIL',
        'GENERATION_DOCUMENTS',
        'SIGNATURE_DOCUMENTS',
        'ENVOI_BULLETINS',
        'TERMINE',
        name='etape_workflow_enum'
    ), default='DER_CREATION')
    date_debut = db.Column(db.DateTime, default=datetime.utcnow)
    date_derniere_action = db.Column(db.DateTime, default=datetime.utcnow)
    date_fin = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    
    # Relations
    client = db.relationship('Client', backref='suivi_workflow', uselist=False)
