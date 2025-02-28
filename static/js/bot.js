// System prompt to focus responses on technical topics
// const SYSTEM_PROMPT = `You are Buddy AI, a technical assistant specializing in:
// - Kubernetes (K8s) and container orchestration
// - Cloud computing (AWS, Azure, GCP)
// - Programming languages and development
// - Technical error handling and debugging
// - DevOps practices and tools
// - Infrastructure and system architecture
// - Cloud-native technologies
// - Technical best practices and patterns

// Only respond to questions related to these technical domains. For non-technical questions, politely inform the user that you're focused on technical topics and can't help with that query.

// Keep responses clear, concise, and technically accurate. When relevant, include code examples or command-line instructions.`;

// Flags for handling API key input
let awaitingProvider = false;
let awaitingApiKey = false;
let selectedProvider = "";

document.addEventListener('DOMContentLoaded', () => {
    checkAPIKey();
    loadChatHistory();
});

// Toggle Chat Window
function toggleChat() {
    var chatWindow = document.getElementById("chatbotWindow");
    chatWindow.style.display = chatWindow.style.display === "none" || chatWindow.style.display === "" ? "flex" : "none";

    if (chatWindow.style.display === "flex") {
        checkAPIKey();
    }
}

// Check if API Key Exists
async function checkAPIKey() {
    try {
        const response = await fetch('/check-api-key/');
        const data = await response.json();

        if (data.status === "missing") {
            botMessage("Hello! To start, please set up your AI API key.");
            botMessage("Which provider do you want to use? (openai/gemini)");
            awaitingProvider = true;
        }
    } catch (error) {
        console.error("Error checking API key:", error);
    }
}

// Handle User Messages
async function sendMessage() {
    const inputField = document.getElementById("chatInput");
    const message = inputField.value.trim();
    if (message === "") return;

    userMessage(message);
    inputField.value = "";

    if (awaitingProvider) {
        handleProviderSelection(message);
        return;
    }

    if (awaitingApiKey) {
        handleApiKeyInput(message);
        return;
    }

    // Process user query only if API key is set
    processUserQuery(message);
}

// Handle Provider Selection
function handleProviderSelection(message) {
    const provider = message.toLowerCase();
    if (!["openai", "gemini"].includes(provider)) {
        botMessage("Invalid provider. Please type 'openai' or 'gemini'.");
        return;
    }

    selectedProvider = provider;
    awaitingProvider = false;
    awaitingApiKey = true;
    botMessage(`Great! Now, please enter your ${provider.toUpperCase()} API key.`);
}

// Handle API Key Input
async function handleApiKeyInput(apiKey) {
    if (!apiKey) {
        botMessage("API key cannot be empty. Please enter a valid key.");
        return;
    }

    try {
        const response = await fetch('/set-api-key/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ provider: selectedProvider, api_key: apiKey }),
        });

        const data = await response.json();
        if (data.status === "success") {
            botMessage("API Key saved successfully! You can now ask me technical questions.");
            awaitingApiKey = false;
        } else {
            botMessage("Error saving API key: " + data.message);
        }
    } catch (error) {
        console.error("Error saving API key:", error);
    }
}

// Process User Query and Get AI Response
async function processUserQuery(message) {
    try {
        console.log("Sending message to backend:", message);

        const response = await fetch('/chatbot-response/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message }),
        });

        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }

        const data = await response.json();
        console.log("Received response from backend:", data);

        if (data.message) {
            botMessage(data.message);
        } else {
            botMessage("Sorry, I couldn't process that.");
        }

    } catch (error) {
        console.error("Error processing message:", error);
        botMessage("Oops! Something went wrong. Please try again.");
    }
}

// Add User Message to Chat
function userMessage(text) {
    const chatBody = document.getElementById("chatBody");
    const messageElement = document.createElement("div");
    messageElement.textContent = text;
    messageElement.className = "user-message";
    chatBody.appendChild(messageElement);
    saveMessage(text, "user-message");
    chatBody.scrollTop = chatBody.scrollHeight;
}

// Add Bot Message to Chat
function botMessage(text) {
    const chatBody = document.getElementById("chatBody");
    const messageElement = document.createElement("div");
    messageElement.textContent = text;
    messageElement.className = "bot-message";
    chatBody.appendChild(messageElement);
    saveMessage(text, "bot-message");
    chatBody.scrollTop = chatBody.scrollHeight;
}

// Load Chat History from Session Storage
function loadChatHistory() {
    const chatBody = document.getElementById("chatBody");
    const chatHistory = JSON.parse(sessionStorage.getItem('chatHistory')) || [];
    
    chatBody.innerHTML = '';
    
    chatHistory.forEach(message => {
        const messageElement = document.createElement("div");
        messageElement.textContent = message.text;
        messageElement.className = message.type;
        chatBody.appendChild(messageElement);
    });

    chatBody.scrollTop = chatBody.scrollHeight;
}

// Save Chat Message to Session Storage
function saveMessage(text, type) {
    const chatHistory = JSON.parse(sessionStorage.getItem('chatHistory')) || [];
    chatHistory.push({ text, type });
    sessionStorage.setItem('chatHistory', JSON.stringify(chatHistory));
}

// Clear Chat History
function clearChatHistory() {
    sessionStorage.removeItem('chatHistory');
    const chatBody = document.getElementById("chatBody");
    chatBody.innerHTML = '';
}

// Listen for "Enter" Key Press in Input Field
document.getElementById("chatInput").addEventListener("keypress", function(event) {
    if (event.key === "Enter") {
        event.preventDefault();
        sendMessage();
    }
});

let isFullscreen = false; // Flag to check if the window is in fullscreen mode

function toggleFullscreen() {
    const chatbotWindow = document.querySelector('.chatbot-window');
    const fullscreenIcon = document.querySelector('.bi-fullscreen'); // Fullscreen icon
    const exitFullscreenIcon = document.querySelector('.bi-fullscreen-exit'); // Exit fullscreen icon

    // Toggle fullscreen state
    if (!isFullscreen) {
        // Maximize the chat window to fullscreen
        chatbotWindow.style.width = '80vw'; // Full width
        chatbotWindow.style.height = '80vh'; // Full height
        chatbotWindow.style.right = '0'; // Stick to right

        // Show exit fullscreen icon, hide fullscreen icon
        fullscreenIcon.classList.add('d-none'); // Hide fullscreen icon
        exitFullscreenIcon.classList.remove('d-none'); // Show exit fullscreen icon
    } else {
        // Minimize the chat window to original size
        chatbotWindow.style.width = '40vw'; // Original width
        chatbotWindow.style.height = '60vh'; // Original height
        chatbotWindow.style.right = '0'; // Reset right margin

        // Show fullscreen icon, hide exit fullscreen icon
        fullscreenIcon.classList.remove('d-none'); // Show fullscreen icon
        exitFullscreenIcon.classList.add('d-none'); // Hide exit fullscreen icon
    }

    // Toggle the fullscreen state
    isFullscreen = !isFullscreen;
}
