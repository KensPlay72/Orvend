/* Muestra el cargador solamente para operaciones que modifican información. */
(() => {
  const loader = document.getElementById("managerGlobalLoader");
  if (!loader) return;

  let solicitudesActivas = 0;
  const metodosMutables = new Set(["POST", "PUT", "PATCH"]);

  const mostrar = () => {
    solicitudesActivas += 1;
    loader.hidden = false;
    document.body.classList.add("manager-loader-active");
  };

  const ocultar = () => {
    solicitudesActivas = Math.max(0, solicitudesActivas - 1);
    if (solicitudesActivas === 0) {
      loader.hidden = true;
      document.body.classList.remove("manager-loader-active");
    }
  };

  // Disponible para procesos puntuales que no empleen fetch ni un formulario.
  window.managerLoader = { mostrar, ocultar };

  const obtenerMetodo = (input, init) => {
    if (init?.method) return init.method.toUpperCase();
    if (input instanceof Request) return input.method.toUpperCase();
    return "GET";
  };

  const fetchOriginal = window.fetch.bind(window);
  window.fetch = function (input, init) {
    const metodo = obtenerMetodo(input, init);
    // Algunas acciones pequeñas, como marcar una notificación como leída,
    // no deben bloquear toda la pantalla con el cargador global.
    if (!metodosMutables.has(metodo) || init?.skipManagerLoader === true) {
      return fetchOriginal(input, init);
    }

    mostrar();
    return fetchOriginal(input, init).finally(ocultar);
  };

  // Este listener corre después de los listeners de cada formulario. Si el
  // formulario fue manejado por JS, fetch se encarga del cargador; si hará
  // navegación normal, se muestra hasta que la página se reemplace.
  document.addEventListener("submit", (event) => {
    const formulario = event.target;
    if (!(formulario instanceof HTMLFormElement) || event.defaultPrevented)
      return;

    const metodo = (formulario.method || "GET").toUpperCase();
    if (metodosMutables.has(metodo)) mostrar();
  });
})();
