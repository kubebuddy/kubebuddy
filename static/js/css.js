document.querySelectorAll(".table").forEach(table => {
    table.classList.add("table","table-bordered", "table-hover");
});

document.querySelectorAll("th").forEach(th => {
    th.classList.add("text-nowrap");
});