document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".purchase-tracker").forEach((tracker) => {
    const fill = tracker.querySelector(".purchase-tracker__line span");
    const steps = tracker.querySelectorAll(".purchase-tracker__step");
    const currentStep = Number(tracker.dataset.currentStep || 0);
    const currentVersion = tracker.dataset.trackerVersion || "";
    const count = steps.length;
    const storageKey = `orvend:purchase-tracker:${tracker.dataset.trackerKey}`;
    let previous = null;

    const reservarEspacioParaContenido = () => {
      const paginador = document.getElementById("paginadordecom");
      const alturaTracker = Math.ceil(tracker.getBoundingClientRect().height);
      document.body.classList.add("purchase-tracker-visible");
      document.documentElement.style.setProperty(
        "--purchase-tracker-space",
        `${alturaTracker + 36}px`,
      );
      if (paginador) paginador.style.marginBottom = "0";
    };

    reservarEspacioParaContenido();
    window.addEventListener("resize", reservarEspacioParaContenido);
    if ("ResizeObserver" in window) {
      new ResizeObserver(reservarEspacioParaContenido).observe(tracker);
    }

    try {
      previous = JSON.parse(sessionStorage.getItem(storageKey));
    } catch (_) {
      previous = null;
    }

    const denominator = Math.max(count - 1, 1);
    const stateChanged = previous && previous.version !== currentVersion;
    const startStep = stateChanged
      ? Math.max(currentStep - 1, 0)
      : previous
        ? Math.min(Number(previous.step || 0), currentStep)
        : 0;
    const start = (startStep / denominator) * 100;
    const target = (currentStep / denominator) * 100;

    fill.style.width = `${start}%`;
    steps.forEach((step, index) => {
      step.classList.toggle("is-complete", index <= startStep);
      step.classList.toggle("is-current", index === startStep);
    });

    requestAnimationFrame(() => {
      window.setTimeout(() => {
        fill.style.width = `${target}%`;
        steps.forEach((step, index) => {
          step.classList.toggle("is-complete", index <= currentStep);
          step.classList.toggle("is-current", index === currentStep);
        });
        reservarEspacioParaContenido();
      }, 120);
    });

    sessionStorage.setItem(
      storageKey,
      JSON.stringify({ step: currentStep, count, version: currentVersion }),
    );

    steps.forEach((step) => {
      if (!step.classList.contains("has-detail")) return;
      step.addEventListener("click", (event) => {
        event.stopPropagation();
        steps.forEach((otherStep) => {
          if (otherStep !== step) otherStep.classList.remove("is-detail-open");
        });
        step.classList.toggle("is-detail-open");
      });
      step.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          step.click();
        }
      });
    });

    document.addEventListener("click", () => {
      steps.forEach((step) => step.classList.remove("is-detail-open"));
    });
  });
});
