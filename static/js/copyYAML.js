function copyToClipboard() {
    var copyText = document.getElementById("yamlContent");
    const copyButton = document.getElementById('copyButton');
    
    // Create a temporary textarea to copy the text
    var textArea = document.createElement("textarea");
    textArea.value = copyText.textContent || copyText.innerText;
    document.body.appendChild(textArea);
    
    // Select and copy the text
    textArea.select();
    document.execCommand("copy");

    copyButton.textContent = 'Copied!';

    // After 3 seconds, change button text back to "Copy YAML"
    setTimeout(() => {
        copyButton.textContent = 'Copy YAML';
    }, 3000);
}