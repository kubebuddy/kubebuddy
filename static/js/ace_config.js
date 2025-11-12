window.addEventListener("DOMContentLoaded", function () {
    const editor = ace.edit("editor");
    editor.session.setMode("ace/mode/yaml");
    editor.setTheme("ace/theme/merbivore");
    editor.setOptions({
    tabSize: 2,
    useSoftTabs: true
    });

    document.querySelector("form").addEventListener("submit", () => {
        document.getElementById("yaml-output").value = editor.getValue();
    });
});