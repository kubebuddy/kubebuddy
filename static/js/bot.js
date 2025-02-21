// Add this to your existing JavaScript section
const API_KEY = 'API Key'; // Replace with your actual API key
const API_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent';

async function sendMessage() {
    const inputField = document.getElementById("chatInput");
    const message = inputField.value.trim();
    if (message === "") return;
    
    const chatBody = document.getElementById("chatBody");
    
    // Add user message
    const userMessageElement = document.createElement("div");
    userMessageElement.textContent = message;
    userMessageElement.className = "user-message";
    chatBody.appendChild(userMessageElement);
    
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
                        text: message
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
        
        // Add bot response
        const botMessageElement = document.createElement("div");
        botMessageElement.textContent = botResponse;
        botMessageElement.className = "bot-message";
        chatBody.appendChild(botMessageElement);
        
    } catch (error) {
        // Remove typing indicator
        typingIndicator.remove();
        
        // Add error message
        const errorElement = document.createElement("div");
        errorElement.textContent = "Sorry, I encountered an error. Please try again.";
        errorElement.className = "bot-message error";
        chatBody.appendChild(errorElement);
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