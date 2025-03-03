document.addEventListener("DOMContentLoaded", function () {
    let pageKey = "selectedNamespace_" + window.location.pathname; // Unique key per page
    let savedNamespace = sessionStorage.getItem(pageKey) || "All Namespaces";

    document.getElementById("newDropdown").innerText = savedNamespace;
    filterTable(savedNamespace);
});

function namespaceHandler(event) {
    let pageKey = "selectedNamespace_" + window.location.pathname; // Unique key per page
    let selectedNamespace = event.target.innerText.trim();

    sessionStorage.setItem(pageKey, selectedNamespace); // Save per page
    filterTable(selectedNamespace);
    document.getElementById("newDropdown").innerText = selectedNamespace;
}

function filterTable(namespace) {
    let tableRows = document.querySelectorAll("tbody tr");
    tableRows.forEach(row => {
        let namespaceCell = row.querySelector("td:first-child");
        if (namespaceCell) {
            let rowNamespace = namespaceCell.innerText.trim();
            row.style.display = (namespace === "All Namespaces" || rowNamespace === namespace) ? "table-row" : "none";
        }
    });
}
