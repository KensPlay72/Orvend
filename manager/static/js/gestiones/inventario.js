document.addEventListener("DOMContentLoaded", () => {
  const tbody = document.querySelector("#tablaProductos tbody");
  const listaMovil = document.querySelector(".inventario-mobile-list");
  const img = document.getElementById("imgProducto");
  const cargando = document.getElementById("imagenCargando");
  const sinImagen = document.getElementById("sinImagenProducto");
  let solicitudActual = 0;
  let controladorBusqueda = null;

  const ocultarEstadosImagen = () => {
    cargando.classList.add("d-none");
    sinImagen.classList.add("d-none");
  };

  const mostrarCargandoImagen = () => {
    ocultarEstadosImagen();
    img.removeAttribute("src");
    img.classList.add("d-none");
    cargando.classList.remove("d-none");
  };

  const mostrarSinImagen = (mensaje = "El producto no tiene una imagen cargada") => {
    ocultarEstadosImagen();
    img.removeAttribute("src");
    img.classList.add("d-none");
    sinImagen.querySelector("span").textContent = mensaje;
    sinImagen.classList.remove("d-none");
  };

  tbody.addEventListener("click", async (e) => {
    const fila = e.target.closest("tr.fila-producto");
    if (!fila) return;

    const idProducto = fila.dataset.id;
    const yaSeleccionada = fila.classList.contains("selected");
    const solicitud = ++solicitudActual;

    document
      .querySelectorAll(".fila-producto.selected")
      .forEach((item) => item.classList.remove("selected"));
    if (yaSeleccionada) return;

    fila.classList.add("selected");
    mostrarCargandoImagen();

    try {
      controladorBusqueda?.abort();
      controladorBusqueda = new AbortController();
      const response = await fetch(`/manager/inventario/${idProducto}/`, {
        headers: { Accept: "application/json" },
        signal: controladorBusqueda.signal,
      });

      if (!response.ok) throw new Error("No se pudo obtener el producto");

      const data = await response.json();
      if (solicitud !== solicitudActual) return;

      renderInventario(data);

      if (!data.producto.tieneImagen) {
        mostrarSinImagen();
        return;
      }

      img.onload = () => {
        if (solicitud !== solicitudActual) return;
        ocultarEstadosImagen();
        img.classList.remove("d-none");
      };

      img.onerror = () => {
        if (solicitud !== solicitudActual) return;
        mostrarSinImagen("No fue posible cargar la imagen del producto");
      };

      img.src = data.producto.imagenUrl;
    } catch (error) {
      if (error.name !== "AbortError" && solicitud === solicitudActual) {
        mostrarSinImagen("No fue posible cargar la información del producto");
      }
    }
  });

  listaMovil?.addEventListener("click", async (e) => {
    const tarjeta = e.target.closest(".inventario-mobile-card");
    if (!tarjeta) return;
    const estabaAbierta = tarjeta.classList.contains("is-open");
    document.querySelectorAll(".inventario-mobile-card.is-open").forEach((item) => {
      item.classList.remove("is-open");
      item.querySelector(".inventario-mobile-card__header")?.setAttribute("aria-expanded", "false");
    });
    if (estabaAbierta) {
      solicitudActual += 1;
      controladorBusqueda?.abort();
      return;
    }

    const solicitud = ++solicitudActual;
    tarjeta.classList.add("is-open");
    tarjeta.querySelector(".inventario-mobile-card__header")?.setAttribute("aria-expanded", "true");
    try {
      controladorBusqueda?.abort();
      controladorBusqueda = new AbortController();
      const response = await fetch(`/manager/inventario/${tarjeta.dataset.id}/`, {
        headers: { Accept: "application/json" },
        signal: controladorBusqueda.signal,
      });
      if (!response.ok) throw new Error("No se pudo obtener el producto");
      const data = await response.json();
      if (solicitud !== solicitudActual) return;
      renderDetalleMovil(tarjeta, data);
    } catch (error) {
      if (error.name !== "AbortError" && solicitud === solicitudActual) {
        const lista = tarjeta.querySelector(".inventario-mobile-card__locations ul");
        if (lista) lista.innerHTML = "<li><span>No fue posible cargar las existencias.</span></li>";
      }
    }
  });
});

function renderInventario(data) {
  document.querySelectorAll("#tablaInventarioBody tr").forEach((tr) => {
    tr.querySelector(".cantidad").textContent = "0";
  });

  data.inventario.forEach((item) => {
    const fila = document.querySelector(
      `#tablaInventarioBody tr[data-id="${item.ubicacion}"]`,
    );

    if (fila) fila.querySelector(".cantidad").textContent = item.cantidad;
  });
}

function renderDetalleMovil(tarjeta, data) {
  const imagen = tarjeta.querySelector(".inventario-mobile-card__image img");
  const iconoImagen = tarjeta.querySelector(".inventario-mobile-card__image div > i");
  if (imagen && iconoImagen) {
    imagen.hidden = !data.producto.tieneImagen;
    iconoImagen.hidden = data.producto.tieneImagen;
    if (data.producto.tieneImagen) {
      imagen.onerror = () => {
        imagen.hidden = true;
        iconoImagen.hidden = false;
      };
      imagen.src = data.producto.imagenUrl;
    } else imagen.removeAttribute("src");
  }

  const lista = tarjeta.querySelector(".inventario-mobile-card__locations ul");
  if (!lista) return;
  lista.replaceChildren();
  const cantidadesPorUbicacion = new Map(
    data.inventario.map((item) => [item.ubicacion, item.cantidad]),
  );
  const ubicaciones = [...document.querySelectorAll("#tablaInventarioBody tr")].map(
    (fila) => ({
      ubicacion: fila.dataset.id,
      cantidad: cantidadesPorUbicacion.get(fila.dataset.id) ?? 0,
    }),
  );
  ubicaciones.forEach((item) => {
    const fila = document.createElement("li");
    const nombre = document.createElement("span");
    const cantidad = document.createElement("strong");
    nombre.textContent = item.ubicacion;
    cantidad.textContent = item.cantidad;
    fila.append(nombre, cantidad);
    lista.appendChild(fila);
  });
}
