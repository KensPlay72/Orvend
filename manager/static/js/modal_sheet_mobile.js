(() => {
  const porcentajeCierre = 0.8;
  const alturaMinima = 0.28;
  const alturaMaxima = 0.88;

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".modal-sheet-mobile").forEach((modal) => {
      const dialogo = modal.querySelector(".modal-dialog");
      const encabezado = modal.querySelector(".modal-header");
      if (!dialogo || !encabezado) return;

      let inicioY = 0;
      let desplazamiento = 0;
      let alturaInicial = 0;
      let arrastrando = false;

      const esMovil = () => window.matchMedia("(max-width: 1032px)").matches;
      const limpiarTransformacion = () => {
        dialogo.style.removeProperty("transform");
        dialogo.style.removeProperty("transition");
      };

      const restaurarApertura = () => {
        dialogo.style.removeProperty("height");
        limpiarTransformacion();
      };

      encabezado.addEventListener("pointerdown", (evento) => {
        if (!esMovil() || evento.target.closest("button, input, a")) return;
        evento.preventDefault();
        inicioY = evento.clientY;
        desplazamiento = 0;
        alturaInicial = dialogo.getBoundingClientRect().height;
        arrastrando = true;
        dialogo.classList.add("modal-sheet-mobile--dragging");
        encabezado.setPointerCapture?.(evento.pointerId);
      });

      encabezado.addEventListener("pointermove", (evento) => {
        if (!arrastrando) return;
        desplazamiento = evento.clientY - inicioY;
        // Los paneles cortos (por ejemplo Apertura de caja) conservan su
        // altura natural al arrastrarlos; no deben crecer de golpe al tocar
        // el encabezado.
        const limiteInferiorBase = window.innerHeight * alturaMinima;
        const limiteInferior = modal.classList.contains("modal-sheet-mobile--auto")
          ? Math.min(alturaInicial, limiteInferiorBase)
          : limiteInferiorBase;
        const limiteSuperior = Math.min(window.innerHeight * alturaMaxima, 720);
        const nuevaAltura = Math.min(
          limiteSuperior,
          Math.max(limiteInferior, alturaInicial - desplazamiento),
        );
        // Las hojas con alto máximo lo definen con !important en CSS. El
        // mismo nivel de prioridad permite reducirlas mientras se arrastran.
        dialogo.style.setProperty("height", `${nuevaAltura}px`, "important");
      });

      const finalizar = (evento) => {
        if (!arrastrando) return;
        arrastrando = false;
        encabezado.releasePointerCapture?.(evento.pointerId);
        dialogo.classList.remove("modal-sheet-mobile--dragging");
        if (desplazamiento > 0 && desplazamiento / alturaInicial >= porcentajeCierre) {
          bootstrap.Modal.getInstance(modal)?.hide();
          return;
        }
        // Mantiene el alto elegido para que el usuario pueda consultar la
        // pantalla de Caja que queda detrás del panel.
      };

      encabezado.addEventListener("pointerup", finalizar);
      encabezado.addEventListener("pointercancel", finalizar);
      modal.addEventListener("shown.bs.modal", restaurarApertura);
      modal.addEventListener("hidden.bs.modal", () => {
        dialogo.classList.remove("modal-sheet-mobile--dragging");
        restaurarApertura();
      });
    });
  });
})();
