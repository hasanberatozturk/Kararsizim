// Django messages → kaybolan toast bildirimleri
(function () {
  document.querySelectorAll(".message").forEach(function (toast, index) {
    setTimeout(function () {
      toast.classList.add("is-hiding");
      setTimeout(function () { toast.remove(); }, 350);
    }, 4000 + index * 500);
  });
})();
