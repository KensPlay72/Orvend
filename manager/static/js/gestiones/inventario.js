document.addEventListener("DOMContentLoaded", () => {
  const tbody = document.querySelector("#tablaProductos tbody");
  const img = document.getElementById("imgProducto");
  const cargando = document.getElementById("imagenCargando");
  const sinImagen = document.getElementById("sinImagenProducto");
  let solicitudActual = 0;

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
    const solicitud = ++solicitudActual;

    document
      .querySelectorAll(".fila-producto.selected")
      .forEach((item) => item.classList.remove("selected"));
    fila.classList.add("selected");
    mostrarCargandoImagen();

    try {
      const response = await fetch(`/manager/inventario/${idProducto}/`, {
        headers: { Accept: "application/json" },
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
      if (solicitud === solicitudActual) {
        mostrarSinImagen("No fue posible cargar la información del producto");
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
