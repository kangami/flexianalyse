# Backend Flow Documentation: User Prompt to Response Generation

## Vue d'ensemble

Ce document explique le flux complet de traitement d'un prompt utilisateur depuis sa réception jusqu'à la génération de la réponse dans le backend de FlexiAnalyse.

---

## Architecture générale

Le backend est construit avec **Flask** et utilise deux modes de recherche principaux :
1. **Mode LOCAL** : Analyse de documents uploadés/indexés
2. **Mode ONLINE** : Recherche en ligne avec enrichissement

---

## 1. Point d'entrée : Route `/query` (POST)

**Fichier** : `backend/backend.py`  
**Fonction** : `handle_query()` (ligne ~3722)

### 1.1 Réception et validation

```python
data = request.get_json()
user_query = data.get('user_query')
research_mode = data.get('research_mode', 'local')
selected_model = data.get('selected_model', DEFAULT_MODEL)
language = data.get('language', 'en')
session_id = request.headers.get('Session-ID', 'default')
conversation_history = data.get('conversation_history', [])
```

**Paramètres extraits** :
- `user_query` : La question de l'utilisateur (obligatoire)
- `research_mode` : `'local'` ou `'online'` (défaut: `'local'`)
- `selected_model` : Modèle LLM à utiliser (ex: `gpt-3.5-turbo`, `mistral`, `gpt-4o`)
- `language` : Langue de l'interface (ex: `'en'`, `'fr'`, `'es'`)
- `session_id` : Identifiant de session (depuis le header HTTP)
- `conversation_history` : Historique de la conversation pour le contexte

**Validation** :
- Vérifie que `user_query` n'est pas vide (erreur 400 sinon)
- Valide que `selected_model` existe dans `MODEL_CONFIG` (fallback vers `DEFAULT_MODEL` sinon)

---

## 2. Branchement selon le mode

### 2.1 MODE LOCAL (`research_mode == 'local'`)

#### 2.1.1 Préparation du contexte

**Fichier** : `backend/backend.py`  
**Fonction** : `handle_query()` → `query_model_local_mode()`

**Étapes** :

1. **Validation du fichier/répertoire** :
   - Si `file_name` n'est pas fourni :
     - Vérifie si un vector store existe pour la session (`session_id in vector_stores`)
     - Si oui, passe en mode **CORPUS** (`file_name = "__DIRECTORY_CORPUS__"`)
     - Sinon, retourne une erreur 400

2. **Recherche hybride (si vector store disponible)** :
   ```python
   if should_use_vectorstore and has_vector_store:
       session_vector_store = vector_stores[session_id]['store']
   ```
   
   **Recherche en deux passes** (`hybrid_retrieve_documents`) :
   
   **a) Première passe - Fichier sélectionné** (si `file_name != "__DIRECTORY_CORPUS__"`) :
   - Utilise `hybrid_retrieve_documents()` avec `preferred_sources=[file_name]`
   - Récupère les 6 chunks les plus pertinents du fichier sélectionné
   
   **b) Deuxième passe - Corpus entier** :
   - Utilise `hybrid_retrieve_documents()` sans restriction
   - Récupère les 12 chunks les plus pertinents de tous les documents
   
   **Fusion et déduplication** :
   - Combine les résultats des deux passes
   - Déduplique par `(source, preview)` pour éviter les doublons
   - Limite à 14 documents au total

3. **Recherche hybride expliquée** :
   
   **Fichier** : `backend/services/hybrid_retrieval.py`  
   **Fonction** : `hybrid_retrieve_documents()`
   
   **Stratégie de scoring** :
   - **Semantic similarity** (60%) : Similarité vectorielle FAISS
   - **BM25-like lexical** (30%) : Score lexical basé sur TF-IDF
   - **Exact term matching** (10%) : Boost pour correspondances exactes
   
   **Processus** :
   1. Récupère `k_candidates` (70) candidats via FAISS
   2. Calcule le score BM25 pour chaque candidat
   3. Détecte les correspondances exactes (dates, montants, IDs)
   4. Combine les scores avec les poids configurés
   5. Trie et retourne les top `k_final` documents

#### 2.1.2 Construction du prompt

**Fichier** : `backend/backend.py`  
**Fonction** : `query_model_local_mode()` (ligne ~2296)

**Structure du prompt** :

```python
prompt = (
    f"{t['local_analysis_mode']}\n"           # Instructions de mode local
    f"{t['no_external_search']}\n\n"          # Interdiction de recherche externe
    f"{history_section}"                       # Historique de conversation
    f"{total_docs_note}"                       # Note sur le nombre de documents
    f"{person_filter_instructions}"            # Filtrage par nom de personne (si applicable)
    f"=== CONTEXTE DU PROJET ===\n"
    f"{repo_structure}\n\n"
    f"=== DOCUMENT PRINCIPAL ===\n"
    f"{file_name}\n"
    f"{trimmed_main_content}\n\n"              # Contenu principal (max 4000 chars)
    f"=== AUTRES DOCUMENTS ===\n"
    f"{directory_content_summary}\n\n"         # Documents contextuels (max 2000 chars/chunk)
    f"=== QUESTION ===\n"
    f"{user_query}\n\n"
    f"{instructions}"                          # Instructions strictes de RAG
)
```

**Instructions strictes de RAG** :
- Répondre **UNIQUEMENT** à partir des documents fournis
- Ne pas inventer ou deviner
- Citer les sources avec le format `[@source:page:section]`
- Analyser TOUS les documents avant de conclure qu'une information est absente
- Réponses courtes et précises (style ChatPDF)

#### 2.1.3 Exécution du modèle avec fallback

**Fichier** : `backend/backend.py`  
**Fonction** : `execute_model_query_with_fallback()` (ligne ~2640)

**Cascade de modèles** :
1. **GPT-3.5-turbo** (premier essai)
2. **Mistral** (si GPT-3.5 non pertinent)
3. **GPT-4o** (si Mistral non pertinent)
4. **GPT-5-Nano** (si GPT-4o non pertinent)
5. **GPT-5-Mini** (si GPT-5-Nano non pertinent)
6. **GPT-5** (dernier recours)

**Vérification de pertinence** :
**Fichier** : `backend/backend.py`  
**Fonction** : `is_response_relevant()` (ligne ~2532)

**Critères de pertinence** :
- Réponse non vide et > 20 caractères
- Absence de phrases d'absence ("n'apparaît pas", "n'est pas trouvé", etc.)
- Présence d'au moins 30% des mots importants de la requête dans la réponse
- Réponse non trop générique

**Logique de fallback** :
```python
if selected_model in ['gpt-3.5-turbo', 'mistral']:
    # Vérifier la pertinence pour les modèles moins puissants
    if not is_response_relevant(response, user_query):
        # Passer au modèle suivant
        continue
else:
    # Pour GPT-4o et supérieur, on fait confiance au modèle
    return response, selected_model
```

#### 2.1.4 Recherche en ligne automatique (optionnelle)

Si `enable_auto_online_search == True` :

1. **Détection d'information absente** :
   **Fichier** : `backend/backend.py`  
   **Fonction** : `detect_missing_information()` (ligne ~2141)
   
   Vérifie si la réponse contient des indicateurs d'absence d'information.

2. **Recherche en ligne** :
   **Fichier** : `backend/services/search_service.py`  
   **Fonction** : `perform_online_search()`
   
   Utilise SerpAPI pour rechercher des informations complémentaires.

3. **Enrichissement** :
   - Combine la réponse locale avec les résultats de recherche
   - Utilise `execute_model_query_with_fallback()` pour fusionner intelligemment

#### 2.1.5 Retour de la réponse

```python
return jsonify({
    "response": response,
    "mode": "local",
    "model_used": actual_model_used,
    "model_config": MODEL_CONFIG.get(selected_model, {}),
    "context_info": {
        "file_name": file_name,
        "directory_files_count": len(directory_content),
        "vector_store_docs": len(relevant_docs),
        "is_binary": is_binary,
        "session_id": session_id,
        "used_backend_vectorstore": use_backend_vectorstore
    }
}), 200
```

---

### 2.2 MODE ONLINE (`research_mode == 'online'`)

#### 2.2.1 Processus d'enrichissement intelligent

**Fichier** : `backend/backend.py`  
**Fonction** : `query_model_online_mode()` (ligne ~3431)

**Étapes** :

1. **Réponse initiale du modèle** :
   ```python
   initial_prompt = (
       f"{t['online_mode_title']}\n"
       f"{t['question']}: {user_query}\n\n"
       f"{instructions}"
   )
   initial_response = await execute_model_query(initial_prompt, selected_model)
   ```

2. **Analyse du besoin de recherche** :
   **Fichier** : `backend/backend.py`  
   **Fonction** : `analyze_query_need_for_search()` (ligne ~3343)
   
   **Détection automatique** :
   - Mots-clés de données en temps réel (heure, prix, actualités, stock)
   - Patterns de requêtes nécessitant des données actuelles
   - Exemples : "heure actuelle", "prix Bitcoin", "news", "stock price"
   
   **APIs spécialisées priorisées** :
   - **CoinGecko API** : Pour les prix de cryptomonnaies
   - **WorldTimeAPI** : Pour l'heure dans différentes localisations
   - **DuckDuckGo Instant Answer** : Pour définitions, conversions, météo
   - **SerpAPI** : Fallback pour recherche Google générale

3. **Recherche en ligne (si nécessaire)** :
   
   **Fichier** : `backend/services/search_service.py`  
   **Fonction** : `perform_online_search()`
   
   **Priorité des APIs** :
   1. Vérifie si c'est une requête de prix Bitcoin → CoinGecko
   2. Vérifie si c'est une requête d'heure → WorldTimeAPI (avec fallback DuckDuckGo, puis SerpAPI)
   3. Sinon → DuckDuckGo Instant Answer, puis SerpAPI
   
   **Extraction de localisation générique** :
   - Utilise des regex pour extraire les noms de villes/pays
   - Traduit les noms français vers anglais pour les APIs
   - Gère un grand nombre de localisations via fallbacks

4. **Enrichissement de la réponse** :
   ```python
   enrichment_prompt = (
       f"Réponse initiale: {initial_response}\n\n"
       f"Résultats de recherche: {search_results}\n\n"
       f"Instructions: Combine intelligemment les informations..."
   )
   enriched_response = await execute_model_query_with_fallback(enrichment_prompt, selected_model)
   ```

5. **Formatage spécial** :
   - Heure : Format `Il est XXhXX à [lieu]`
   - Prix : Format carte avec prix en gras, changement en pourcentage
   - Taux de change : Format structuré
   - Météo : Format avec température et conditions

#### 2.2.2 Retour de la réponse

```python
return jsonify({
    "response": final_response,
    "mode": "online",
    "model_used": selected_model,
    "model_config": MODEL_CONFIG.get(selected_model, {}),
    "search_info": {
        "query": user_query,
        "language": language,
        "search_performed": "intelligent_enrichment",
        "approach": "searchgpt_style"
    }
}), 200
```

---

## 3. Route `/query-stream` (POST) - Mode Streaming

**Fichier** : `backend/backend.py`  
**Fonction** : `handle_query_stream()` (ligne ~3992)

### 3.1 Différences avec `/query`

- Utilise **Server-Sent Events (SSE)** pour le streaming
- Réponses en temps réel (token par token)
- Format : `text/event-stream`
- Même logique de branchement selon le mode (`local` ou `online`)

### 3.2 Format SSE

```
data: {"content": "token1", "status": "generating"}
data: {"content": "token2"}
data: {"done": true}
```

---

## 4. Indexation de documents (`/index-directory`)

**Fichier** : `backend/backend.py`  
**Fonction** : `index_directory()` (ligne ~3552)

### 4.1 Processus d'indexation

1. **Réception des fichiers** :
   - Liste de fichiers avec `fileName` et `content`
   - `session_id` depuis le header HTTP

2. **Création des Documents LangChain** :
   ```python
   Document(
       page_content=file_data['content'],
       metadata={
           'fileName': file_data['fileName'],
           'file_size': len(file_data['content']),
           'indexed_at': datetime.utcnow().isoformat()
       }
   )
   ```

3. **Chunking** :
   - Utilise `RecursiveCharacterTextSplitter`
   - `chunk_size=2000`, `chunk_overlap=300`
   - Séparateurs : `["\n\n\n", "\n\n", "\n", ". ", " ", ""]`

4. **Génération des embeddings** :
   - Modèle : `text-embedding-3-small` (fallback vers `ada-002`)
   - Utilise `OpenAIEmbeddings` de LangChain

5. **Création du vector store FAISS** :
   ```python
   vector_store = await FAISS.afrom_documents(split_docs, embeddings)
   ```

6. **Stockage par session** :
   ```python
   vector_stores[session_id] = {
       'store': vector_store,
       'created_at': datetime.utcnow().isoformat(),
       'files_count': len(files),
       'chunks_count': len(split_docs),
       'files_indexed': [f['fileName'] for f in files],
       'auto_actions': inferred_actions
   }
   ```

7. **Inférence d'actions suggérées** :
   - Analyse le corpus pour détecter le type de documents
   - Génère des actions suggérées selon le type (contrat, CV, facture, etc.)

---

## 5. Services auxiliaires

### 5.1 Extraction de texte

**Fichier** : `backend/utils/file_utils.py`

**Fonctions** :
- `extract_text_from_pdf()` : Extraction PDF avec fallback OCR (PyMuPDF + TrOCR)
- `extract_text_from_docx()` : Extraction DOCX (python-docx)

**OCR pour PDF scannés** :
- Détection automatique si peu de texte extractible
- Utilise `microsoft/trocr-base-printed` (fallback vers `trocr-base-handwritten`)
- Conversion PDF → images avec PyMuPDF
- Preprocessing d'images (contrast, sharpness)
- Extraction texte page par page

### 5.2 Recherche hybride

**Fichier** : `backend/services/hybrid_retrieval.py`  
**Fonction** : `hybrid_retrieve_documents()`

**Algorithme** :
1. Récupération de candidats via FAISS (similarité sémantique)
2. Calcul de scores BM25 pour chaque candidat
3. Détection de correspondances exactes (dates, montants)
4. Combinaison des scores avec pondération
5. Tri et retour des top documents

### 5.3 Clients API

**Fichier** : `backend/services/api_clients.py`

**Fonctions** :
- `call_openai_api()` : Appels à l'API OpenAI
- `call_mistral_api()` : Appels à l'API Mistral
- `call_ollama_api()` : Appels à Ollama (local)

---

## 6. Gestion des erreurs

### 6.1 Erreurs de validation

- **400 Bad Request** : Paramètres manquants ou invalides
- **500 Internal Server Error** : Erreurs serveur (avec message d'erreur dans le JSON)

### 6.2 Logging

- Toutes les étapes importantes sont loggées avec des emojis pour faciliter le debugging
- Niveaux : `INFO`, `WARNING`, `ERROR`

---

## 7. Flux de données complet (Mode LOCAL avec vector store)

```
User Prompt
    ↓
/query (POST)
    ↓
handle_query()
    ↓
Mode LOCAL détecté
    ↓
Vector store disponible ?
    ↓ OUI
hybrid_retrieve_documents() [2 passes]
    ├─ Pass 1: Fichier sélectionné (6 chunks)
    └─ Pass 2: Corpus entier (12 chunks)
    ↓
Fusion et déduplication → 14 documents max
    ↓
query_model_local_mode()
    ├─ Construction du prompt avec contexte
    ├─ Détection de noms de personnes (filtrage)
    └─ Instructions RAG strictes
    ↓
execute_model_query_with_fallback()
    ├─ Essai GPT-3.5-turbo
    ├─ Vérification de pertinence
    ├─ Fallback vers Mistral si non pertinent
    ├─ Fallback vers GPT-4o si non pertinent
    └─ ... (cascade jusqu'à GPT-5)
    ↓
Détection d'information absente ? (si enable_auto_online_search)
    ↓ OUI
perform_online_search()
    ↓
Enrichissement de la réponse
    ↓
JSON Response avec métadonnées
```

---

## 8. Points clés de performance

1. **Recherche hybride** : Combine sémantique + lexical pour meilleure précision
2. **Two-pass retrieval** : Priorise le fichier sélectionné, puis le corpus
3. **Fallback de modèles** : Garantit la pertinence des réponses
4. **Caching** : Cache les réponses pour éviter les recalculs
5. **Chunking intelligent** : Préserve le contexte avec overlap
6. **Streaming** : Réponses en temps réel pour meilleure UX

---

## 9. Extensions futures possibles

1. **Re-ranking avec cross-encoder** : Améliorer encore la précision
2. **Citations automatiques** : Extraire et formater les citations
3. **Validation de réponse** : Vérifier que la réponse est bien dans les documents
4. **Embeddings HuggingFace** : E5/BGE pour meilleure qualité sémantique

