document.addEventListener("DOMContentLoaded", function () {
    const searchInput = document.getElementById("tableSearchInput");
    
    searchInput.addEventListener("keyup", function () {
        const filter = searchInput.value.toLowerCase();
        const rows = document.querySelectorAll("table tbody tr");
        
        rows.forEach(row => {
            const text = row.innerText.toLowerCase();
            if (text.includes(filter)) {
                row.style.display = "";
            } else {
                row.style.display = "none";
            }
        });
    });

    document.querySelectorAll("th.sortable").forEach(header => {
        header.innerHTML += ' <span class="sort-indicator">↕</span>';
        header.style.cursor = "pointer";
        header.addEventListener("click", function () {
            const table = header.closest("table");
            const tbody = table.querySelector("tbody");
            const rows = Array.from(tbody.querySelectorAll("tr"));
            const index = Array.from(header.parentNode.children).indexOf(header);
            const currentState = header.getAttribute("data-sort") || "desc";
            const newState = currentState === "asc" ? "desc" : "asc";
            
            header.setAttribute("data-sort", newState);
            
            rows.sort((rowA, rowB) => {
                const cellA = rowA.children[index].innerText.trim().toLowerCase();
                const cellB = rowB.children[index].innerText.trim().toLowerCase();
                return newState === "asc" ? cellA.localeCompare(cellB) : cellB.localeCompare(cellA);
            });
            
            rows.forEach(row => tbody.appendChild(row));
            
            document.querySelectorAll(".sort-indicator").forEach(indicator => indicator.innerText = "↕");
            header.querySelector(".sort-indicator").innerText = newState === "asc" ? "▲" : "▼";
        });
    });
});
