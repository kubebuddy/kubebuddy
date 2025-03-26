document.querySelectorAll(".table").forEach(table => {
    table.classList.add("table", "table-striped","table-bordered","table-striped", "table-hover");
});

document.querySelectorAll("th").forEach(th => {
    th.classList.add("text-nowrap");
});