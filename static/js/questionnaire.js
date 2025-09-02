/**
 * Questionnaire Profil Investisseur - JavaScript Interactif
 * Calcul en temps réel du profil de risque et validation
 */

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('questionnaireForm');
    const resultsCard = document.getElementById('resultsCard');
    const scoreDisplay = document.getElementById('scoreDisplay');
    const profilDescription = document.getElementById('profilDescription');
    
    // Scores pour chaque réponse
    const questionScores = {
        'q1': {
            'debutant': 1,
            'intermediaire': 3,
            'avance': 5
        },
        'q2': {
            'court': 1,
            'moyen': 3,
            'long': 5
        },
        'q3': {
            'vente_panique': 1,
            'inquiet': 2,
            'attente': 3,
            'opportunite': 4,
            'achats': 5
        },
        'q4': {
            'moins_10': 1,
            '10_25': 2,
            '25_50': 3,
            '50_75': 4,
            'plus_75': 5
        },
        'q5': {
            'preservation': 1,
            'revenus': 2,
            'croissance_moderee': 3,
            'croissance': 4,
            'croissance_aggressive': 5
        }
    };
    
    // Descriptions des profils
    const profilDescriptions = {
        'prudent': {
            name: 'Profil Prudent',
            description: 'Investisseur privilégiant la sécurité du capital',
            color: 'success',
            recommendations: [
                'Fonds euros et obligations d\'État',
                'Maximum 20% d\'actifs risqués',
                'Épargne réglementée pour la liquidité'
            ]
        },
        'equilibre': {
            name: 'Profil Équilibré',
            description: 'Investisseur recherchant un compromis rendement/risque',
            color: 'warning',
            recommendations: [
                'Mix 60% sécurité / 40% croissance',
                'Fonds mixtes diversifiés',
                'SCPI et immobilier locatif'
            ]
        },
        'dynamique': {
            name: 'Profil Dynamique',
            description: 'Investisseur orienté croissance à long terme',
            color: 'danger',
            recommendations: [
                '70% d\'actifs de croissance',
                'Actions européennes et internationales',
                'Produits structurés et thématiques'
            ]
        }
    };
    
    // Fonction de calcul du score total
    function calculateTotalScore() {
        let totalScore = 0;
        let answeredQuestions = 0;
        
        for (let questionId in questionScores) {
            const selectedInput = document.querySelector(`input[name="${questionId}"]:checked`);
            if (selectedInput) {
                const answerValue = selectedInput.value;
                const score = questionScores[questionId][answerValue] || 0;
                totalScore += score;
                answeredQuestions++;
            }
        }
        
        return {
            total: totalScore,
            answered: answeredQuestions,
            maxPossible: Object.keys(questionScores).length * 5
        };
    }
    
    // Fonction de détermination du profil
    function determineProfile(score) {
        if (score <= 7) {
            return 'prudent';
        } else if (score <= 14) {
            return 'equilibre';
        } else {
            return 'dynamique';
        }
    }
    
    // Fonction de mise à jour de l'affichage
    function updateResults() {
        const scoreData = calculateTotalScore();
        const profileType = determineProfile(scoreData.total);
        const profile = profilDescriptions[profileType];
        
        // Afficher la carte de résultats si au moins une question est répondue
        if (scoreData.answered > 0) {
            resultsCard.style.display = 'block';
            resultsCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
        
        // Mettre à jour le score
        scoreDisplay.textContent = scoreData.total;
        scoreDisplay.className = `display-4 text-${profile.color}`;
        
        // Mettre à jour la description
        if (scoreData.answered === Object.keys(questionScores).length) {
            profilDescription.innerHTML = `
                <div class="text-${profile.color}">
                    <strong>${profile.name}</strong>
                </div>
                <div class="small text-muted mt-1">${profile.description}</div>
            `;
            
            // Ajouter les recommandations
            const recommendationsHtml = profile.recommendations.map(rec => 
                `<li class="text-muted small">${rec}</li>`
            ).join('');
            
            profilDescription.innerHTML += `
                <div class="mt-3">
                    <small class="text-muted"><strong>Recommandations:</strong></small>
                    <ul class="mt-1 ps-3">${recommendationsHtml}</ul>
                </div>
            `;
        } else {
            profilDescription.innerHTML = `
                <div class="text-muted">
                    ${scoreData.answered}/${Object.keys(questionScores).length} questions répondues
                </div>
                <div class="small text-muted">Complétez toutes les questions pour voir votre profil</div>
            `;
        }
    }
    
    // Fonction de validation des réponses
    function validateAnswers() {
        const scoreData = calculateTotalScore();
        return scoreData.answered === Object.keys(questionScores).length;
    }
    
    // Fonction d'animation des cartes de questions
    function animateQuestionCard(questionElement) {
        questionElement.style.transform = 'scale(0.98)';
        questionElement.style.transition = 'transform 0.1s ease-in-out';
        
        setTimeout(() => {
            questionElement.style.transform = 'scale(1)';
        }, 100);
    }
    
    // Écouteurs d'événements pour les réponses
    document.querySelectorAll('input[type="radio"]').forEach(input => {
        input.addEventListener('change', function() {
            // Animation de la carte de question
            const questionCard = this.closest('.card');
            animateQuestionCard(questionCard);
            
            // Ajout de classe de validation visuelle
            const questionInputs = document.querySelectorAll(`input[name="${this.name}"]`);
            questionInputs.forEach(inp => {
                const label = inp.closest('.form-check').querySelector('.form-check-label');
                label.classList.remove('border', 'border-success');
            });
            
            const selectedLabel = this.closest('.form-check').querySelector('.form-check-label');
            selectedLabel.classList.add('border', 'border-success');
            
            // Mettre à jour les résultats
            updateResults();
            
            // Auto-scroll vers la question suivante si ce n'est pas la dernière
            const currentQuestionNumber = parseInt(this.name.substring(1));
            const nextQuestion = document.querySelector(`input[name="q${currentQuestionNumber + 1}"]`);
            if (nextQuestion && currentQuestionNumber < Object.keys(questionScores).length) {
                setTimeout(() => {
                    nextQuestion.closest('.card').scrollIntoView({ 
                        behavior: 'smooth', 
                        block: 'center' 
                    });
                }, 300);
            }
        });
    });
    
    // Validation du formulaire
    form.addEventListener('submit', function(e) {
        if (!validateAnswers()) {
            e.preventDefault();
            
            // Trouver la première question non répondue
            let firstUnanswered = null;
            for (let i = 1; i <= Object.keys(questionScores).length; i++) {
                const questionInputs = document.querySelectorAll(`input[name="q${i}"]`);
                const answered = Array.from(questionInputs).some(input => input.checked);
                if (!answered) {
                    firstUnanswered = document.querySelector(`input[name="q${i}"]`);
                    break;
                }
            }
            
            // Scroll vers la première question non répondue
            if (firstUnanswered) {
                firstUnanswered.closest('.card').scrollIntoView({ 
                    behavior: 'smooth', 
                    block: 'center' 
                });
                
                // Animation d'attention
                const questionCard = firstUnanswered.closest('.card');
                questionCard.style.boxShadow = '0 0 20px rgba(220, 53, 69, 0.3)';
                questionCard.style.transition = 'box-shadow 0.3s ease-in-out';
                
                setTimeout(() => {
                    questionCard.style.boxShadow = '';
                }, 2000);
            }
            
            // Afficher un message d'erreur
            showAlert('Veuillez répondre à toutes les questions avant de continuer.', 'danger');
            return false;
        }
        
        // Animation de soumission
        const submitBtn = this.querySelector('button[type="submit"]');
        submitBtn.classList.add('loading');
        submitBtn.disabled = true;
        
        // Simuler un délai de traitement
        setTimeout(() => {
            submitBtn.classList.remove('loading');
            submitBtn.disabled = false;
        }, 2000);
    });
    
    // Fonction d'affichage d'alertes
    function showAlert(message, type = 'info') {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            <i class="fas fa-${type === 'danger' ? 'exclamation-triangle' : 'info-circle'} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        // Insérer l'alerte en haut du formulaire
        form.insertBefore(alertDiv, form.firstChild);
        
        // Auto-suppression après 5 secondes
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }
    
    // Sauvegarde automatique des réponses dans le localStorage
    function saveProgress() {
        const answers = {};
        document.querySelectorAll('input[type="radio"]:checked').forEach(input => {
            answers[input.name] = input.value;
        });
        
        localStorage.setItem('cif_questionnaire_progress', JSON.stringify({
            answers: answers,
            timestamp: Date.now(),
            clientId: window.location.pathname.split('/').pop()
        }));
    }
    
    // Restauration des réponses depuis le localStorage
    function restoreProgress() {
        const saved = localStorage.getItem('cif_questionnaire_progress');
        if (saved) {
            try {
                const data = JSON.parse(saved);
                const currentClientId = window.location.pathname.split('/').pop();
                
                // Vérifier que c'est pour le bon client et que ce n'est pas trop ancien (24h)
                if (data.clientId === currentClientId && 
                    (Date.now() - data.timestamp) < 24 * 60 * 60 * 1000) {
                    
                    Object.entries(data.answers).forEach(([questionName, answer]) => {
                        const input = document.querySelector(`input[name="${questionName}"][value="${answer}"]`);
                        if (input) {
                            input.checked = true;
                            input.dispatchEvent(new Event('change'));
                        }
                    });
                    
                    showAlert('Vos réponses précédentes ont été restaurées.', 'info');
                }
            } catch (e) {
                console.warn('Erreur lors de la restauration des réponses:', e);
            }
        }
    }
    
    // Écouteur pour la sauvegarde automatique
    document.querySelectorAll('input[type="radio"]').forEach(input => {
        input.addEventListener('change', saveProgress);
    });
    
    // Nettoyage du localStorage après soumission réussie
    window.addEventListener('beforeunload', function() {
        // Ne pas nettoyer si on quitte avant d'avoir terminé
        const scoreData = calculateTotalScore();
        if (scoreData.answered === Object.keys(questionScores).length) {
            localStorage.removeItem('cif_questionnaire_progress');
        }
    });
    
    // Initialisation
    restoreProgress();
    updateResults();
    
    // Effet de progression visuelle
    function updateProgressBar() {
        const scoreData = calculateTotalScore();
        const progressPercent = (scoreData.answered / Object.keys(questionScores).length) * 100;
        
        let progressBar = document.querySelector('.questionnaire-progress');
        if (!progressBar) {
            // Créer la barre de progression si elle n'existe pas
            const progressContainer = document.createElement('div');
            progressContainer.className = 'card bg-light mb-3';
            progressContainer.innerHTML = `
                <div class="card-body py-2">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <small class="text-muted">Progression du questionnaire</small>
                        <small class="text-muted"><span class="progress-text">${scoreData.answered}/${Object.keys(questionScores).length}</span></small>
                    </div>
                    <div class="progress questionnaire-progress" style="height: 8px;">
                        <div class="progress-bar bg-primary" role="progressbar" style="width: ${progressPercent}%"></div>
                    </div>
                </div>
            `;
            
            form.insertBefore(progressContainer, form.firstChild);
            progressBar = progressContainer.querySelector('.progress-bar');
        } else {
            progressBar.style.width = `${progressPercent}%`;
            document.querySelector('.progress-text').textContent = `${scoreData.answered}/${Object.keys(questionScores).length}`;
        }
    }
    
    // Mettre à jour la progression à chaque changement
    document.querySelectorAll('input[type="radio"]').forEach(input => {
        input.addEventListener('change', updateProgressBar);
    });
    
    // Initialiser la barre de progression
    updateProgressBar();
});
