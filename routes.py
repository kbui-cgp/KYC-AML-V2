from flask import render_template, request, redirect, url_for, flash, send_file, jsonify
from werkzeug.utils import secure_filename
from app import app, db
from models import Client, Document, QuestionnaireResponse, WorkflowStatus, DocumentType, RiskTolerance, InvestmentHorizon, DER, PieceJustificative, ProfilInvestisseur, DocumentGenere, SuiviWorkflow
from document_generator import generate_investment_report, generate_mission_letter, generate_der_document, generate_kyc_document
import os
from datetime import datetime

# Configuration des extensions de fichiers autorisées
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def calculate_workflow_progress(client):
    """Calcule le pourcentage de progression du workflow pour un client"""
    if not client:
        return 0
    
    progress = 0
    total_steps = 6  # Nombre total d'étapes
    
    # Étape 1: Client créé (16.67%)
    if client.statut_workflow.name in ['CREATED', 'DER_GENERATED', 'DER_SENT', 'DER_SIGNED', 'DOCUMENTS_UPLOADED', 'QUESTIONNAIRE_COMPLETED', 'COMPLETED']:
        progress += 1
    
    # Étape 2: DER généré (33.33%)
    if client.statut_workflow.name in ['DER_GENERATED', 'DER_SENT', 'DER_SIGNED', 'DOCUMENTS_UPLOADED', 'QUESTIONNAIRE_COMPLETED', 'COMPLETED']:
        progress += 1
    
    # Étape 3: DER signé (50%)
    if client.statut_workflow.name in ['DER_SIGNED', 'DOCUMENTS_UPLOADED', 'QUESTIONNAIRE_COMPLETED', 'COMPLETED']:
        progress += 1
    
    # Étape 4: Documents téléchargés (66.67%) - Vérification réelle des 4 documents requis
    from models import Document, DocumentType
    documents = Document.query.filter_by(client_id=client.id).all()
    required_docs = [
        DocumentType.PIECE_IDENTITE,
        DocumentType.AVIS_IMPOSITION,
        DocumentType.JUSTIFICATIF_DOMICILE,
        DocumentType.RELEVE_BANCAIRE
    ]
    uploaded_doc_types = [doc.type_document for doc in documents]
    required_docs_count = sum(1 for doc_type in required_docs if doc_type in uploaded_doc_types)
    all_required_uploaded = required_docs_count == 4
    
    if all_required_uploaded:
        progress += 1
        # Mettre à jour automatiquement le statut si tous les documents sont téléchargés
        if client.statut_workflow.name == 'DER_SIGNED':
            client.statut_workflow = WorkflowStatus.DOCUMENTS_UPLOADED
            from app import db
            db.session.commit()
    
    # Étape 5: Questionnaire complété (83.33%) - Vérification réelle du profil investisseur
    from models import ProfilInvestisseur
    profil = ProfilInvestisseur.query.filter_by(client_id=client.id).first()
    if profil:
        progress += 1
        # Mettre à jour automatiquement le statut si le questionnaire est complété
        if client.statut_workflow.name == 'DOCUMENTS_UPLOADED':
            client.statut_workflow = WorkflowStatus.QUESTIONNAIRE_COMPLETED
            from app import db
            db.session.commit()
    
    # Étape 6: Processus terminé (100%) - Mettre à jour automatiquement si toutes les étapes sont complètes
    if progress == 5 and client.statut_workflow.name != 'COMPLETED':
        client.statut_workflow = WorkflowStatus.COMPLETED
        from app import db
        db.session.commit()
        progress += 1
    elif client.statut_workflow.name == 'COMPLETED':
        progress += 1
    
    return round((progress / total_steps) * 100)


@app.route('/')
def index():
    """Page d'accueil avec statistiques"""
    total_clients = Client.query.count()
    clients_en_cours = Client.query.filter(Client.statut_workflow != WorkflowStatus.COMPLETED).count()
    clients_completes = Client.query.filter_by(statut_workflow=WorkflowStatus.COMPLETED).count()
    
    clients_recents = Client.query.order_by(Client.date_creation.desc()).limit(5).all()
    
    return render_template('index.html', 
                         total_clients=total_clients,
                         clients_en_cours=clients_en_cours,
                         clients_completes=clients_completes,
                         clients_recents=clients_recents)

@app.route('/onboarding', methods=['GET', 'POST'])
def client_onboarding():
    """Formulaire d'accueil client (DER)"""
    if request.method == 'POST':
        try:
            client = Client(
                nom=request.form['nom'].strip().upper(),
                prenom=request.form['prenom'].strip().title(),
                email=request.form['email'].strip().lower(),
                telephone=request.form.get('telephone', '').strip(),
                date_naissance=datetime.strptime(request.form['date_naissance'], '%Y-%m-%d').date() if request.form.get('date_naissance') else None,
                adresse=request.form.get('adresse', '').strip(),
                ville=request.form.get('ville', '').strip(),
                profession=request.form.get('profession', '').strip(),
                revenus_mensuels=float(request.form['revenus_mensuels']) if request.form.get('revenus_mensuels') else None,
                patrimoine_total=float(request.form['patrimoine_total']) if request.form.get('patrimoine_total') else None,
                charges_mensuelles=float(request.form['charges_mensuelles']) if request.form.get('charges_mensuelles') else None,
                date_entree_relation=datetime.strptime(request.form['date_entree_relation'], '%Y-%m-%d').date() if request.form.get('date_entree_relation') else datetime.now().date(),
                statut_workflow=WorkflowStatus.CREATED
            )
            
            db.session.add(client)
            db.session.commit()
            
            # Générer automatiquement le DER
            der_path = generate_der_document(client)
            if der_path:
                der_doc = Document(
                    client_id=client.id,
                    nom_fichier=os.path.basename(der_path),
                    nom_original=f"DER_{client.nom}_{client.prenom}.docx",
                    type_document=DocumentType.DER,
                    chemin_fichier=der_path,
                    taille_fichier=os.path.getsize(der_path),
                    genere_automatiquement=True
                )
                db.session.add(der_doc)
                client.statut_workflow = WorkflowStatus.DER_GENERATED
                db.session.commit()
                
                flash(f'Client {client.prenom} {client.nom} créé avec succès! DER généré automatiquement.', 'success')
            else:
                flash(f'Client créé mais erreur lors de la génération du DER.', 'warning')
            
            return redirect(url_for('client_details', client_id=client.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la création du client: {str(e)}', 'error')
    
    return render_template('client_onboarding.html')

@app.route('/upload_documents/<int:client_id>', methods=['GET', 'POST'])
def upload_documents(client_id):
    """Interface de téléchargement des documents KYC"""
    client = Client.query.get_or_404(client_id)
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Aucun fichier sélectionné', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        document_type = request.form.get('document_type')
        
        if file.filename == '':
            flash('Aucun fichier sélectionné', 'error')
            return redirect(request.url)
        
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Créer un nom unique pour éviter les conflits
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{client_id}_{timestamp}_{filename}"
            
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Enregistrer le document en base
            document = Document(
                client_id=client_id,
                nom_fichier=filename,
                nom_original=file.filename,
                type_document=DocumentType(document_type),
                chemin_fichier=filepath,
                taille_fichier=os.path.getsize(filepath)
            )
            
            db.session.add(document)
            
            # Mettre à jour le statut du workflow si nécessaire
            if client.statut_workflow == WorkflowStatus.DER_SIGNED:
                # Vérifier si tous les 4 documents obligatoires sont téléchargés
                required_docs = [
                    DocumentType.PIECE_IDENTITE,
                    DocumentType.JUSTIFICATIF_DOMICILE,
                    DocumentType.AVIS_IMPOSITION,
                    DocumentType.RELEVE_BANCAIRE
                ]
                
                uploaded_doc_types = [doc.type_document for doc in Document.query.filter_by(client_id=client_id, genere_automatiquement=False).all()]
                
                if all(doc_type in uploaded_doc_types for doc_type in required_docs):
                    client.statut_workflow = WorkflowStatus.DOCUMENTS_UPLOADED
            db.session.commit()
            flash('Document téléchargé avec succès!', 'success')
        else:
            flash('Type de fichier non autorisé', 'error')
    
    documents = Document.query.filter_by(client_id=client_id, genere_automatiquement=False).all()
    
    # Calculer la progression des documents obligatoires
    required_docs = [
        DocumentType.PIECE_IDENTITE,
        DocumentType.JUSTIFICATIF_DOMICILE,
        DocumentType.AVIS_IMPOSITION,
        DocumentType.RELEVE_BANCAIRE
    ]
    
    uploaded_doc_types = [doc.type_document for doc in documents]
    required_docs_count = sum(1 for doc_type in required_docs if doc_type in uploaded_doc_types)
    all_required_uploaded = required_docs_count == 4
    
    # Utiliser la fonction de calcul de progression cohérente
    workflow_progress = calculate_workflow_progress(client)
    
    return render_template('upload_documents.html', 
                         client=client, 
                         documents=documents, 
                         DocumentType=DocumentType,
                         required_docs_count=required_docs_count,
                         all_required_uploaded=all_required_uploaded,
                         workflow_progress=workflow_progress)

@app.route('/questionnaire/<int:client_id>', methods=['GET', 'POST'])
def questionnaire(client_id):
    """Questionnaire profil investisseur interactif"""
    client = Client.query.get_or_404(client_id)
    
    if request.method == 'POST':
        try:
            # Supprimer les anciennes réponses
            QuestionnaireResponse.query.filter_by(client_id=client_id).delete()
            
            total_score = 0
            questions_data = [
                {'id': 'q1', 'text': 'Quelle est votre expérience en matière d\'investissement?', 'scores': {'debutant': 1, 'intermediaire': 3, 'avance': 5}},
                {'id': 'q2', 'text': 'Quel est votre horizon d\'investissement principal?', 'scores': {'court': 1, 'moyen': 3, 'long': 5}},
                {'id': 'q3', 'text': 'Comment réagissez-vous face aux fluctuations du marché?', 'scores': {'vente_panique': 1, 'inquiet': 2, 'attente': 3, 'opportunite': 4, 'achats': 5}},
                {'id': 'q4', 'text': 'Quel pourcentage de votre patrimoine souhaitez-vous investir?', 'scores': {'moins_10': 1, '10_25': 2, '25_50': 3, '50_75': 4, 'plus_75': 5}},
                {'id': 'q5', 'text': 'Quel est votre objectif principal d\'investissement?', 'scores': {'preservation': 1, 'revenus': 2, 'croissance_moderee': 3, 'croissance': 4, 'croissance_aggressive': 5}},
            ]
            
            # Enregistrer les réponses et calculer le score
            for question in questions_data:
                reponse = request.form.get(question['id'])
                if reponse:
                    score = question['scores'].get(reponse, 0)
                    total_score += score
                    
                    response = QuestionnaireResponse(
                        client_id=client_id,
                        question_id=question['id'],
                        question_text=question['text'],
                        reponse=reponse,
                        score=score
                    )
                    db.session.add(response)
            
            # Déterminer le profil basé sur le score total
            if total_score <= 7:
                tolerance_risque = RiskTolerance.FAIBLE
                profil_score = 1
            elif total_score <= 14:
                tolerance_risque = RiskTolerance.MOYENNE
                profil_score = 3
            else:
                tolerance_risque = RiskTolerance.ELEVEE
                profil_score = 5
            
            # Déterminer l'horizon basé sur la réponse à la question 2
            horizon_reponse = request.form.get('q2')
            if horizon_reponse == 'court':
                horizon = InvestmentHorizon.COURT
            elif horizon_reponse == 'moyen':
                horizon = InvestmentHorizon.MOYEN
            else:
                horizon = InvestmentHorizon.LONG
            
            # Mettre à jour le client
            client.tolerance_risque = tolerance_risque
            client.horizon_investissement = horizon
            client.profil_score = profil_score
            client.experience_financiere = request.form.get('q1', '')
            client.objectifs_investissement = request.form.get('q5', '')
            client.statut_workflow = WorkflowStatus.QUESTIONNAIRE_COMPLETED
            
            db.session.commit()
            flash(f'Questionnaire complété! Profil de risque: {tolerance_risque.value}', 'success')
            return redirect(url_for('generate_documents', client_id=client_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de l\'enregistrement: {str(e)}', 'error')
    
    return render_template('questionnaire.html', client=client)

    
    return redirect(url_for('client_details', client_id=client_id))

@app.route('/dashboard')
def dashboard():
    """Tableau de bord des clients"""
    clients = Client.query.order_by(Client.date_derniere_maj.desc()).all()
    return render_template('dashboard.html', clients=clients, WorkflowStatus=WorkflowStatus)

@app.route('/client/<int:client_id>')
def client_details(client_id):
    """Détails d'un client"""
    client = Client.query.get_or_404(client_id)
    documents = Document.query.filter_by(client_id=client_id).all()
    responses = QuestionnaireResponse.query.filter_by(client_id=client_id).all()
    
    # Calculer la progression du workflow
    progress = calculate_workflow_progress(client)
    
    return render_template('client_details.html', 
                         client=client, 
                         documents=documents, 
                         responses=responses,
                         DocumentType=DocumentType,
                         progress=progress)

@app.route('/download/<int:document_id>')
def download_document(document_id):
    """Téléchargement d'un document"""
    document = Document.query.get_or_404(document_id)
    
    if os.path.exists(document.chemin_fichier):
        return send_file(document.chemin_fichier, 
                        as_attachment=True, 
                        download_name=document.nom_original)
    else:
        flash('Fichier introuvable', 'error')
        return redirect(url_for('dashboard'))

@app.route('/send_der/<int:client_id>')
def send_der_signature(client_id):
    """Envoyer le DER en signature"""
    client = Client.query.get_or_404(client_id)
    if client.statut_workflow == WorkflowStatus.DER_GENERATED:
        client.statut_workflow = WorkflowStatus.DER_SENT
        client.date_envoi_der = datetime.utcnow()
        db.session.commit()
        flash(f'DER envoyé en signature pour {client.prenom} {client.nom}', 'success')
    else:
        flash('Impossible d\'envoyer le DER dans cet état', 'error')
    return redirect(url_for('client_details', client_id=client_id))

@app.route('/confirm_der_signed/<int:client_id>')
def confirm_der_signed(client_id):
    """Confirmer la signature du DER"""
    client = Client.query.get_or_404(client_id)
    if client.statut_workflow == WorkflowStatus.DER_SENT:
        client.statut_workflow = WorkflowStatus.DER_SIGNED
        client.date_signature_der = datetime.utcnow()
        db.session.commit()
        flash(f'DER signé confirmé pour {client.prenom} {client.nom}. Vous pouvez maintenant demander les documents KYC.', 'success')
    else:
        flash('Impossible de confirmer la signature dans cet état', 'error')
    return redirect(url_for('client_details', client_id=client_id))

@app.route('/generate_final_documents/<int:client_id>')
def generate_final_documents(client_id):
    """Générer tous les documents finaux pour signature"""
    client = Client.query.get_or_404(client_id)
    
    if client.statut_workflow != WorkflowStatus.QUESTIONNAIRE_COMPLETED:
        flash('Le questionnaire doit être complété avant de générer les documents finaux', 'error')
        return redirect(url_for('client_details', client_id=client_id))
    
    try:
        documents_generated = []
        
        # Générer le rapport d'adéquation
        rapport_path = generate_investment_report(client)
        if rapport_path:
            rapport_doc = Document(
                client_id=client_id,
                nom_fichier=os.path.basename(rapport_path),
                nom_original=f"Rapport_adequation_{client.nom}_{client.prenom}.docx",
                type_document=DocumentType.RAPPORT_ADEQUATION,
                chemin_fichier=rapport_path,
                taille_fichier=os.path.getsize(rapport_path),
                genere_automatiquement=True
            )
            db.session.add(rapport_doc)
            documents_generated.append("Rapport d'adéquation")
        
        # Générer la lettre de mission
        lettre_path = generate_mission_letter(client)
        if lettre_path:
            lettre_doc = Document(
                client_id=client_id,
                nom_fichier=os.path.basename(lettre_path),
                nom_original=f"Lettre_mission_{client.nom}_{client.prenom}.docx",
                type_document=DocumentType.LETTRE_MISSION,
                chemin_fichier=lettre_path,
                taille_fichier=os.path.getsize(lettre_path),
                genere_automatiquement=True
            )
            db.session.add(lettre_doc)
            documents_generated.append("Lettre de mission")
        
        # Générer le document KYC compilé
        kyc_path = generate_kyc_document(client)
        if kyc_path:
            kyc_doc = Document(
                client_id=client_id,
                nom_fichier=os.path.basename(kyc_path),
                nom_original=f"KYC_{client.nom}_{client.prenom}.docx",
                type_document=DocumentType.KYC_DOCUMENT,
                chemin_fichier=kyc_path,
                taille_fichier=os.path.getsize(kyc_path),
                genere_automatiquement=True
            )
            db.session.add(kyc_doc)
            documents_generated.append("Document KYC")
        
        # Mettre à jour le statut
        client.statut_workflow = WorkflowStatus.DOCUMENTS_GENERATED
        db.session.commit()
        
        flash(f'Documents générés avec succès: {", ".join(documents_generated)}', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la génération des documents: {str(e)}', 'error')
    
    return redirect(url_for('client_details', client_id=client_id))

@app.route('/send_documents_signature/<int:client_id>')
def send_documents_signature(client_id):
    """Envoyer tous les documents en signature"""
    client = Client.query.get_or_404(client_id)
    if client.statut_workflow == WorkflowStatus.DOCUMENTS_GENERATED:
        client.statut_workflow = WorkflowStatus.DOCUMENTS_SENT
        client.date_envoi_documents = datetime.utcnow()
        
        # Marquer tous les documents générés automatiquement comme envoyés en signature
        documents = Document.query.filter_by(client_id=client_id, genere_automatiquement=True).all()
        for doc in documents:
            if not doc.date_envoi_signature:
                doc.date_envoi_signature = datetime.utcnow()
        
        db.session.commit()
        flash(f'Documents envoyés en signature pour {client.prenom} {client.nom}', 'success')
    else:
        flash('Impossible d\'envoyer les documents dans cet état', 'error')
    return redirect(url_for('client_details', client_id=client_id))

@app.route('/confirm_documents_signed/<int:client_id>')
def confirm_documents_signed(client_id):
    """Confirmer la signature de tous les documents"""
    client = Client.query.get_or_404(client_id)
    if client.statut_workflow == WorkflowStatus.DOCUMENTS_SENT:
        client.statut_workflow = WorkflowStatus.DOCUMENTS_SIGNED
        client.date_signature_documents = datetime.utcnow()
        
        # Marquer tous les documents comme signés
        documents = Document.query.filter_by(client_id=client_id, genere_automatiquement=True).all()
        for doc in documents:
            doc.date_signature = datetime.utcnow()
            doc.signe = True
        
        db.session.commit()
        flash(f'Signature des documents confirmée pour {client.prenom} {client.nom}. Vous pouvez maintenant envoyer les bulletins de souscription.', 'success')
    else:
        flash('Impossible de confirmer la signature dans cet état', 'error')
    return redirect(url_for('client_details', client_id=client_id))

@app.route('/send_subscription_forms/<int:client_id>')
def send_subscription_forms(client_id):
    """Envoyer les bulletins de souscription"""
    client = Client.query.get_or_404(client_id)
    if client.statut_workflow == WorkflowStatus.DOCUMENTS_SIGNED:
        client.statut_workflow = WorkflowStatus.SUBSCRIPTION_SENT
        client.date_envoi_souscription = datetime.utcnow()
        db.session.commit()
        flash(f'Bulletins de souscription envoyés pour {client.prenom} {client.nom}', 'success')
    else:
        flash('Impossible d\'envoyer les bulletins dans cet état', 'error')
    return redirect(url_for('client_details', client_id=client_id))

@app.route('/complete_workflow/<int:client_id>')
def complete_workflow(client_id):
    """Marquer le workflow comme terminé"""
    client = Client.query.get_or_404(client_id)
    client.statut_workflow = WorkflowStatus.COMPLETED
    db.session.commit()
    flash(f'Workflow terminé pour {client.prenom} {client.nom}', 'success')
    return redirect(url_for('client_details', client_id=client_id))

@app.route('/auto_send_der/<int:client_id>')
def auto_send_der(client_id):
    """Envoi automatique du DER pour signature"""
    try:
        client = Client.query.get_or_404(client_id)
        
        # Créer l'enregistrement DER
        der = DER(
            client_id=client.id,
            date_entree_relation=client.date_entree_relation or datetime.now().date(),
            date_envoi_signature=datetime.now(),
            statut='EN_ATTENTE'
        )
        
        # Créer ou mettre à jour le suivi workflow
        suivi = SuiviWorkflow.query.filter_by(client_id=client.id).first()
        if not suivi:
            suivi = SuiviWorkflow(
                client_id=client.id,
                etape_courante='DER_SIGNATURE',
                date_derniere_action=datetime.now()
            )
            db.session.add(suivi)
        else:
            suivi.etape_courante = 'DER_SIGNATURE'
            suivi.date_derniere_action = datetime.now()
        
        db.session.add(der)
        client.statut_workflow = WorkflowStatus.DER_SENT
        db.session.commit()
        
        flash(f'DER envoyé en signature pour {client.prenom} {client.nom}', 'success')
        return redirect(url_for('client_details', client_id=client.id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de l\'envoi du DER: {str(e)}', 'error')
        return redirect(url_for('client_details', client_id=client.id))

@app.route('/confirm_der_signature/<int:client_id>')
def confirm_der_signature(client_id):
    """Confirmation de signature du DER et passage à l'étape suivante"""
    try:
        client = Client.query.get_or_404(client_id)
        der = DER.query.filter_by(client_id=client.id).first()
        
        if der:
            der.date_signature = datetime.now()
            der.statut = 'SIGNE'
        
        # Mettre à jour le suivi workflow
        suivi = SuiviWorkflow.query.filter_by(client_id=client.id).first()
        if suivi:
            suivi.etape_courante = 'UPLOAD_PIECES'
            suivi.date_derniere_action = datetime.now()
        
        client.statut_workflow = WorkflowStatus.DER_SIGNED
        db.session.commit()
        
        flash(f'Signature DER confirmée pour {client.prenom} {client.nom}. Le client peut maintenant charger ses pièces justificatives.', 'success')
        return redirect(url_for('client_details', client_id=client.id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la confirmation: {str(e)}', 'error')
        return redirect(url_for('client_details', client_id=client.id))

@app.route('/upload_piece_justificative/<int:client_id>', methods=['GET', 'POST'])
def upload_piece_justificative(client_id):
    """Upload des pièces justificatives requises"""
    client = Client.query.get_or_404(client_id)
    
    if request.method == 'POST':
        try:
            type_piece = request.form.get('type_piece')
            file = request.files.get('file')
            
            if not file or not allowed_file(file.filename):
                flash('Fichier non valide', 'error')
                return redirect(request.url)
            
            # Sauvegarder le fichier
            filename = secure_filename(f"{type_piece}_{client.nom}_{client.prenom}_{file.filename}")
            upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(upload_path)
            
            # Créer l'enregistrement
            piece = PieceJustificative(
                client_id=client.id,
                type_piece=type_piece,
                nom_fichier=filename,
                fichier_path=upload_path,
                statut='EN_ATTENTE'
            )
            
            db.session.add(piece)
            
            # Vérifier si toutes les pièces sont uploadées
            pieces_requises = ['PIECE_IDENTITE', 'AVIS_IMPOSITION', 'JUSTIFICATIF_DOMICILE', 'RELEVE_COMPTE']
            pieces_client = PieceJustificative.query.filter_by(client_id=client.id).all()
            types_uploaded = [p.type_piece for p in pieces_client]
            
            if all(piece_type in types_uploaded for piece_type in pieces_requises):
                # Toutes les pièces sont uploadées, passer à l'étape suivante
                suivi = SuiviWorkflow.query.filter_by(client_id=client.id).first()
                if suivi:
                    suivi.etape_courante = 'COMPLETION_KYC'
                    suivi.date_derniere_action = datetime.now()
                
                client.statut_workflow = WorkflowStatus.DOCUMENTS_UPLOADED
                flash('Toutes les pièces justificatives ont été uploadées. Vous pouvez maintenant compléter le KYC.', 'success')
            else:
                flash(f'Pièce {type_piece} uploadée avec succès.', 'success')
            
            db.session.commit()
            return redirect(url_for('client_details', client_id=client.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de l\'upload: {str(e)}', 'error')
    
    # Récupérer les pièces déjà uploadées
    pieces_existantes = PieceJustificative.query.filter_by(client_id=client.id).all()
    pieces_requises = [
        ('PIECE_IDENTITE', 'Pièce d\'identité'),
        ('AVIS_IMPOSITION', 'Avis d\'imposition année en cours'),
        ('JUSTIFICATIF_DOMICILE', 'Justificatif de domicile < 3 mois'),
        ('RELEVE_COMPTE', 'Relevé de comptes 3 derniers mois')
    ]
    
    return render_template('upload_pieces.html', 
                         client=client, 
                         pieces_existantes=pieces_existantes,
                         pieces_requises=pieces_requises)

@app.route('/download_piece/<int:piece_id>')
def download_piece(piece_id):
    """Télécharger une pièce justificative"""
    piece = PieceJustificative.query.get_or_404(piece_id)
    
    try:
        return send_file(
            piece.fichier_path,
            as_attachment=True,
            download_name=piece.nom_fichier
        )
    except FileNotFoundError:
        flash('Fichier non trouvé', 'error')
        return redirect(url_for('client_details', client_id=piece.client_id))

@app.route('/complete_kyc/<int:client_id>', methods=['GET', 'POST'])
def complete_kyc(client_id):
    """Complétion du KYC et profil investisseur"""
    client = Client.query.get_or_404(client_id)
    
    # Vérifier que toutes les pièces sont uploadées
    pieces_requises = ['PIECE_IDENTITE', 'AVIS_IMPOSITION', 'JUSTIFICATIF_DOMICILE', 'RELEVE_COMPTE']
    pieces_client = PieceJustificative.query.filter_by(client_id=client.id).all()
    types_uploaded = [p.type_piece for p in pieces_client]
    
    if not all(piece_type in types_uploaded for piece_type in pieces_requises):
        flash('Toutes les pièces justificatives doivent être uploadées avant de compléter le KYC', 'error')
        return redirect(url_for('upload_piece_justificative', client_id=client.id))
    
    if request.method == 'POST':
        try:
            # Données KYC
            # Créer ou mettre à jour le profil investisseur
            profil = ProfilInvestisseur.query.filter_by(client_id=client.id).first()
            if not profil:
                profil = ProfilInvestisseur(client_id=client.id)
                db.session.add(profil)
            
            # Type d'investisseur
            type_inv = request.form.get('type_investisseur')
            if type_inv:
                profil.type_investisseur = TypeInvestisseur(type_inv)
            
            # Connaissance et expérience
            niveau_conn = request.form.get('niveau_connaissance')
            if niveau_conn:
                profil.niveau_connaissance = NiveauConnaissance(niveau_conn)
            
            # Capacité financière et tolérance au risque
            profil.garantie_capital = request.form.get('garantie_capital') == 'on'
            profil.risque_perte_capital = request.form.get('risque_perte_capital') == 'on'
            profil.perte_limitee_capital = request.form.get('perte_limitee_capital') == 'on'
            profil.perte_excedant_capital = request.form.get('perte_excedant_capital') == 'on'
            profil.rendement_garanti = request.form.get('rendement_garanti') == 'on'
            profil.risque_evolution_rendement = request.form.get('risque_evolution_rendement') == 'on'
            profil.risque_liquidite = request.form.get('risque_liquidite') == 'on'
            profil.liquidite_immediate = request.form.get('liquidite_immediate') == 'on'
            
            # Tolérance au risque et durée d'investissement
            tolerance = request.form.get('tolerance_risque')
            if tolerance:
                profil.tolerance_risque = RiskTolerance(tolerance)
            
            srri = request.form.get('srri_score')
            if srri:
                profil.srri_score = int(srri)
            
            horizon = request.form.get('horizon_investissement')
            if horizon:
                profil.horizon_investissement = InvestmentHorizon(horizon)
            
            duree = request.form.get('duree_investissement_annees')
            if duree:
                profil.duree_investissement_annees = int(duree)
            
            # Critères et risques liés à la durabilité
            sfdr = request.form.get('classification_sfdr')
            if sfdr:
                profil.classification_sfdr = ClassificationSFDR(sfdr)
            
            profil.objectif_investissement_durable = request.form.get('objectif_investissement_durable') == 'on'
            
            pct_env = request.form.get('caracteristiques_env_sociales_pct')
            if pct_env:
                profil.caracteristiques_env_sociales_pct = float(pct_env)
            
            profil.taxonomie_environnementale = request.form.get('taxonomie_environnementale')
            profil.incidences_negatives = request.form.get('incidences_negatives')
            profil.activites_negatives_exclues = request.form.get('activites_negatives_exclues')
            
            # Objectifs et besoins du client
            type_sous = request.form.get('type_souscripteur')
            if type_sous:
                profil.type_souscripteur = TypeSouscripteur(type_sous)
            
            # Objectifs d'investissement (multiple selection)
            objectifs_selected = request.form.getlist('objectifs_investissement')
            profil.objectifs_investissement = ','.join(objectifs_selected)
            
            # Informations financières existantes
            profil.situation_financiere = request.form.get('situation_financiere')
            profil.experience_financiere = request.form.get('experience_financiere')
            
            revenus = request.form.get('revenus_annuels')
            if revenus:
                profil.revenus_annuels = float(revenus)
            
            patrimoine = request.form.get('patrimoine_total')
            if patrimoine:
                profil.patrimoine_total = float(patrimoine)
            
            profil.date_mise_a_jour = datetime.now()
            
            
            # Mettre à jour le statut du client
            client.statut_workflow = WorkflowStatus.QUESTIONNAIRE_COMPLETED
            
            # Mettre à jour le suivi workflow
            suivi = SuiviWorkflow.query.filter_by(client_id=client.id).first()
            if suivi:
                suivi.etape_courante = 'GENERATION_DOCUMENTS'
                suivi.date_derniere_action = datetime.now()
                suivi.kyc_complete = True
                suivi.date_completion_kyc = datetime.now()
            
            db.session.commit()
            
            flash('KYC et profil investisseur complétés avec succès', 'success')
            return redirect(url_for('generate_documents', client_id=client.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la sauvegarde: {str(e)}', 'error')
    
    # Récupérer le profil existant s'il y en a un
    profil = ProfilInvestisseur.query.filter_by(client_id=client.id).first()
    
    return render_template('complete_kyc.html', client=client, profil=profil)

@app.route('/generate_documents/<int:client_id>')
def generate_documents(client_id):
    """Génération automatique des documents après KYC"""
    client = Client.query.get_or_404(client_id)
    profil = ProfilInvestisseur.query.filter_by(client_id=client.id).first()
    
    if not profil:
        flash('Le KYC doit être complété avant de générer les documents', 'error')
        return redirect(url_for('complete_kyc', client_id=client.id))
    
    try:
        documents_generes = []
        
        # 1. Lettre de mission
        lettre_mission_path = generate_mission_letter(client, profil)
        if lettre_mission_path:
            doc_lettre = DocumentGenere(
                client_id=client.id,
                type_document='LETTRE_MISSION',
                nom_fichier=f'lettre_mission_{client.nom}_{client.prenom}.docx',
                fichier_path=lettre_mission_path,
                statut='GENERE'
            )
            db.session.add(doc_lettre)
            documents_generes.append('Lettre de mission')
        
        # 2. Rapport d'adéquation
        rapport_adequation_path = generate_investment_report(client, profil)
        if rapport_adequation_path:
            doc_rapport = DocumentGenere(
                client_id=client.id,
                type_document='RAPPORT_ADEQUATION',
                nom_fichier=f'rapport_adequation_{client.nom}_{client.prenom}.docx',
                fichier_path=rapport_adequation_path,
                statut='GENERE'
            )
            db.session.add(doc_rapport)
            documents_generes.append('Rapport d\'adéquation')
        
        # 3. Document KYC
        kyc_doc_path = generate_kyc_document(client, profil)
        if kyc_doc_path:
            doc_kyc = DocumentGenere(
                client_id=client.id,
                type_document='DOCUMENT_KYC',
                nom_fichier=f'kyc_{client.nom}_{client.prenom}.docx',
                fichier_path=kyc_doc_path,
                statut='GENERE'
            )
            db.session.add(doc_kyc)
            documents_generes.append('Document KYC')
        
        # 4. Profil investisseur
        profil_doc_path = generate_investor_profile(client, profil)
        if profil_doc_path:
            doc_profil = DocumentGenere(
                client_id=client.id,
                type_document='PROFIL_INVESTISSEUR',
                nom_fichier=f'profil_investisseur_{client.nom}_{client.prenom}.docx',
                fichier_path=profil_doc_path,
                statut='GENERE'
            )
            db.session.add(doc_profil)
            documents_generes.append('Profil investisseur')
        
        # Mettre à jour le statut
        client.statut_workflow = WorkflowStatus.DOCUMENTS_GENERATED
        
        # Mettre à jour le suivi
        suivi = SuiviWorkflow.query.filter_by(client_id=client.id).first()
        if suivi:
            suivi.etape_courante = 'ENVOI_SIGNATURE'
            suivi.date_derniere_action = datetime.now()
            suivi.documents_generes = True
            suivi.date_generation_documents = datetime.now()
        
        db.session.commit()
        
        flash(f'Documents générés avec succès: {", ".join(documents_generes)}', 'success')
        return redirect(url_for('send_for_signature', client_id=client.id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la génération des documents: {str(e)}', 'error')
        return redirect(url_for('client_details', client_id=client.id))

@app.route('/send_for_signature/<int:client_id>')
def send_for_signature(client_id):
    """Envoi des documents pour signature"""
    client = Client.query.get_or_404(client_id)
    documents = DocumentGenere.query.filter_by(client_id=client.id).all()
    
    if not documents:
        flash('Aucun document à envoyer pour signature', 'error')
        return redirect(url_for('generate_documents', client_id=client.id))
    
    try:
        # Marquer les documents comme envoyés pour signature
        for doc in documents:
            if doc.statut == 'GENERE':
                doc.statut = 'ENVOYE_SIGNATURE'
                doc.date_envoi_signature = datetime.now()
        
        # Mettre à jour le statut du client
        client.statut_workflow = WorkflowStatus.PENDING_SIGNATURE
        
        # Mettre à jour le suivi
        suivi = SuiviWorkflow.query.filter_by(client_id=client.id).first()
        if suivi:
            suivi.etape_courante = 'ATTENTE_SIGNATURE'
            suivi.date_derniere_action = datetime.now()
            suivi.documents_envoyes_signature = True
            suivi.date_envoi_signature = datetime.now()
        
        db.session.commit()
        
        flash(f'{len(documents)} documents envoyés pour signature', 'success')
        return render_template('documents_signature.html', client=client, documents=documents)
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de l\'envoi: {str(e)}', 'error')
        return redirect(url_for('client_details', client_id=client.id))
