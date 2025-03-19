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