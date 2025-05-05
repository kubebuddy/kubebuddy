document.addEventListener("DOMContentLoaded", function () {
    const sidebar = document.getElementById("sidebar");
    const currentTheme = localStorage.getItem("theme");

    // Apply dark mode styles if stored preference is "dark"
    if (currentTheme === "dark") {
        document.body.classList.add("dark-mode");

        if (sidebar) {
            sidebar.classList.add("bg-dark", "text-white");
        }

        const navbar = document.querySelector(".navbar");
        if (navbar) {
            navbar.classList.add("navbar-dark", "bg-dark");
        }

        // Optionally dispatch an event if other components need to react
        document.dispatchEvent(new Event("darkModeChanged"));
    }

    // Highlight active sidebar link
    const sidebarLinks = document.querySelectorAll(".sidebar a");
    const currentUrl = window.location.pathname;

    function updateLinkStyles() {
        sidebarLinks.forEach(link => {
            const linkHref = link.getAttribute("href").split('?')[0];
            if (linkHref === currentUrl) {
                if (document.body.classList.contains("dark-mode")) {
                    link.style.backgroundColor = "#007acc";
                    link.style.color = "#ffffff";
                } else {
                    link.style.backgroundColor = "#8ddbff";
                    link.style.color = "";
                }
                link.style.borderRadius = "5px";
                link.style.padding = "5px 10px";
                link.scrollIntoView({ behavior: "smooth", block: "center" });
            }
        });
    }

    updateLinkStyles();

    // Observe dark mode class changes to update link styles accordingly
    const observer = new MutationObserver(() => {
        updateLinkStyles();
    });

    observer.observe(document.body, {
        attributes: true,
        attributeFilter: ['class']
    });
});