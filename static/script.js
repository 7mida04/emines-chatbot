// Global variables
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let currentTranscription = '';

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('EMINES Chatbot initialized');
});

// Handle Enter key press
function handleKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

// Send message
async function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    
    if (!message) return;
    
    // Hide welcome screen
    hideWelcomeScreen();
    
    // Clear input
    input.value = '';
    
    // Add user message to chat
    addMessage(message, 'user');
    
    // Show typing indicator
    const typingId = showTypingIndicator();
    
    try {
        // Send message to backend with SSE
        await streamChatResponse(message, typingId);
    } catch (error) {
        console.error('Error sending message:', error);
        removeTypingIndicator(typingId);
        addMessage('Désolé, une erreur s\'est produite. Veuillez réessayer.', 'bot');
    }
}

// Format markdown text to HTML
function formatMarkdown(text) {
    // Gras: **texte** ou __texte__
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    text = text.replace(/__(.*?)__/g, '<strong>$1</strong>');
    
    // Italique: *texte* ou _texte_
    text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
    text = text.replace(/_(.*?)_/g, '<em>$1</em>');
    
    // Listes à puces: - item ou * item
    text = text.replace(/^[\-\*] (.+)$/gm, '• $1');
    
    // Sauts de ligne
    text = text.replace(/\n/g, '<br>');
    
    return text;
}

// Stream chat response from backend
async function streamChatResponse(message, typingId) {
    const chatMessages = document.getElementById('chat-messages');
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: message })
        });

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }

        // Remove typing indicator
        removeTypingIndicator(typingId);

        // Create message element for bot response
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message message-bot';
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.innerHTML = '<i class="fas fa-robot"></i>';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        const textDiv = document.createElement('div');
        textDiv.className = 'message-text';
        
        contentDiv.appendChild(textDiv);
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(contentDiv);
        chatMessages.appendChild(messageDiv);

        // Read the stream
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullText = '';

        while (true) {
            const { done, value } = await reader.read();
            
            if (done) break;
            
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.substring(6).trim();
                    
                    if (data === '[DONE]') {
                        continue;
                    }
                    
                    try {
                        const parsed = JSON.parse(data);
                        if (parsed.text) {
                            fullText += parsed.text;
                            textDiv.innerHTML = formatMarkdown(fullText);
                            scrollToBottom();
                        }
                    } catch (e) {
                        console.error('Error parsing SSE data:', e);
                    }
                }
            }
        }

        // Final scroll
        scrollToBottom();

    } catch (error) {
        console.error('Error streaming response:', error);
        removeTypingIndicator(typingId);
        addMessage('Désolé, une erreur s\'est produite lors de la communication avec le serveur.', 'bot');
    }
}

// Add message to chat
function addMessage(text, sender) {
    const chatMessages = document.getElementById('chat-messages');
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${sender}`;
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.innerHTML = sender === 'user' 
        ? '<i class="fas fa-user"></i>' 
        : '<i class="fas fa-robot"></i>';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    const textDiv = document.createElement('div');
    textDiv.className = 'message-text';
    textDiv.innerHTML = sender === 'bot' ? formatMarkdown(text) : text;
    
    contentDiv.appendChild(textDiv);
    
    if (sender === 'user') {
        messageDiv.appendChild(contentDiv);
        messageDiv.appendChild(avatar);
    } else {
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(contentDiv);
    }
    
    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

// Show typing indicator
function showTypingIndicator() {
    const chatMessages = document.getElementById('chat-messages');
    
    const messageDiv = document.createElement('div');
    const typingId = 'typing-' + Date.now();
    messageDiv.id = typingId;
    messageDiv.className = 'message message-bot';
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.innerHTML = '<i class="fas fa-robot"></i>';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    const typingDiv = document.createElement('div');
    typingDiv.className = 'typing-indicator';
    typingDiv.innerHTML = `
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
    `;
    
    contentDiv.appendChild(typingDiv);
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    
    scrollToBottom();
    return typingId;
}

// Remove typing indicator
function removeTypingIndicator(typingId) {
    const element = document.getElementById(typingId);
    if (element) {
        element.remove();
    }
}

// Hide welcome screen and show chat
function hideWelcomeScreen() {
    const welcomeScreen = document.getElementById('welcome-screen');
    const chatMessages = document.getElementById('chat-messages');
    
    if (welcomeScreen.style.display !== 'none') {
        welcomeScreen.style.display = 'none';
        chatMessages.classList.add('active');
    }
}

// Scroll to bottom of chat
function scrollToBottom() {
    const chatMessages = document.getElementById('chat-messages');
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Send quick question
function sendQuickQuestion(question) {
    const input = document.getElementById('messageInput');
    input.value = question;
    sendMessage();
}

// New chat
async function newChat() {
    try {
        await fetch('/api/clear', {
            method: 'POST'
        });
        
        // Clear chat messages
        const chatMessages = document.getElementById('chat-messages');
        chatMessages.innerHTML = '';
        chatMessages.classList.remove('active');
        
        // Show welcome screen
        const welcomeScreen = document.getElementById('welcome-screen');
        welcomeScreen.style.display = 'flex';
        
        // Clear input
        document.getElementById('messageInput').value = '';
        
    } catch (error) {
        console.error('Error clearing chat:', error);
    }
}

// Voice recording functions
async function toggleVoiceRecording() {
    const voiceBtn = document.getElementById('voiceBtn');
    
    if (!isRecording) {
        await startRecording();
    } else {
        await stopRecording();
    }
}

async function startRecording() {
    try {
        console.log('Requesting microphone access...');
        
        // Essayer d'abord avec les contraintes minimales
        let stream;
        try {
            stream = await navigator.mediaDevices.getUserMedia({ 
                audio: true
            });
            console.log('Got stream with basic constraints');
        } catch (e) {
            console.log('Basic constraints failed, trying advanced...');
            // Si ça échoue, essayer avec des contraintes spécifiques
            stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: false,
                    noiseSuppression: false,
                    autoGainControl: false,
                    channelCount: 1,
                    sampleRate: 16000
                } 
            });
            console.log('Got stream with advanced constraints');
        }
        
        // Vérifier que le stream a bien des tracks audio
        const audioTracks = stream.getAudioTracks();
        console.log('Audio tracks:', audioTracks.length);
        if (audioTracks.length === 0) {
            throw new Error('No audio tracks in stream');
        }
        
        // Tester les différents types MIME
        const mimeTypes = [
            'audio/webm',
            'audio/webm;codecs=opus',
            'audio/ogg;codecs=opus',
            'audio/mp4',
            ''  // Type par défaut
        ];
        
        let mimeType = '';
        for (const type of mimeTypes) {
            if (type === '' || MediaRecorder.isTypeSupported(type)) {
                mimeType = type;
                console.log('Selected MIME type:', type || 'default');
                break;
            }
        }
        
        // Créer le MediaRecorder
        const options = mimeType ? { mimeType: mimeType } : {};
        mediaRecorder = new MediaRecorder(stream, options);
        audioChunks = [];
        
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
                console.log('Data chunk received:', event.data.size, 'bytes');
            }
        };
        
        mediaRecorder.onstop = async () => {
            console.log('Recording stopped, total chunks:', audioChunks.length);
            const audioBlob = new Blob(audioChunks, { type: mimeType || 'audio/webm' });
            console.log('Audio blob created:', audioBlob.size, 'bytes');
            await transcribeAudio(audioBlob);
            
            // Stop all tracks
            stream.getTracks().forEach(track => {
                track.stop();
                console.log('Track stopped');
            });
        };
        
        mediaRecorder.onerror = (event) => {
            console.error('MediaRecorder error:', event.error);
        };
        
        // Démarrer l'enregistrement
        mediaRecorder.start(1000); // Collecter les données toutes les secondes
        isRecording = true;
        
        const voiceBtn = document.getElementById('voiceBtn');
        voiceBtn.classList.add('recording');
        voiceBtn.innerHTML = '<i class="fas fa-stop"></i>';
        
        console.log('Recording started successfully, state:', mediaRecorder.state);
        
    } catch (error) {
        console.error('Error starting recording:', error);
        console.error('Error name:', error.name);
        console.error('Error message:', error.message);
        
        let errorMessage = 'Impossible d\'accéder au microphone.\n\n';
        
        if (error.name === 'NotAllowedError') {
            errorMessage += '❌ Accès refusé\n\nVeuillez :\n1. Cliquer sur l\'icône de cadenas dans la barre d\'adresse\n2. Autoriser l\'accès au microphone\n3. Rafraîchir la page';
        } else if (error.name === 'NotFoundError') {
            errorMessage += '❌ Aucun microphone détecté\n\nVérifiez que votre microphone est bien branché.';
        } else if (error.name === 'NotReadableError') {
            errorMessage += '❌ Microphone inaccessible\n\nSolutions :\n1. Fermez toutes les autres applications utilisant le micro (Teams, Zoom, Discord...)\n2. Redémarrez votre navigateur\n3. Si le problème persiste, redémarrez votre ordinateur';
        } else if (error.name === 'OverconstrainedError') {
            errorMessage += '❌ Configuration microphone incompatible\n\nVotre microphone ne supporte pas les paramètres demandés.';
        } else {
            errorMessage += '❌ Erreur : ' + error.message;
        }
        
        alert(errorMessage);
    }
}

async function stopRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        
        const voiceBtn = document.getElementById('voiceBtn');
        voiceBtn.classList.remove('recording');
        voiceBtn.innerHTML = '<i class="fas fa-microphone"></i>';
    }
}

async function transcribeAudio(audioBlob) {
    const messageInput = document.getElementById('messageInput');
    
    // Afficher un indicateur visuel dans l'input
    const originalPlaceholder = messageInput.placeholder;
    messageInput.placeholder = '🎤 Transcription en cours...';
    messageInput.disabled = true;
    
    try {
        const formData = new FormData();
        // Utiliser l'extension appropriée selon le type
        const extension = audioBlob.type.includes('webm') ? 'webm' : 
                         audioBlob.type.includes('ogg') ? 'ogg' : 
                         audioBlob.type.includes('mp4') ? 'mp4' : 'wav';
        formData.append('audio', audioBlob, `recording.${extension}`);
        
        console.log('Sending audio for transcription:', audioBlob.size, 'bytes');
        
        const response = await fetch('/api/transcribe', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Transcription failed');
        }
        
        const data = await response.json();
        console.log('Transcription response:', data);
        
        if (data.corrected || data.raw) {
            // Utiliser la version corrigée ou la version brute
            currentTranscription = data.corrected || data.raw;
            
            // Mettre la transcription directement dans l'input
            messageInput.value = currentTranscription;
            messageInput.placeholder = originalPlaceholder;
            messageInput.disabled = false;
            messageInput.focus();
            
            // Afficher aussi la version brute si différente (pour debug)
            if (data.raw && data.corrected && data.raw !== data.corrected) {
                console.log('Raw transcription:', data.raw);
                console.log('Corrected transcription:', data.corrected);
            }
        } else {
            throw new Error('No transcription data received');
        }
        
    } catch (error) {
        console.error('Error transcribing audio:', error);
        
        // Restaurer l'input et afficher une alerte
        messageInput.placeholder = originalPlaceholder;
        messageInput.disabled = false;
        alert('Erreur lors de la transcription. Veuillez réessayer.');
    }
}

function sendTranscription() {
    if (currentTranscription) {
        const input = document.getElementById('messageInput');
        input.value = currentTranscription;
        closeTranscriptionModal();
        sendMessage();
    }
}

function cancelTranscription() {
    closeTranscriptionModal();
}

function closeTranscriptionModal() {
    const modal = document.getElementById('transcriptionModal');
    modal.classList.remove('active');
    currentTranscription = '';
    
    // Reset status styles
    const statusDiv = document.getElementById('transcriptionStatus');
    statusDiv.style.background = 'rgba(0, 212, 255, 0.1)';
    statusDiv.style.color = '#00d4ff';
}
