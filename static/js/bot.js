// =====================================================
//  Chatbot Logic (Gemini + OpenAI + Ollama Integrated)
// =====================================================

// Flags for handling API key input
let awaitingProvider = false;
let awaitingApiKey = false;
let selectedProvider = "";
let providerConfigured = false;

document.addEventListener('DOMContentLoaded', () => {
    // Clear chat on fresh login
    const isNewSession = sessionStorage.getItem('chatSessionStarted');
    if (!isNewSession) {
        clearChatHistory();
        sessionStorage.setItem('chatSessionStarted', 'true');
    }
    
    selectedProvider = sessionStorage.getItem('selectedProvider') || "";
    providerConfigured = sessionStorage.getItem('providerConfigured') === 'true' || false;
    
    loadChatHistory();

    // Show welcome message if chat is empty
    const chatBody = document.getElementById("chatBody");
    if (!chatBody || chatBody.children.length === 0) {
        showWelcomeMessage();
    }

    // Hide API key section if Ollama is selected - on page load
    updateApiKeyVisibility();
});

// ✅ Function to update API key visibility based on selected provider
function updateApiKeyVisibility() {
    const apiKeyDiv = document.getElementById("apiKeyDiv");
    if (!apiKeyDiv) return;
    
    if (selectedProvider === "ollama") {
        apiKeyDiv.style.display = "none";
    } else {
        apiKeyDiv.style.display = "block";
    }
}

// ✅ Function to show initial greeting
function showWelcomeMessage() {
    const chatBody = document.getElementById("chatBody");
    if (chatBody && chatBody.children.length === 0) {
        botMessage("👋 Hello! What provider would you like to choose?<br>1️⃣ Gemini<br>2️⃣ OpenAI<br>3️⃣ Ollama<br><br>💡 <small>Tip: Type /change anytime to switch providers</small>");
        awaitingProvider = true;
    }
}

// Toggle Chat Window
function toggleChat() {
    const chatWindow = document.getElementById("chatbotWindow");
    const isOpening = chatWindow.style.display === "none" || chatWindow.style.display === "";

    chatWindow.style.display = isOpening ? "flex" : "none";
    chatWindow.classList.add('popup-animation');

    if (isOpening) {
        scrollChatToBottom();
    }
}

// Handle User Messages
async function sendMessage() {
    const inputField = document.getElementById("chatInput");
    const message = inputField.value.trim();
    if (message === "") return;

    userMessage(message);
    inputField.value = "";

    // Check for change provider command
    if (message.toLowerCase() === "/change" || message.toLowerCase() === "/switch") {
        changeProvider();
        return;
    }

    if (awaitingProvider) {
        handleProviderSelection(message);
        return;
    }

    if (awaitingApiKey) {
        handleApiKeyInput(message);
        return;
    }

    processUserQuery(message);
}

// NEW FUNCTION: Change Provider
function changeProvider() {
    botMessage("🔄 Switching provider... Which one would you like?<br>1️⃣ Gemini<br>2️⃣ OpenAI<br>3️⃣ Ollama");
    awaitingProvider = true;
    awaitingApiKey = false;
    selectedProvider = "";
    providerConfigured = false;
    sessionStorage.removeItem('selectedProvider');
    sessionStorage.removeItem('providerConfigured');
    updateApiKeyVisibility();
    scrollChatToBottom();
}

// Handle Provider Selection - FIXED VERSION
async function handleProviderSelection(message) {
    const input = message.toLowerCase().trim();
    let provider = "";

    if (input === "1" || input === "gemini") provider = "gemini";
    else if (input === "2" || input === "openai") provider = "openai";
    else if (input === "3" || input === "ollama") provider = "ollama";
    else {
        botMessage(`❌ Invalid selection. Please type:<br>1 for Gemini<br>2 for OpenAI<br>3 for Ollama`);
        scrollChatToBottom();
        return;
    }

    selectedProvider = provider;
    sessionStorage.setItem('selectedProvider', provider);
    
    // IMPORTANT: Set these flags to false/true immediately
    awaitingProvider = false;
    providerConfigured = true;
    sessionStorage.setItem('providerConfigured', 'true');

    // Update API key div visibility
    updateApiKeyVisibility();

    const providerName = provider.charAt(0).toUpperCase() + provider.slice(1);
    botMessage(`✅ ${providerName} selected! If not configured, please set it up in <a href='/settings/?tab=ai-config'>Settings</a>. You can now start chatting!`);
    scrollChatToBottom();
}

// Handle API Key Input - REMOVED, NOT USED ANYMORE
async function handleApiKeyInput(apiKey) {
    botMessage("⚠️ Please configure your API key in <a href='/settings/?tab=ai-config'>Settings</a> instead.");
    scrollChatToBottom();
}

// Process User Query
async function processUserQuery(message) {
    if (!selectedProvider || !providerConfigured) {
        botMessage("⚠️ Please select and configure a provider first. Type 1 for Gemini, 2 for OpenAI, or 3 for Ollama.");
        awaitingProvider = true;
        scrollChatToBottom();
        return;
    }

    const loadingMsgId = showLoadingMessage("Buddy is thinking...");

    try {
        const response = await fetch('/chatbot-response/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                message: message,
                provider: selectedProvider
            }),
        });

        removeLoadingMessage(loadingMsgId);

        if (!response.ok) throw new Error(`Server error: ${response.status}`);
        const data = await response.json();
        
        if (data.status === "error") {
            if (data.message && data.message.includes('not configured')) {
                botMessage(`⚠️ ${selectedProvider} is not configured. Please set it up in <a href='/settings/?tab=ai-config'>Settings</a>.`);
            } else if (data.message && data.message.includes('not found')) {
                botMessage(`⚠️ The selected model is not available. Please configure it in <a href='/settings/?tab=ai-config'>Settings</a>.`);
            } else {
                botMessage(data.message || "Sorry, I couldn't process that.");
            }
        } else {
            botMessage(data.message || "Sorry, I couldn't process that.");
        }
        scrollChatToBottom();

    } catch (error) {
        removeLoadingMessage(loadingMsgId);
        console.error("Error processing message:", error);
        botMessage("Oops! Something went wrong. Please try again.");
        scrollChatToBottom();
    }
}

// Show and remove loading messages
function showLoadingMessage(text) {
    const chatBody = document.getElementById("chatBody");
    const messageElement = document.createElement("div");
    messageElement.textContent = text;
    messageElement.className = "bot-message loading-message";
    messageElement.id = "loading-" + Date.now();
    chatBody.appendChild(messageElement);
    scrollChatToBottom();
    return messageElement.id;
}

function removeLoadingMessage(messageId) {
    if (!messageId) return;
    const loadingElement = document.getElementById(messageId);
    if (loadingElement) loadingElement.remove();
}

// Add messages to chat
function userMessage(text) {
    const chatBody = document.getElementById("chatBody");
    const messageElement = document.createElement("div");
    messageElement.textContent = text;
    messageElement.className = "user-message";
    chatBody.appendChild(messageElement);
    saveMessage(text, "user-message");
    scrollChatToBottom();
}

function botMessage(text) {
    const chatBody = document.getElementById("chatBody");
    const messageElement = document.createElement("div");
    messageElement.innerHTML = text;
    messageElement.className = "bot-message";
    chatBody.appendChild(messageElement);
    saveMessage(text, "bot-message");
    scrollChatToBottom();
}

// Scroll chat to bottom
function scrollChatToBottom() {
    const chatBody = document.getElementById("chatBody");
    if (chatBody) {
        chatBody.scrollTop = chatBody.scrollHeight;
    }
}

// Save/load chat history
function loadChatHistory() {
    const chatBody = document.getElementById("chatBody");
    const chatHistory = JSON.parse(sessionStorage.getItem('chatHistory')) || [];
    chatBody.innerHTML = '';
    chatHistory.forEach(msg => {
        const messageElement = document.createElement("div");
        messageElement.innerHTML = msg.text;
        messageElement.className = msg.type;
        chatBody.appendChild(messageElement);
    });
    scrollChatToBottom();
}

function saveMessage(text, type) {
    const chatHistory = JSON.parse(sessionStorage.getItem('chatHistory')) || [];
    chatHistory.push({ text, type });
    sessionStorage.setItem('chatHistory', JSON.stringify(chatHistory));
}

function clearChatHistory() {
    sessionStorage.removeItem('chatHistory');
    sessionStorage.removeItem('apiKeyMessageShown');
    sessionStorage.removeItem('selectedProvider');
    sessionStorage.removeItem('providerConfigured');
    sessionStorage.removeItem('chatSessionStarted');
    const chatBody = document.getElementById("chatBody");
    if (chatBody) {
        chatBody.innerHTML = '';
    }
}

// Enter key listener
document.getElementById("chatInput").addEventListener("keydown", function(event) {
    if (event.key === "Enter") {
        if (event.shiftKey) {
            event.preventDefault();
            this.value += "\n";
        } else {
            event.preventDefault();
            sendMessage();
            this.style.height = "auto";
        }
    }
});

// Fullscreen toggle
let isFullscreen = false;
function toggleFullscreen() {
    const chatbotWindow = document.querySelector('.chatbot-window');
    const fullscreenIcon = document.querySelector('.bi-fullscreen');
    const exitFullscreenIcon = document.querySelector('.bi-fullscreen-exit');

    if (!isFullscreen) {
        chatbotWindow.style.width = '80vw';
        chatbotWindow.style.height = '68vh';
        chatbotWindow.style.right = '0';
        fullscreenIcon.classList.add('d-none');
        exitFullscreenIcon.classList.remove('d-none');
    } else {
        chatbotWindow.style.width = '40vw';
        chatbotWindow.style.height = '58vh';
        chatbotWindow.style.right = '0';
        fullscreenIcon.classList.remove('d-none');
        exitFullscreenIcon.classList.add('d-none');
    }
    isFullscreen = !isFullscreen;
}