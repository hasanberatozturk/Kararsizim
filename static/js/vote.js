(function () {
  // Progressive enhancement: without JS the vote form posts normally.
  document.addEventListener("submit", function (event) {
    const form = event.target.closest(".vote-form");
    if (!form || !window.fetch) return;
    event.preventDefault();

    const button = event.submitter;
    if (!button || !button.value) return;

    const body = form.closest(".poll-body");
    const card = form.closest(".poll-card");
    const buttons = form.querySelectorAll("button");

    buttons.forEach(function (b) { b.disabled = true; });
    button.classList.add("is-loading");

    const token = form.querySelector("[name=csrfmiddlewaretoken]").value;
    const payload = new URLSearchParams({ option_id: button.value });

    fetch(form.action, {
      method: "POST",
      headers: {
        "X-CSRFToken": token,
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
      },
      credentials: "same-origin",
      body: payload,
    })
      .then(function (response) {
        return response.json().then(function (data) { return { status: response.status, data: data }; });
      })
      .then(function (result) {
        if (result.data.html) {
          body.innerHTML = result.data.html;
          return;
        }
        throw new Error(result.data.error || "Bir şeyler ters gitti.");
      })
      .catch(function (error) {
        buttons.forEach(function (b) { b.disabled = false; });
        button.classList.remove("is-loading");
        const box = card.querySelector(".vote-error");
        box.textContent = error.message || "Bağlantı hatası. Lütfen tekrar dene.";
        box.hidden = false;
      });
  });
})();
