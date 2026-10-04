(function () {
  const form = document.getElementById("poll-form");
  if (!form) return;

  const min = Number(form.dataset.min);
  const max = Number(form.dataset.max);
  const list = document.getElementById("options-list");
  const addButton = document.getElementById("add-option");
  const counter = document.getElementById("option-count");

  function rows() {
    return list.querySelectorAll(".option-row");
  }

  function refresh() {
    const all = rows();
    all.forEach(function (row, index) {
      const input = row.querySelector("input");
      input.placeholder = "Seçenek " + (index + 1);
      input.setAttribute("aria-label", "Seçenek " + (index + 1));
      row.querySelector(".remove-option").disabled = all.length <= min;
    });
    addButton.disabled = all.length >= max;
    counter.textContent = all.length + " / " + max;
  }

  addButton.addEventListener("click", function () {
    if (rows().length >= max) return;
    const row = rows()[0].cloneNode(true);
    row.querySelector("input").value = "";
    list.appendChild(row);
    row.querySelector("input").focus();
    refresh();
  });

  list.addEventListener("click", function (event) {
    const button = event.target.closest(".remove-option");
    if (!button || rows().length <= min) return;
    button.closest(".option-row").remove();
    refresh();
  });

  refresh();
})();
