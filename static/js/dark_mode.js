document.addEventListener("DOMContentLoaded", function () {
    const toggleButton = document.getElementById("darkModeToggle");
    const body = document.body;
    const sidebar = document.getElementById("sidebar"); // Optional sidebar element

    // Check localStorage for theme preference
    if (localStorage.getItem("theme") === "dark") {
        enableDarkMode();
    }

    // Toggle dark mode on button click
    if (toggleButton) { // Check if the button exists
        toggleButton.addEventListener("click", function () {
            if (body.classList.contains("dark-mode")) {
                disableDarkMode();
            } else {
                enableDarkMode();
            }
            document.dispatchEvent(new Event("darkModeChanged"));
        });
    }

    function enableDarkMode() {
        body.classList.add("dark-mode");
        if (sidebar) { // Only apply if sidebar exists
            sidebar.classList.add("bg-dark", "text-white");
        }
        if(document.querySelector(".navbar")){
            document.querySelector(".navbar").classList.add("navbar-dark", "bg-dark");
        }

        if(document.querySelectorAll("table")){
            document.querySelectorAll("table").forEach(table => {
                table.classList.add("table-dark");
            });
        }
        if(toggleButton){
            toggleButton.innerHTML = '<i class="bi bi-sun"></i>';
        }
        localStorage.setItem("theme", "dark");
    }

    function disableDarkMode() {
        body.classList.remove("dark-mode");
        if (sidebar) {
            sidebar.classList.remove("bg-dark", "text-white");
        }
        if(document.querySelector(".navbar")){
            document.querySelector(".navbar").classList.remove("navbar-dark", "bg-dark");
        }
        if(document.querySelectorAll("table")){
            document.querySelectorAll("table").forEach(table => {
                table.classList.remove("table-dark");
            });
        }
        if(toggleButton){
            toggleButton.innerHTML = '<i class="bi bi-moon-stars"></i>';
        }
        localStorage.setItem("theme", "light");
    }
});