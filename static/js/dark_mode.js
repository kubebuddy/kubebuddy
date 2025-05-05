document.addEventListener("DOMContentLoaded", function () {
    const sidebarLinks = document.querySelectorAll(".sidebar a");
    const currentUrl = window.location.pathname;

    sidebarLinks.forEach(link => {
        const linkHref = link.getAttribute("href").split("?")[0];

        if (linkHref === currentUrl) {
            // Reset styles for all links first (optional but safer)
            sidebarLinks.forEach(l => {
                l.style.backgroundColor = "";
                l.style.color = "";
                l.style.borderRadius = "";
                l.style.padding = "";
            });

            // Apply styles to the active link
            link.style.backgroundColor = "#007acc";
            link.style.color = "#ffffff";
            link.style.borderRadius = "5px";
            link.style.padding = "5px 10px";
            link.scrollIntoView({ behavior: "smooth", block: "center" });
        }
    });
});
