const terminalIcon = document.getElementById('terminal-icon');
const terminalWindow = document.getElementById('terminal-window');
const closeTerminal = document.getElementById('close-terminal');
const terminalOutput = document.getElementById('terminal-output');
const input = document.getElementById('input');

// Toggle terminal visibility
terminalIcon.addEventListener('click', toggleTerminal);
closeTerminal.addEventListener('click', hideTerminal);

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
                    const response = await fetch(`/cluster_name/execute/`, {
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
    const terminalWindow = document.querySelector('#terminal-window');
    const fullscreenIcon = document.querySelector('.bi-fullscreen'); // Fullscreen icon
    const exitFullscreenIcon = document.querySelector('.bi-fullscreen-exit'); // Exit fullscreen icon

    // Toggle fullscreen state
    if (!terScreen) {
        // Maximize the chat window to fullscreen
        terminalWindow.style.width = '80vw'; // Full width
        terminalWindow.style.height = '73vh'; // Full height
        terminalWindow.style.right = '20px'; // Stick to right

        // Show exit fullscreen icon, hide fullscreen icon
        fullscreenIcon.classList.add('d-none'); // Hide fullscreen icon
        exitFullscreenIcon.classList.remove('d-none'); // Show exit fullscreen icon
    } else {
        // Minimize the chat window to original size
        terminalWindow.style.width = '50vw'; // Original width
        terminalWindow.style.height = '60vh'; // Original height
        terminalWindow.style.right = '20px'; // Reset right margin

        // Show fullscreen icon, hide exit fullscreen icon
        fullscreenIcon.classList.remove('d-none'); // Show fullscreen icon
        exitFullscreenIcon.classList.add('d-none'); // Hide exit fullscreen icon
    }

    // Toggle the fullscreen state
    terScreen = !terScreen;
}