const terminalIcon = document.getElementById('terminal-icon');
const terminalWindow = document.getElementById('terminal-window');
const closeTerminal = document.getElementById('close-terminal');
const terminalOutput = document.getElementById('terminal-output');
const input = document.getElementById('input');
const fullscreenButton = document.getElementById('fullscreen-terminal'); // Add this line to get the fullscreen button

// Toggle terminal visibility
terminalIcon.addEventListener('click', toggleTerminal);
closeTerminal.addEventListener('click', hideTerminal);
// Add fullscreen button event listener
if (fullscreenButton) {
    fullscreenButton.addEventListener('click', terminalFullscreen);
}

function toggleTerminal() {
    if (terminalWindow.style.display === 'flex') {
        hideTerminal();
    } else {
        showTerminal();
    }
}

function showTerminal() {
    terminalWindow.style.display = 'flex';
    terminalWindow.classList.add('popup-animation');
    input.focus();
}

function hideTerminal() {
    terminalWindow.style.display = 'none';
}

// Handle input
input.addEventListener('keydown', async (event) => {
    if (event.key === 'Enter') {
        const command = input.value.trim();
        if (command) {
            // Display the command
            const commandLine = document.createElement('div');
            commandLine.innerHTML = `<span class="prompt">user@host:~$</span> ${command}`;
            terminalOutput.appendChild(commandLine);

            // Handle clear/cls command
            if (command === 'clear' || command === 'cls') {
                terminalOutput.innerHTML = ''; // Clear the terminal output
            } else {
                // Send the command to the backend
                try {
                    const response = await fetch(`/execute/`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCookie('csrftoken'), // Ensure CSRF token is included
                        },
                        body: JSON.stringify({ command: command }),
                    });

                    const data = await response.json();
                    if (data.output) {
                        const outputLine = document.createElement('div');
                        outputLine.textContent = data.output;
                        terminalOutput.appendChild(outputLine);
                    } else if (data.error) {
                        const errorLine = document.createElement('div');
                        errorLine.textContent = data.error;
                        terminalOutput.appendChild(errorLine);
                    }
                } catch (error) {
                    const errorLine = document.createElement('div');
                    errorLine.textContent = `Error: ${error.message}`;
                    terminalOutput.appendChild(errorLine);
                }
            }

            // Clear the input
            input.value = '';

            // Scroll to the bottom
            terminalOutput.scrollTop = terminalOutput.scrollHeight;
        }
    }
});

let terScreen = false; // Flag to check if the window is in fullscreen mode

function terminalFullscreen() {
    const fullscreenIcon = document.querySelector('.bi-fullscreen'); // Fullscreen icon
    const exitFullscreenIcon = document.querySelector('.bi-fullscreen-exit'); // Exit fullscreen icon

    // Toggle fullscreen state
    if (!terScreen) {
        // Maximize the chat window to fullscreen
        terminalWindow.style.width = '80vw'; // Full width
        terminalWindow.style.height = '65vh'; // Full height
        terminalWindow.style.right = '20px'; // Stick to right

        // Show exit fullscreen icon, hide fullscreen icon
        if (fullscreenIcon) fullscreenIcon.classList.add('d-none'); // Hide fullscreen icon
        if (exitFullscreenIcon) exitFullscreenIcon.classList.remove('d-none'); // Show exit fullscreen icon
    } else {
        // Minimize the chat window to original size
        terminalWindow.style.width = '50vw'; // Original width
        terminalWindow.style.height = '55vh'; // Original height
        terminalWindow.style.right = '20px'; // Reset right margin

        // Show fullscreen icon, hide exit fullscreen icon
        if (fullscreenIcon) fullscreenIcon.classList.remove('d-none'); // Show fullscreen icon
        if (exitFullscreenIcon) exitFullscreenIcon.classList.add('d-none'); // Hide exit fullscreen icon
    }

    // Toggle the fullscreen state
    terScreen = !terScreen;
}

// Helper function to get CSRF token from cookies
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}