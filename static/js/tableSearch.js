document.addEventListener("DOMContentLoaded", function () {
    // searching table
    const searchInput = document.getElementById("tableSearchInput");
    
    function debounce(func, delay) {
        let timeout;
        return function (...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), delay);
        };
    }
    
    const filterTable = debounce(() => {
        const filter = searchInput.value.trim().toLowerCase();
        const rows = document.querySelectorAll("table tbody tr");
    
        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(filter) ? "" : "none";
        });
    }, 300); // delay
    
    searchInput.addEventListener("keyup", filterTable);

    // sorting columns
    document.querySelectorAll("th.sortable").forEach(header => {
        header.innerHTML += ' <i class="bi bi-arrow-down sort-indicator"></i>';
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
            
            document.querySelectorAll(".sort-indicator").forEach(indicator => indicator.HTML = " <i class='bi bi-arrow-down sort-indicator'></i>");
            // header.querySelector(".sort-indicator").classList = newState === "asc" ? "" : "";
            if (newState === 'asc'){
                header.querySelector(".sort-indicator").classList.remove("bi-arrow-down");
                header.querySelector(".sort-indicator").classList.add("bi-arrow-up");
            } else{
                header.querySelector(".sort-indicator").classList.remove("bi-arrow-up");
                header.querySelector(".sort-indicator").classList.add("bi-arrow-down");
            }
        });
    });
});
