document.addEventListener("DOMContentLoaded", function () {
    // Get the current hash from the URL
    let hash = window.location.hash;
    
    if (hash) {
        // Remove 'active' class from all tabs
        document.querySelectorAll(".nav-link").forEach(tab => {
            tab.classList.remove("active");
        });

        document.querySelectorAll(".tab-pane").forEach(content => {
            content.classList.remove("show", "active");
        });

        // Activate the tab with the matching hash
        let activeTab = document.querySelector(`a[href="${hash}"]`);
        if (activeTab) {
            activeTab.classList.add("active");

            let activeContent = document.querySelector(hash);
            if (activeContent) {
                activeContent.classList.add("show", "active");
            }
        }
    }

    // Update URL hash when a tab is clicked
    document.querySelectorAll('.nav-link').forEach(tab => {
        tab.addEventListener('click', function () {
            history.pushState(null, null, this.getAttribute('href'));
        });
    });
});