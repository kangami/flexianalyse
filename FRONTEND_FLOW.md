# Frontend Flow Documentation: User Prompt to Response Display

## Vue d'ensemble

Ce document explique le flux complet de traitement d'un prompt utilisateur depuis l'interface utilisateur jusqu'à l'affichage de la réponse dans le frontend de FlexiAnalyse.

---

## Architecture générale

Le frontend est construit avec **React + TypeScript** et utilise :
- **Context API** pour la gestion d'état globale (thème, langue)
- **Hooks personnalisés** pour la logique métier
- **Composants modulaires** pour l'UI

---

## 1. Point d'entrée : Composant `QueryForm`

**Fichier** : `src/components/main/QueryForm.tsx`

### 1.1 Saisie utilisateur

L'utilisateur saisit sa question dans le champ de texte et clique sur "Envoyer" ou appuie sur `Enter`.

### 1.2 Soumission de la requête

**Handler** : `onQuerySubmit(query: string, mode: 'online' | 'local')`

```typescript
// Détermination du mode par défaut
const defaultMode: 'online' | 'local' = selectedFile ? 'local' : 'online';

// Appel de la fonction de soumission
onQuerySubmit(query, defaultMode);
```

Le mode est déterminé automatiquement :
- **Mode LOCAL** : Si un fichier est sélectionné
- **Mode ONLINE** : Sinon

---

## 2. Composant principal : `FlexiAnalyseApp`

**Fichier** : `src/FlexiAnalyseApp.tsx`

### 2.1 Fonction de gestion : `handleQuerySubmitWithStream`

**Ligne** : ~1243

#### 2.1.1 Vérifications préliminaires

```typescript
// Vérification des limites pour utilisateurs non connectés
if (!isAuthenticated && !checkQueryLimit()) {
    showLimitInfoBubble('Limite de requêtes atteinte');
    return;
}

// Incrémentation du compteur
if (!isAuthenticated) {
    incrementDailyQueries();
}
```

#### 2.1.2 Redirection selon le mode

```typescript
// Si mode local, utiliser l'ancienne méthode (non-streaming)
if (mode === 'local') {
    return handleQuerySubmit(query, mode);
}

// Sinon, utiliser le streaming (mode online)
```

**Note** : Actuellement, le streaming est utilisé uniquement pour le mode `online`. Le mode `local` utilise `handleQuerySubmit` (non-streaming).

---

### 2.2 Fonction : `handleQuerySubmit` (Mode LOCAL)

**Ligne** : ~971

#### 2.2.1 Préparation du message

```typescript
const messageId = Math.random().toString(36).substr(2, 9);
const newMessage: ChatMessage = { 
    id: messageId,
    userQuery: query, 
    aiResponse: '' 
};

// Ajout à l'historique
setChatHistory((prev) => [...prev, newMessage]);
setLoading(true);
```

#### 2.2.2 Préparation de la requête

**Détection de langue** :
```typescript
const language = detectLanguage(query); // Utilise 'franc-min'
```

**Sélection du modèle** :
```typescript
const effectiveModel = selectedModel === AUTO_MODEL_ID 
    ? chooseModelForQuery(query) 
    : selectedModel;
```

**Préparation du payload** :
```typescript
const requestPayload: any = {
    user_query: query,
    selected_model: effectiveModel,
    language: language,
    research_mode: effectiveMode,
    conversation_history: chatHistory.slice(-6).flatMap((msg) => [
        { role: 'user', content: msg.userQuery },
        { role: 'assistant', content: msg.aiResponse },
    ])
};
```

**Mode LOCAL spécifique** :
```typescript
if (effectiveMode === 'local') {
    // Vérification du vector store
    const hasVectorStore = isDirectoryIndexed || (selectedFile && fileDetails);
    
    requestPayload.use_backend_vectorstore = hasVectorStore;
    
    if (selectedFile && fileDetails) {
        // Extraction du contenu selon le type de fichier
        let fileContent: string = '';
        
        if (typeof fileDetails.content === 'string') {
            fileContent = fileDetails.content;
        } else if (fileDetails.content instanceof ArrayBuffer) {
            // Pour les PDFs/DOCX, le contenu est déjà extrait
            fileContent = ''; // Le backend lira depuis le vector store
        }
        
        requestPayload.file_name = selectedFile.name;
        requestPayload.file_content = fileContent;
        requestPayload.is_binary = fileDetails.content instanceof ArrayBuffer;
    } else if (isDirectoryIndexed) {
        // Mode corpus (répertoire indexé)
        requestPayload.file_name = undefined; // Le backend détectera "__DIRECTORY_CORPUS__"
        requestPayload.use_backend_vectorstore = true;
    }
}
```

#### 2.2.3 Envoi de la requête HTTP

```typescript
const response = await fetch(`${apiUrl}/query`, {
    method: 'POST',
    headers: { 
        'Content-Type': 'application/json',
        'Session-ID': sessionId // Important pour le vector store
    },
    body: JSON.stringify(requestPayload),
});
```

**Gestion des erreurs** :
```typescript
if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || 'Échec du traitement');
}
```

#### 2.2.4 Traitement de la réponse

```typescript
const data = await response.json();

// Mise à jour de l'historique avec la réponse
setChatHistory((prev) => 
    prev.map(msg => 
        msg.id === messageId 
            ? { ...msg, aiResponse: data.response }
            : msg
    )
);
```

#### 2.2.5 Extraction des citations (si présentes)

Les citations sont extraites automatiquement lors du rendu dans `ResponseDisplay` (voir section 4).

---

### 2.3 Fonction : `handleQuerySubmitWithStream` (Mode ONLINE)

**Ligne** : ~1243

#### 2.3.1 Préparation identique à `handleQuerySubmit`

#### 2.3.2 Envoi avec streaming SSE

```typescript
const response = await fetch(`${apiUrl}/query-stream`, {
    method: 'POST',
    headers: { 
        'Content-Type': 'application/json',
        'Session-ID': sessionId
    },
    body: JSON.stringify({
        user_query: query,
        selected_model: effectiveModel,
        language: language,
        research_mode: mode,
        conversation_history: chatHistory.slice(-6).flatMap(...),
        enable_online_search: mode === 'online'
    }),
});
```

#### 2.3.3 Lecture du stream

```typescript
const reader = response.body?.getReader();
const decoder = new TextDecoder();
let accumulatedResponse = '';

if (reader) {
    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        // Décodage du chunk
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');
        
        for (const line of lines) {
            // Format SSE: "data: {...}"
            if (line.startsWith('data: ')) {
                const jsonData = JSON.parse(line.slice(6));
                
                // Mise à jour du statut
                if (jsonData.status) {
                    setCurrentStatus(jsonData.status);
                }
                
                // Accumulation du contenu
                if (jsonData.content) {
                    accumulatedResponse += jsonData.content;
                    
                    // Mise à jour en temps réel
                    setChatHistory((prev) => 
                        prev.map(msg => 
                            msg.id === messageId 
                                ? { ...msg, aiResponse: accumulatedResponse }
                                : msg
                        )
                    );
                }
                
                // Fin du stream
                if (jsonData.done) {
                    console.log('✅ Streaming terminé');
                }
            }
        }
    }
}
```

**Avantages du streaming** :
- Affichage en temps réel (token par token)
- Meilleure UX (pas d'attente de la réponse complète)
- Feedback visuel immédiat

---

## 3. Affichage : Composant `ChatPanel`

**Fichier** : `src/components/main/ChatPanel.tsx`

### 3.1 Structure

```typescript
<ChatPanel
    chatHistory={chatHistory}           // Historique des messages
    loading={loading}                   // État de chargement
    onQuerySubmit={handleQuerySubmitWithStream}
    selectedModel={selectedModel}
    researchMode={researchMode}
    setResearchMode={setResearchMode}
    suggestedActions={suggestedActions}
    onSuggestedActionClick={handleSuggestedActionClick}
    isSearchingOnline={isSearchingOnline}
    currentStatus={currentStatus}
/>
```

### 3.2 Rendu des messages

Le `ChatPanel` itère sur `chatHistory` et affiche chaque message via `ResponseDisplay`.

---

## 4. Rendu de la réponse : Composant `ResponseDisplay`

**Fichier** : `src/components/main/ResponseDisplay.tsx`

### 4.1 Extraction des citations

Les citations sont extraites depuis `aiResponse` en utilisant une regex :

```typescript
// Format des citations: [@source:page:section]
const citationRegex = /\[@([^\]]+)\]/g;
const citations: Citation[] = [];

let match;
while ((match = citationRegex.exec(aiResponse)) !== null) {
    const fullMatch = match[0];
    const citationContent = match[1];
    
    // Parsing du contenu (ex: "file.docx:1:DOCUMENT PRINCIPAL")
    const parts = citationContent.split(':');
    citations.push({
        source: parts[0],
        page: parts[1] || '1',
        section: parts[2] || '',
        full_match: fullMatch,
        start_pos: match.index,
        end_pos: match.index + fullMatch.length,
        text_snippet: extractTextSnippet(aiResponse, match.index), // Extrait le contexte
        citation_number: citations.length + 1
    });
}
```

### 4.2 Rendu du markdown

**Composant** : `MarkdownResponse`

```typescript
<MarkdownResponse
    content={aiResponse}
    citations={citations}
    onCitationClick={handleCitationClick}
/>
```

### 4.3 Formatage des citations

Les citations sont remplacées par des composants cliquables :

```typescript
// Remplacement de [@source:page:section] par <CitationLink />
const renderWithCitations = (content: string) => {
    let lastIndex = 0;
    const elements: ReactNode[] = [];
    
    citations.forEach((citation, index) => {
        // Texte avant la citation
        elements.push(content.slice(lastIndex, citation.start_pos));
        
        // Lien de citation
        elements.push(
            <CitationLink
                key={index}
                citation={citation}
                onClick={() => onCitationClick(citation)}
            />
        );
        
        lastIndex = citation.end_pos;
    });
    
    // Texte restant
    elements.push(content.slice(lastIndex));
    
    return elements;
};
```

---

## 5. Gestion des clics sur citations

### 5.1 Handler : `handleCitationClick`

**Fichier** : `src/FlexiAnalyseApp.tsx`  
**Ligne** : ~1650

```typescript
const handleCitationClick = useCallback((citation: Citation) => {
    console.log('Citation clicked:', citation);
    
    // Si un fichier est déjà sélectionné
    if (selectedFile && fileDetails) {
        // Vérifier si la citation correspond au fichier actuel
        const citationSource = citation.source.replace(/ \([0-9]+\)$/, '').replace(/\.[^.]+$/, '');
        const currentFileName = selectedFile.name.replace(/\.[^.]+$/, '');
        
        if (citationSource.toLowerCase().includes(currentFileName.toLowerCase()) ||
            currentFileName.toLowerCase().includes(citationSource.toLowerCase())) {
            // Fichier correspondant → Highlight direct
            setHighlightCitation(citation);
            return;
        }
    }
    
    // Sinon, chercher le fichier dans directoryFiles
    const matchingFile = directoryFiles.find(file => {
        const fileName = file.name.replace(/\.[^.]+$/, '');
        const citationSource = citation.source.replace(/ \([0-9]+\)$/, '').replace(/\.[^.]+$/, '');
        return fileName.toLowerCase().includes(citationSource.toLowerCase()) ||
               citationSource.toLowerCase().includes(fileName.toLowerCase());
    });
    
    if (matchingFile) {
        // Charger le fichier et highlight la citation
        handleFileSelect(matchingFile, {
            content: fileDetails?.content || '',
            description: matchingFile.name
        }).then(() => {
            setHighlightCitation(citation);
        });
    }
}, [selectedFile, fileDetails, directoryFiles, handleFileSelect]);
```

### 5.2 Highlight dans `FileViewer`

**Fichier** : `src/components/main/FileViewer.tsx`

**Effet** :
```typescript
useEffect(() => {
    if (!highlightCitation) return;
    
    const citation = highlightCitation;
    
    // Pour les PDFs
    if (file?.name.endsWith('.pdf')) {
        // Scroll vers la page
        scrollToPdfPage(parseInt(citation.page) || 1).then(() => {
            // Highlight le texte
            highlightTextInPdf(citation.text_snippet);
        });
    }
    
    // Pour les DOCX/TXT
    else {
        // Scroll vers le texte dans le contenu
        highlightTextInContent(citation.text_snippet);
    }
}, [highlightCitation]);
```

**Fonction `highlightTextInContent`** :
- Recherche flexible du texte (exact, progressive, mot par mot)
- Scroll vers l'élément trouvé
- Ajout d'une classe CSS pour le highlight (couleur violette)

---

## 6. Upload et indexation de fichiers

### 6.1 Upload de fichier unique

**Handler** : `handleFileSelect`

**Fichier** : `src/FlexiAnalyseApp.tsx`  
**Ligne** : ~450

#### 6.1.1 Extraction du contenu

```typescript
let content: string | ArrayBuffer;

if (extension === '.pdf' || extension === '.docx') {
    // Pour les PDFs/DOCX, garder le ArrayBuffer pour le backend
    content = await file.arrayBuffer();
} else {
    // Pour les fichiers texte, extraire directement
    content = await file.text();
}
```

#### 6.1.2 Génération du résumé (streaming)

```typescript
// Appel au backend pour générer le résumé
const summaryResponse = await fetch(`${apiUrl}/summarize_file_stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        file_name: file.name,
        content: typeof content === 'string' ? content : '',
        file_bytes: typeof content === 'string' ? undefined : 
            Array.from(new Uint8Array(content)).map(b => b.toString(16).padStart(2, '0')).join('')
    })
});

// Lecture du stream
const reader = summaryResponse.body?.getReader();
// ... (similaire au streaming de réponse)
```

#### 6.1.3 Sauvegarde de l'état

```typescript
setSelectedFile(file);
setFileDetails({ content, description: fileSummary });
setFileSummary(fileSummary);
```

---

### 6.2 Upload de répertoire

**Handler** : `handleDirectorySelect`

**Fichier** : `src/FlexiAnalyseApp.tsx`  
**Ligne** : ~570

#### 6.2.1 Préparation des fichiers

```typescript
// Conversion en FileNode pour l'affichage
const fileTree = buildFileTree(files);
setDirectoryFiles(files);

// Passage en mode local
setResearchMode('local');
```

#### 6.2.2 Indexation backend

**Fonction** : `indexDirectoryContentOnBackend`

**Fichier** : `src/FlexiAnalyseApp.tsx`  
**Ligne** : ~863

```typescript
// Extraction du texte de tous les fichiers
const fileContents: { fileName: string; content: string }[] = [];

for (const file of files) {
    const text = await extractTextFromFile(file);
    if (text && text !== 'Unsupported file type') {
        fileContents.push({
            fileName: file.name,
            content: text
        });
    }
}

// Envoi au backend
const response = await fetch(`${apiUrl}/index-directory`, {
    method: 'POST',
    headers: { 
        'Content-Type': 'application/json',
        'Session-ID': sessionId
    },
    body: JSON.stringify({
        files: fileContents,
        language: language
    }),
});

const data = await response.json();

// Mise à jour des actions suggérées
if (Array.isArray(data.suggested_actions)) {
    setSuggestedActions(data.suggested_actions);
}
```

#### 6.2.3 Génération du résumé du répertoire

```typescript
// Appel au backend pour générer le résumé du corpus
const repoSummaryResponse = await fetch(`${apiUrl}/summarize_repository_stream`, {
    // ... (similaire au résumé de fichier)
});
```

---

## 7. Actions suggérées

### 7.1 Génération automatique

Les actions suggérées sont générées par le backend lors de l'indexation (`/index-directory`) ou lors de la sélection d'un fichier (`/infer-corpus-actions`).

### 7.2 Clic sur une action

**Handler** : `handleSuggestedActionClick`

**Fichier** : `src/FlexiAnalyseApp.tsx`  
**Ligne** : ~1478

```typescript
const handleSuggestedActionClick = useCallback(
    (action: SuggestedAction) => {
        // Détection si c'est une action d'extraction structurée
        const isExtractionAction = action.id.includes('extract') || 
                                   action.id.includes('structured');
        
        if (isExtractionAction && selectedFile) {
            // Appeler l'extraction structurée
            handleExtractStructured();
        } else {
            // Envoyer le prompt de l'action
            const defaultMode: 'online' | 'local' = selectedFile ? 'local' : 'online';
            handleQuerySubmitWithStream(action.sample_prompt, defaultMode);
        }
    },
    [selectedFile, handleQuerySubmitWithStream, handleExtractStructured]
);
```

---

## 8. Gestion d'état globale

### 8.1 États principaux

```typescript
const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
const [selectedFile, setSelectedFile] = useState<File | null>(null);
const [fileDetails, setFileDetails] = useState<{content: string | ArrayBuffer, description: string} | null>(null);
const [researchMode, setResearchMode] = useState<'online' | 'local'>('online');
const [loading, setLoading] = useState(false);
const [suggestedActions, setSuggestedActions] = useState<SuggestedAction[]>([]);
const [directoryFiles, setDirectoryFiles] = useState<File[]>([]);
const [isDirectoryIndexed, setIsDirectoryIndexed] = useState(false);
const [highlightCitation, setHighlightCitation] = useState<Citation | null>(null);
```

### 8.2 Session ID

```typescript
const sessionId = useMemo(() => {
    let id = sessionStorage.getItem('session_id');
    if (!id) {
        id = Math.random().toString(36).substr(2, 9);
        sessionStorage.setItem('session_id', id);
    }
    return id;
}, []);
```

Le `session_id` est utilisé pour :
- Associer un vector store à une session
- Persister les données entre les requêtes
- Gérer l'indexation de répertoires

---

## 9. Flux de données complet (Mode LOCAL avec fichier)

```
User Input (QueryForm)
    ↓
onQuerySubmit(query, 'local')
    ↓
FlexiAnalyseApp.handleQuerySubmit()
    ├─ Création du message dans chatHistory
    ├─ Préparation du payload
    │   ├─ user_query
    │   ├─ selected_model
    │   ├─ language
    │   ├─ research_mode: 'local'
    │   ├─ file_name
    │   ├─ file_content
    │   ├─ use_backend_vectorstore
    │   └─ conversation_history
    └─ Fetch POST /query
        ↓
Backend (voir BACKEND_FLOW.md)
        ↓
JSON Response
    ├─ response: string
    ├─ mode: 'local'
    ├─ model_used: string
    └─ context_info: {...}
    ↓
Mise à jour de chatHistory
    ↓
ChatPanel.render()
    ↓
ResponseDisplay.render()
    ├─ Extraction des citations (regex)
    ├─ Parsing markdown
    └─ Rendu avec CitationLink
    ↓
User clicks citation
    ↓
handleCitationClick()
    ├─ Recherche du fichier correspondant
    ├─ handleFileSelect() si nécessaire
    └─ setHighlightCitation()
    ↓
FileViewer.useEffect()
    ├─ scrollToPdfPage() ou scrollToContent()
    └─ highlightTextInPdf() ou highlightTextInContent()
    ↓
Texte highlighté en violet
```

---

## 10. Points clés de l'UX

1. **Streaming** : Réponses en temps réel pour meilleure réactivité
2. **Citations cliquables** : Navigation directe vers la source
3. **Highlight automatique** : Mise en évidence du texte cité
4. **Actions suggérées** : Aide à la formulation des requêtes
5. **Mode adaptatif** : Passage automatique en mode local lors de l'upload
6. **Multi-langue** : Support FR/EN/ES avec détection automatique
7. **Thèmes** : Support de plusieurs thèmes (white, dark, dark-blue)

---

## 11. Optimisations

1. **Memoization** : Utilisation de `useMemo` et `useCallback` pour éviter les re-renders
2. **Debouncing** : Upload de fichiers avec debounce pour éviter les requêtes multiples
3. **Lazy loading** : Chargement à la demande des composants lourds
4. **Error boundaries** : Gestion gracieuse des erreurs
5. **Loading states** : Feedback visuel pendant les opérations asynchrones

