// Flags for handling API key input
let awaitingProvider = false;
let awaitingApiKey = false;
let selectedProvider = "";
let loadingMessageId = null;

document.addEventListener('DOMContentLoaded', () => {
    checkAPIKey();
    loadChatHistory();
});

// Toggle Chat Window
function toggleChat() {
    var chatWindow = document.getElementById("chatbotWindow");
    chatWindow.style.display = chatWindow.style.display === "none" || chatWindow.style.display === "" ? "flex" : "none";
    chatWindow.classList.add('popup-animation');
}

// Check if API Key Exists
async function checkAPIKey() {
    try {
        const response = await fetch('/check-api-key/');
        const data = await response.json();

        const apiKeyMessageShown = sessionStorage.getItem('apiKeyMessageShown');

        if (data.status === "missing" && !apiKeyMessageShown) {
            botMessage("Hello! To start, please set up your AI API key.");
            botMessage("Which provider do you want to use? <br> 1) Gemini <br> 2) OpenAI");
            awaitingProvider = true;
            sessionStorage.setItem('apiKeyMessageShown', 'true');
        } else {
            awaitingProvider = false;
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
    const input = message.toLowerCase();
    let provider = "";
    
    // Handle both number and text input
    if (input === "1" || input === "gemini") {
        provider = "gemini";
    } else if (input === "2" || input === "openai") {
        provider = "openai";
    } else {
        botMessage("Invalid selection. Please type '1' or 'Gemini' for Gemini, or '2' or 'OpenAI' for OpenAI or <a href='/settings/?tab=ai-config'>click here</a>");
        return;
    }

    selectedProvider = provider;
    awaitingProvider = false;
    awaitingApiKey = true;
    botMessage(`You selected ${provider.charAt(0).toUpperCase() + provider.slice(1)}. Now, please enter your ${provider.toUpperCase()} API key.`);
}

// Handle API Key Input
async function handleApiKeyInput(apiKey) {
    if (!apiKey) {
        botMessage("API key cannot be empty. Please enter a valid key.");
        return;
    }

    // Show loading message while validating API key
    const loadingMsgId = showLoadingMessage("Validating API key...");

    try {
        const response = await fetch('/validate-api-key/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ provider: selectedProvider, api_key: apiKey }),
        });

        const data = await response.json();
        
        // Remove loading message
        removeLoadingMessage(loadingMsgId);
        
        if (data.status === "valid") {
            // If valid, save the API key
            const saveResponse = await fetch('/set-api-key/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ provider: selectedProvider, api_key: apiKey }),
            });
            
            const saveData = await saveResponse.json();
            
            if (saveData.status === "success") {
                botMessage("API Key validated and saved successfully! You can now ask me technical questions.");
                awaitingApiKey = false;
            } else {
                botMessage("Error saving API key: " + saveData.message);
            }
        } else {
            botMessage("Invalid API key. Please check your key and try again.");
        }
    } catch (error) {
        // Remove loading message on error
        removeLoadingMessage(loadingMsgId);
        console.error("Error validating API key:", error);
        botMessage("An error occurred while validating your API key. Please try again.");
    }
}

// Process User Query and Get AI Response
async function processUserQuery(message) {
    try {
        // Show "Buddy is thinking" message
        const loadingMsgId = showLoadingMessage("Buddy is thinking...");
        
        const response = await fetch('/chatbot-response/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message }),
        });

        // Remove the "Buddy is thinking" message
        removeLoadingMessage(loadingMsgId);

        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }

        const data = await response.json();

        if (data.message) {
            botMessage(data.message);
        } else {
            botMessage("Sorry, I couldn't process that.");
        }

    } catch (error) {
        // Make sure to remove loading message on error
        if (loadingMsgId) {
            removeLoadingMessage(loadingMsgId);
        }
        console.error("Error processing message:", error);
        botMessage("Oops! Something went wrong. Please try again.");
    }
}

// Show a loading message and return its ID
function showLoadingMessage(text) {
    const chatBody = document.getElementById("chatBody");
    const messageElement = document.createElement("div");
    messageElement.textContent = text;
    messageElement.className = "bot-message loading-message";
    messageElement.id = "loading-" + Date.now();
    chatBody.appendChild(messageElement);
    chatBody.scrollTop = chatBody.scrollHeight;
    return messageElement.id;
}

// Remove a loading message by ID
function removeLoadingMessage(messageId) {
    if (messageId) {
        const loadingElement = document.getElementById(messageId);
        if (loadingElement) {
            loadingElement.remove();
        }
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

    messageElement.innerHTML = text; // Use innerHTML to render HTML properly
    messageElement.className = "bot-message";
    
    chatBody.appendChild(messageElement);
    saveMessage(text, "bot-message");
    chatBody.scrollTop = chatBody.scrollHeight;
}

// Load Chat History from Session Storage
function loadChatHistory() {
    const chatBody = document.getElementById("chatBody");
    const chatHistory = JSON.parse(sessionStorage.getItem('chatHistory')) || [];
    
    chatBody.innerHTML = ''; // Clear existing messages

    chatHistory.forEach(message => {
        const messageElement = document.createElement("div");

        // Use innerHTML to render formatted text properly
        messageElement.innerHTML = message.text; 
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
    sessionStorage.removeItem('apiKeyMessageShown'); // Reset the API key message flag
    const chatBody = document.getElementById("chatBody");
    chatBody.innerHTML = '';
}

// Listen for "Enter" Key Press in Input Field
document.getElementById("chatInput").addEventListener("keydown", function(event) {
    if (event.key === "Enter") {
        if (event.shiftKey) {
            event.preventDefault();
            this.value += "\n"; // Add a newline
            autoResize(this); // Adjust height
        } else {
            event.preventDefault();
            sendMessage();
            this.style.height = "auto"; // Reset height after sending
        }
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
        chatbotWindow.style.height = '68vh'; // Full height
        chatbotWindow.style.right = '0'; // Stick to right

        // Show exit fullscreen icon, hide fullscreen icon
        fullscreenIcon.classList.add('d-none'); // Hide fullscreen icon
        exitFullscreenIcon.classList.remove('d-none'); // Show exit fullscreen icon
    } else {
        // Minimize the chat window to original size
        chatbotWindow.style.width = '40vw'; // Original width
        chatbotWindow.style.height = '58vh'; // Original height
        chatbotWindow.style.right = '0'; // Reset right margin

        // Show fullscreen icon, hide exit fullscreen icon
        fullscreenIcon.classList.remove('d-none'); // Show fullscreen icon
        exitFullscreenIcon.classList.add('d-none'); // Hide exit fullscreen icon
    }

    // Toggle the fullscreen state
    isFullscreen = !isFullscreen;
}