document.addEventListener("DOMContentLoaded", function () {
    let pageKey = "selectedNamespaces_" + window.location.pathname;
    let savedNamespaces = JSON.parse(sessionStorage.getItem(pageKey)) || ["All Namespaces"];

    // Restore checkbox states
    document.querySelectorAll(".namespace-checkbox").forEach(checkbox => {
        if (savedNamespaces.includes(checkbox.value)) {
            checkbox.checked = true;
        }
    });

    // Handle "All Namespaces" selection
    if (savedNamespaces.includes("All Namespaces")) {
        document.getElementById("allNamespaces").checked = true;
    }

    updateDropdownText(savedNamespaces);
    filterTable(savedNamespaces);
});

function namespaceHandler() {
    let pageKey = "selectedNamespaces_" + window.location.pathname;
    let selectedNamespaces = [];

    document.querySelectorAll(".namespace-checkbox:checked").forEach(checkbox => {
        selectedNamespaces.push(checkbox.value);
    });

    if (selectedNamespaces.length === 0) {
        // Default back to "All Namespaces" if nothing is selected
        selectedNamespaces = ["All Namespaces"];
        document.getElementById("allNamespaces").checked = true;
    } else {
        document.getElementById("allNamespaces").checked = false;
    }

    sessionStorage.setItem(pageKey, JSON.stringify(selectedNamespaces));
    updateDropdownText(selectedNamespaces);
    filterTable(selectedNamespaces);
}

function toggleAllNamespaces() {
    let pageKey = "selectedNamespaces_" + window.location.pathname;
    let allNamespacesChecked = document.getElementById("allNamespaces").checked;

    if (allNamespacesChecked) {
        // Uncheck all individual namespace checkboxes
        document.querySelectorAll(".namespace-checkbox").forEach(checkbox => checkbox.checked = false);
        sessionStorage.setItem(pageKey, JSON.stringify(["All Namespaces"]));
        updateDropdownText(["All Namespaces"]);
        filterTable(["All Namespaces"]);
    }
}

function updateDropdownText(selectedNamespaces) {
    let dropdownText = selectedNamespaces.includes("All Namespaces") ? "All Namespaces" : selectedNamespaces.join(", ");
    document.getElementById("newDropdown").innerText = dropdownText || "Select Namespaces";
}

function filterTable(selectedNamespaces) {
    let tableRows = document.querySelectorAll("tbody tr");

    tableRows.forEach(row => {
        let namespaceCell = row.querySelector("td:first-child");
        if (namespaceCell) {
            let rowNamespace = namespaceCell.innerText.trim();
            let isVisible = selectedNamespaces.includes("All Namespaces") || selectedNamespaces.includes(rowNamespace);
            row.style.display = isVisible ? "table-row" : "none";
        }
    });
}