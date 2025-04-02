function copyToClipboard() {
    var copyText = document.getElementById("yamlContent");
    const copyButton = document.getElementById('copyButton');

    // Copy text using the Clipboard API
    navigator.clipboard.writeText(copyText.textContent || copyText.innerText)
        .then(() => {
            copyButton.textContent = 'Copied!';
            setTimeout(() => {
                copyButton.textContent = 'Copy YAML';
            }, 3000);
        })
        .catch(err => {
            console.error('Failed to copy:', err);
        });
}
