function validarSoloNumeros(input) {
  input.value = input.value.replace(/\D/g, "");
}

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("formConfiguracion");
  const inputLogo = document.getElementById("logoEmpresa");
  const logoPreview = document.getElementById("logoPreview");
  const botonGuardar = document.getElementById("guardarConfiguracion");
  let logo = null;
  let quitarLogo = false;
  const bannersEliminar = new Set();
  const inputBanner = document.getElementById("bannerPrincipal");
  const inputCarrusel = document.getElementById("carruselTienda");
  let carruselArchivos = [];
  const validarMedida = (file) =>
    new Promise((resolve) => {
      const imagen = new Image();
      imagen.onload = () => {
        URL.revokeObjectURL(imagen.src);
        resolve(imagen.naturalWidth === 1920 && imagen.naturalHeight === 640);
      };
      imagen.onerror = () => resolve(false);
      imagen.src = URL.createObjectURL(file);
    });
  const activarCarrusel = () => {
    const vista = document.getElementById("carruselPreview"),
      items = [...vista.querySelectorAll("figure")],
      dots = document.getElementById("carruselDots"),
      anterior = document.getElementById("carruselPrev"),
      siguiente = document.getElementById("carruselNext");
    let indice = 0;
    anterior.hidden = siguiente.hidden = items.length < 2;
    dots.hidden = items.length < 2;
    dots.innerHTML = items
      .map(
        (_, i) =>
          `<button type="button" class="${i ? "" : "active"}"></button>`,
      )
      .join("");
    const mover = (n) => {
      if (!items.length) return;
      indice = (n + items.length) % items.length;
      vista.scrollTo({ left: vista.clientWidth * indice, behavior: "smooth" });
      [...dots.children].forEach((d, i) =>
        d.classList.toggle("active", i === indice),
      );
    };
    anterior.onclick = () => mover(indice - 1);
    siguiente.onclick = () => mover(indice + 1);
    [...dots.children].forEach((d, i) => (d.onclick = () => mover(i)));
    if (items.length > 1 && !vista.dataset.auto) {
      vista.dataset.auto = "true";
      setInterval(() => siguiente.click(), 3500);
    }
  };

  document
    .getElementById("carruselPreview")
    ?.addEventListener("click", (event) => {
      const boton = event.target.closest(".config-banner-remove");
      if (!boton) return;
      const tarjeta = boton.closest("figure");
      if (tarjeta.dataset.bannerId)
        bannersEliminar.add(Number(tarjeta.dataset.bannerId));
      if (tarjeta.dataset.archivoIndice !== undefined) {
        carruselArchivos.splice(Number(tarjeta.dataset.archivoIndice), 1);
        renderCarruselPendiente();
        return;
      }
      tarjeta.remove();
    });

  document
    .querySelector(".config-banner-main-remove")
    ?.addEventListener("click", async (event) => {
      const boton = event.currentTarget;
      const resultado = await Swal.fire({
        title: "¿Eliminar banner?",
        text: "La imagen se eliminará al guardar la configuración.",
        icon: "warning",
        showCancelButton: true,
        confirmButtonText: "Sí, eliminar",
        cancelButtonText: "Cancelar",
        customClass: { confirmButton: "classbotones" },
      });
      if (!resultado.isConfirmed) return;
      bannersEliminar.add(Number(boton.dataset.bannerId));
      document.getElementById("bannerPreviewBox").innerHTML =
        '<div class="config-banner-default" id="bannerPreview">Vista predeterminada de la tienda</div>';
    });

  const renderCarruselPendiente = () => {
    const grid = document.getElementById("carruselPreview");
    grid.innerHTML = "";
    carruselArchivos.forEach((file, indice) => {
      const figure = document.createElement("figure");
      figure.dataset.archivoIndice = indice;
      figure.innerHTML = `<img src="${URL.createObjectURL(file)}" alt="Vista previa"><button type="button" class="config-banner-remove" aria-label="Quitar imagen"><i class="bx bx-x"></i></button>`;
      grid.appendChild(figure);
    });
    if (!carruselArchivos.length)
      grid.innerHTML =
        '<span id="carruselVacio">Aún no has agregado imágenes.</span>';
    activarCarrusel();
  };

  inputBanner?.addEventListener("change", async () => {
    if (!inputBanner.files[0]) return;
    if (!(await validarMedida(inputBanner.files[0]))) {
      inputBanner.value = "";
      Swal.fire(
        "Medida incorrecta",
        "El banner debe medir 1920 × 640 píxeles.",
        "warning",
      );
      return;
    }
    const box = document.getElementById("bannerPreviewBox");
    box.innerHTML = '<img id="bannerPreview" alt="Vista previa del banner">';
    document.getElementById("bannerPreview").src = URL.createObjectURL(
      inputBanner.files[0],
    );
  });

  const carruselVista = document.getElementById("carruselPreview");
  if (carruselVista && carruselVista.querySelectorAll("figure").length > 1) {
    setInterval(() => {
      const limite = carruselVista.scrollWidth - carruselVista.clientWidth;
      carruselVista.scrollTo({
        left:
          carruselVista.scrollLeft >= limite - 2
            ? 0
            : carruselVista.scrollLeft + carruselVista.clientWidth,
        behavior: "smooth",
      });
    }, 3500);
  }
  inputCarrusel?.addEventListener("change", async () => {
    for (const file of inputCarrusel.files)
      if (!(await validarMedida(file))) {
        inputCarrusel.value = "";
        Swal.fire(
          "Medida incorrecta",
          "Cada imagen debe medir 1920 × 640 píxeles.",
          "warning",
        );
        return;
      }
    carruselArchivos.push(...inputCarrusel.files);
    inputCarrusel.value = "";
    renderCarruselPendiente();
  });
  activarCarrusel();

  inputLogo.addEventListener("change", () => {
    const archivo = inputLogo.files?.[0];
    if (!archivo) return;
    if (!["image/jpeg", "image/png", "image/webp"].includes(archivo.type)) {
      inputLogo.value = "";
      Swal.fire({
        icon: "warning",
        title: "Formato inválido",
        text: "Selecciona un logo JPG, PNG o WEBP.",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });
      return;
    }
    logo = archivo;
    quitarLogo = false;
    logoPreview.src = URL.createObjectURL(archivo);
  });

  document.getElementById("quitarLogo").addEventListener("click", () => {
    logo = null;
    quitarLogo = true;
    inputLogo.value = "";
    logoPreview.src = "/static/img/LH.png";
  });

  form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const nombre = document.getElementById("nombreComercial").value.trim();
    if (!nombre) {
      Swal.fire({
        icon: "warning",
        title: "Dato requerido",
        text: "Ingresa el nombre comercial del negocio.",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });
      return;
    }
    const datos = new FormData();
    [
      ["nombre_comercial", nombre],
      ["razon_social", "razonSocial"],
      ["rtn", "rtnEmpresa"],
      ["telefono", "telefonoEmpresa"],
      ["email", "emailEmpresa"],
      ["direccion", "direccionEmpresa"],
      ["mensaje_factura", "mensajeFactura"],
    ].forEach(([campo, valor]) =>
      datos.append(
        campo,
        campo === "nombre_comercial"
          ? valor
          : document.getElementById(valor).value.trim(),
      ),
    );
    datos.append("quitar_logo", quitarLogo);
    datos.append("moneda", document.getElementById("monedaSistema").value);
    const diasCotizacion = document.getElementById("cotizacionDiasValidez");
    if (diasCotizacion)
      datos.append("cotizacion_dias_validez", diasCotizacion.value.trim());
    const disenoFactura = document.querySelector(
      'input[name="disenoFactura"]:checked',
    );
    if (disenoFactura) datos.append("diseno_factura", disenoFactura.value);
    const colorPrimario = document.getElementById("tiendaColorPrimario");
    if (colorPrimario) {
      datos.append("tienda_color_primario", colorPrimario.value);
      datos.append(
        "tienda_color_secundario",
        document.getElementById("tiendaColorSecundario").value,
      );
      datos.append(
        "tienda_color_acento",
        document.getElementById("tiendaColorAcento").value,
      );
      datos.append(
        "tienda_subtitulo",
        document.getElementById("tiendaSubtitulo").value.trim(),
      );
    }
    datos.append("eliminar_banners", JSON.stringify([...bannersEliminar]));
    if (inputBanner?.files[0])
      datos.append("banner_principal", inputBanner.files[0]);
    carruselArchivos.forEach((banner) => datos.append("carrusel", banner));
    if (logo) datos.append("logo", logo);
    try {
      botonGuardar.disabled = true;
      const respuesta = await fetch(CONFIGURACION_URL, {
        method: "POST",
        headers: {
          "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]")
            .value,
        },
        body: datos,
      });
      const resultado = await respuesta.json();
      if (!respuesta.ok || !resultado.success)
        throw new Error(
          resultado.message || "No fue posible guardar la configuración.",
        );
      await Swal.fire({
        icon: "success",
        title: "Configuración guardada",
        text: resultado.message,
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });
      window.location.reload();
    } catch (error) {
      Swal.fire({
        icon: "error",
        title: "No se pudo guardar",
        text: error.message || "Inténtalo nuevamente.",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });
    } finally {
      botonGuardar.disabled = false;
    }
  });
});
