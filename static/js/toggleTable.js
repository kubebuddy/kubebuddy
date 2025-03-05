document.addEventListener("DOMContentLoaded", function () {
    const allCheckbox = document.getElementById("All");
    const checkboxes = document.querySelectorAll(".column-checkbox:not(#All)");
    const tableHeaders = document.querySelectorAll("thead th");
    const tableRows = document.querySelectorAll("tbody tr");
    const pageKey = window.location.pathname;  // Unique key for different pages

    // message display
    const messageElements = document.querySelectorAll(".message-truncate");

    messageElements.forEach(element => {
        element.addEventListener("click", function () {
            const fullMessage = this.getAttribute("data-full");
            // Toggle between showing truncated message and full message
            if (this.textContent.length > 100) {
                this.textContent = fullMessage;
            } else {
                this.textContent = fullMessage.slice(0, 100) + "...";
            }
        });
    });

    // Function to save selection
    function saveSelection() {
        const selectedColumns = [];
        checkboxes.forEach(checkbox => {
            if (checkbox.checked) {
                selectedColumns.push(checkbox.value);
            }
        });
        localStorage.setItem(`selectedColumns_${pageKey}`, JSON.stringify(selectedColumns));
    }

    // Function to load selection from storage
    function loadSelection() {
        const savedSelection = JSON.parse(localStorage.getItem(`selectedColumns_${pageKey}`));
        
        if (savedSelection && savedSelection.length > 0) {
            checkboxes.forEach(checkbox => {
                checkbox.checked = savedSelection.includes(checkbox.value);
            });

            // Check "All" only if all individual columns are selected
            allCheckbox.checked = checkboxes.length === savedSelection.length;
        } else {
            // Default to all checked if no selection exists
            checkboxes.forEach(checkbox => (checkbox.checked = true));
            allCheckbox.checked = true;
            saveSelection();  // Save the default checked state
        }
        toggleColumns();
    }

    // Function to show/hide columns
    function toggleColumns() {
        let visibleColumnCount = 0; // Track visible columns
        checkboxes.forEach(checkbox => {
            const columnIndex = getColumnIndex(checkbox.value);
            if (columnIndex !== -1) {
                const displayStyle = checkbox.checked ? "table-cell" : "none";
                tableHeaders[columnIndex].style.display = displayStyle;
                tableRows.forEach(row => {
                    row.children[columnIndex].style.display = displayStyle;
                });
                if (checkbox.checked) {
                    visibleColumnCount++; // Increment visible column count
                }
            }
        });
        const actionsColumnIndex = tableHeaders.length - 1;
        if (actionsColumnIndex >= 0) {
            const shouldHideActions = visibleColumnCount === 0; // Hide if no other columns are visible
            tableHeaders[actionsColumnIndex].style.display = shouldHideActions ? "none" : "table-cell";
            tableRows.forEach(row => {
                row.children[actionsColumnIndex].style.display = shouldHideActions ? "none" : "table-cell";
            });
        }
    }

    // Function to get the column index by column name
    function getColumnIndex(columnName) {
        for (let i = 0; i < tableHeaders.length; i++) {
            if (
                tableHeaders[i].textContent
                    .replace(/[^a-zA-Z]+/g, '')  // Remove unwanted characters
                    .trim()  // Remove leading/trailing spaces
                    .replace(/\s+/g, "")  // Remove all spaces (including multiple spaces)
                    .toLowerCase() === 
                columnName
                    .replace(/[^a-zA-Z]+/g, '')
                    .trim()
                    .replace(/\s+/g, "")
                    .toLowerCase()
            ){
                return i;
            }
        }
        return -1;
    }

    // Event listener for individual checkboxes
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener("change", function () {
            // If any column is unchecked, remove "All" selection
            if (!this.checked) {
                allCheckbox.checked = false;
            }
            // If all are checked, set "All" to checked
            else if ([...checkboxes].every(cb => cb.checked)) {
                allCheckbox.checked = true;
            }

            toggleColumns();
            saveSelection();
        });
    });

    // Event listener for "All" checkbox
    allCheckbox.addEventListener("change", function () {
        checkboxes.forEach(checkbox => {
            checkbox.checked = this.checked;
        });
        toggleColumns();
        saveSelection();
    });

    // Load selections on page load
    loadSelection();
});
