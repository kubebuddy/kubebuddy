// Constants
const API_KEY = 'API KEY';
const API_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent';

// System prompt to focus responses on technical topics
const SYSTEM_PROMPT = `You are Buddy AI, a technical assistant specializing in:
- Kubernetes (K8s) and container orchestration
- Cloud computing (AWS, Azure, GCP)
- Programming languages and development
- Technical error handling and debugging
- DevOps practices and tools
- Infrastructure and system architecture
- Cloud-native technologies
- Technical best practices and patterns

Only respond to questions related to these technical domains. For non-technical questions, politely inform the user that you're focused on technical topics and can't help with that query.

Keep responses clear, concise, and technically accurate. When relevant, include code examples or command-line instructions.`;

// Initialize chat history from session storage when the page loads
document.addEventListener('DOMContentLoaded', () => {
    loadChatHistory();
});

// Load chat history from session storage
function loadChatHistory() {
    const chatBody = document.getElementById("chatBody");
    const chatHistory = JSON.parse(sessionStorage.getItem('chatHistory')) || [];
    
    // Clear existing messages
    chatBody.innerHTML = '';
    
    // Recreate each message from history
    chatHistory.forEach(message => {
        const messageElement = document.createElement("div");
        messageElement.textContent = message.text;
        messageElement.className = message.type;
        chatBody.appendChild(messageElement);
    });
    
    // Scroll to bottom
    chatBody.scrollTop = chatBody.scrollHeight;
}

// Save a message to session storage
function saveMessage(text, type) {
    const chatHistory = JSON.parse(sessionStorage.getItem('chatHistory')) || [];
    chatHistory.push({ text, type });
    sessionStorage.setItem('chatHistory', JSON.stringify(chatHistory));
}

// Clear chat history
function clearChatHistory() {
    sessionStorage.removeItem('chatHistory');
    const chatBody = document.getElementById("chatBody");
    chatBody.innerHTML = '';
}

async function sendMessage() {
    const inputField = document.getElementById("chatInput");
    const message = inputField.value.trim();
    if (message === "") return;
    
    const chatBody = document.getElementById("chatBody");
    
    // Add and save user message
    const userMessageElement = document.createElement("div");
    userMessageElement.textContent = message;
    userMessageElement.className = "user-message";
    chatBody.appendChild(userMessageElement);
    saveMessage(message, "user-message");
    
    // Show typing indicator
    const typingIndicator = document.createElement("div");
    typingIndicator.className = "bot-message typing-indicator";
    typingIndicator.textContent = "Buddy is thinking...";
    chatBody.appendChild(typingIndicator);
    
    // Clear input
    inputField.value = "";
    chatBody.scrollTop = chatBody.scrollHeight;

    try {
        const response = await fetch(`${API_URL}?key=${API_KEY}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                contents: [{
                    parts: [{
                        text: SYSTEM_PROMPT + "\n\nUser: " + message
                    }]
                }]
            })
        });

        if (!response.ok) {
            throw new Error('API request failed');
        }

        const data = await response.json();
        const botResponse = data.candidates[0].content.parts[0].text;
        
        // Remove typing indicator
        typingIndicator.remove();
        
        // Add and save bot response
        const botMessageElement = document.createElement("div");
        botMessageElement.textContent = botResponse;
        botMessageElement.className = "bot-message";
        chatBody.appendChild(botMessageElement);
        saveMessage(botResponse, "bot-message");
        
    } catch (error) {
        // Remove typing indicator
        typingIndicator.remove();
        
        // Add and save error message
        const errorMessage = "Sorry, you haven't configured your API key yet.";
        const errorElement = document.createElement("div");
        errorElement.textContent = errorMessage;
        errorElement.className = "bot-message error";
        chatBody.appendChild(errorElement);
        saveMessage(errorMessage, "bot-message error");
    }
    
    chatBody.scrollTop = chatBody.scrollHeight;
}

// Add event listener for Enter key
document.getElementById("chatInput").addEventListener("keypress", function(event) {
    if (event.key === "Enter") {
        event.preventDefault();
        sendMessage();
    }
});

function toggleChat() {
    var chatWindow = document.getElementById("chatbotWindow");
    chatWindow.style.display = chatWindow.style.display === "none" || chatWindow.style.display === "" ? "flex" : "none";
}