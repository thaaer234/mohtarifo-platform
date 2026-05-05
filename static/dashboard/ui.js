(function () {
  document.querySelectorAll("form").forEach(function (form) {
    form.addEventListener("submit", function () {
      const button = form.querySelector("button[type='submit'], input[type='submit']");
      if (!button || button.dataset.loading === "true") {
        return;
      }
      button.dataset.originalText = button.textContent || button.value || "";
      button.dataset.loading = "true";
      if (button.tagName === "INPUT") {
        button.value = "جار المعالجة...";
      } else {
        button.textContent = "جار المعالجة...";
      }
      button.classList.add("is-loading");
    });
  });
})();
