function namespaceHandler(event) {
    let selectedNamespace = event.target.innerText.trim();
      let tableRows = document.querySelectorAll("tbody tr");
      tableRows.forEach(row => {
          let namespaceCell = row.querySelector("td:first-child");
          if (namespaceCell) {
              let namespace = namespaceCell.innerText.trim();
              if (selectedNamespace === "All Namespaces" || namespace === selectedNamespace) {
                  row.style.display = "table-row";
              } else {
                  row.style.display = "none";
              }
          }
      });
      document.getElementById("newDropdown").innerText = selectedNamespace;
  }