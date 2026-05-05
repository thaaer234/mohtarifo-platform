(function () {
  const protectedContent = document.querySelector(".protected-content");
  const watermark = document.body.dataset.studentWatermark || "";

  if (!protectedContent) {
    return;
  }

  document.documentElement.classList.add("has-protected-content");

  const blockEvent = function (event) {
    event.preventDefault();
    event.stopPropagation();
    return false;
  };

  ["contextmenu", "copy", "cut", "dragstart"].forEach(function (eventName) {
    document.addEventListener(eventName, blockEvent);
  });

  document.addEventListener("keydown", function (event) {
    const key = event.key.toLowerCase();
    const protectedCombo =
      event.key === "PrintScreen" ||
      (event.ctrlKey && ["s", "p", "u"].includes(key)) ||
      (event.ctrlKey && event.shiftKey && ["i", "j", "c"].includes(key)) ||
      (event.metaKey && event.shiftKey && ["3", "4", "5"].includes(key));

    if (protectedCombo) {
      blockEvent(event);
      document.body.classList.add("capture-guard");
      window.setTimeout(function () {
        document.body.classList.remove("capture-guard");
      }, 2500);
    }
  });

  document.addEventListener("visibilitychange", function () {
    document.body.classList.toggle("capture-guard", document.hidden);
  });

  window.addEventListener("blur", function () {
    document.body.classList.add("capture-guard");
  });

  window.addEventListener("focus", function () {
    document.body.classList.remove("capture-guard");
  });

  if (watermark) {
    document.querySelectorAll(".video-watermark span").forEach(function (item) {
      item.textContent = watermark;
    });
  }
})();
