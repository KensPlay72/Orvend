function validarSoloNumeros(input) {
  input.value = input.value.replace(/\D/g, "");
}

function convertImageToWebP(file, quality = 0.85) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onload = function (event) {
      const img = new Image();

      img.onload = function () {
        const canvas = document.createElement("canvas");
        canvas.width = img.width;
        canvas.height = img.height;

        const ctx = canvas.getContext("2d");
        ctx.drawImage(img, 0, 0);

        canvas.toBlob(
          (blob) => {
            if (!blob) return reject(new Error("Error de conversión"));

            const webpFile = new File(
              [blob],
              file.name.replace(/\.[^/.]+$/, ".webp"),
              { type: "image/webp" },
            );

            resolve(webpFile);
          },
          "image/webp",
          quality,
        );
      };

      img.onerror = () => reject(new Error("Error al cargar la imagen"));
      img.src = event.target.result;
    };

    reader.onerror = () => reject(new Error("Error al leer el archivo"));
    reader.readAsDataURL(file);
  });
}

function mostrarAlerta({ icon = "warning", title = "", text = "" }) {
  return Swal.fire({
    icon,
    title,
    text,
    confirmButtonText: "Aceptar",
    customClass: { confirmButton: "classbotones" },
  });
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
  let bannerPrincipalArchivo = null;
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
      dots = document.getElementById("carruselDots"),
      anterior = document.getElementById("carruselPrev"),
      siguiente = document.getElementById("carruselNext");
    if (!vista || !dots || !anterior || !siguiente) return;
    const items = [...vista.querySelectorAll("figure")];
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
      bannerPrincipalArchivo = null;
      if (boton.dataset.bannerId) {
        bannersEliminar.add(Number(boton.dataset.bannerId));
      }
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
    const file = inputBanner.files[0];
    if (!file) return;
    const ext = file.name.split(".").pop().toLowerCase();
    if (!["jpg", "jpeg", "png", "webp"].includes(ext)) {
      inputBanner.value = "";
      mostrarAlerta({
        icon: "warning",
        title: "Formato inválido",
        text: "El banner debe ser JPG, PNG o WEBP.",
      });
      return;
    }
    if (!(await validarMedida(file))) {
      inputBanner.value = "";
      mostrarAlerta({
        icon: "warning",
        title: "Medida incorrecta",
        text: "El banner debe medir 1920 × 640 píxeles.",
      });
      return;
    }

    try {
      bannerPrincipalArchivo = await convertImageToWebP(file);
      const box = document.getElementById("bannerPreviewBox");
      box.innerHTML = '<img id="bannerPreview" alt="Vista previa del banner">';
      document.getElementById("bannerPreview").src = URL.createObjectURL(
        bannerPrincipalArchivo,
      );
    } catch (e) {
      inputBanner.value = "";
      mostrarAlerta({
        icon: "error",
        title: "Error",
        text: "No se pudo procesar la imagen del banner.",
      });
    }
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
    const archivos = Array.from(inputCarrusel.files || []);
    inputCarrusel.value = "";
    if (!archivos.length) return;

    for (const file of archivos) {
      const ext = file.name.split(".").pop().toLowerCase();
      if (!["jpg", "jpeg", "png", "webp"].includes(ext)) {
        mostrarAlerta({
          icon: "warning",
          title: "Formato inválido",
          text: "Cada imagen del carrusel debe ser JPG, PNG o WEBP.",
        });
        return;
      }
      if (!(await validarMedida(file))) {
        mostrarAlerta({
          icon: "warning",
          title: "Medida incorrecta",
          text: "Cada imagen debe medir 1920 × 640 píxeles.",
        });
        return;
      }
    }

    try {
      for (const file of archivos) {
        const webpFile = await convertImageToWebP(file);
        carruselArchivos.push(webpFile);
      }
      renderCarruselPendiente();
    } catch (e) {
      mostrarAlerta({
        icon: "error",
        title: "Error",
        text: "No se pudo procesar una de las imágenes del carrusel.",
      });
    }
  });
  activarCarrusel();

  inputLogo?.addEventListener("change", async () => {
    const archivo = inputLogo.files?.[0];
    if (!archivo) return;
    const ext = archivo.name.split(".").pop().toLowerCase();
    if (!["jpg", "jpeg", "png", "webp"].includes(ext)) {
      inputLogo.value = "";
      mostrarAlerta({
        icon: "warning",
        title: "Formato inválido",
        text: "Selecciona un logo JPG, PNG o WEBP.",
      });
      return;
    }
    try {
      logo = await convertImageToWebP(archivo);
      quitarLogo = false;
      logoPreview.src = URL.createObjectURL(logo);
    } catch (e) {
      inputLogo.value = "";
      mostrarAlerta({
        icon: "error",
        title: "Error",
        text: "No se pudo procesar la imagen del logo a WebP.",
      });
    }
  });

  document.getElementById("quitarLogo")?.addEventListener("click", () => {
    logo = null;
    quitarLogo = true;
    inputLogo.value = "";
    logoPreview.src = "/static/img/LH.webp";
  });

  const ocultarLoaderCompleto = () => {
    const loader = document.getElementById("managerGlobalLoader");
    if (loader) {
      loader.hidden = true;
      loader.setAttribute("hidden", "");
    }
    document.body.classList.remove("manager-loader-active");
    if (window.managerLoader) {
      window.managerLoader.ocultar();
      window.managerLoader.ocultar();
    }
  };

  if (!form || !botonGuardar) return;

  form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const nombre = document.getElementById("nombreComercial").value.trim();
    if (!nombre) {
      mostrarAlerta({
        icon: "warning",
        title: "Dato requerido",
        text: "Ingresa el nombre comercial del negocio.",
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
    if (bannerPrincipalArchivo) {
      datos.append("banner_principal", bannerPrincipalArchivo);
    } else if (inputBanner?.files[0]) {
      // Fallback si no fue procesado por el change
      const webpBanner = await convertImageToWebP(inputBanner.files[0]);
      datos.append("banner_principal", webpBanner);
    }
    carruselArchivos.forEach((banner) => datos.append("carrusel", banner));
    if (logo) datos.append("logo", logo);

    try {
      botonGuardar.disabled = true;
      window.managerLoader?.mostrar();
      const respuesta = await fetch(form.dataset.saveUrl || form.action, {
        method: "POST",
        headers: {
          "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]")
            .value,
        },
        body: datos,
        skipManagerLoader: true,
      });
      const resultado = await respuesta.json();
      ocultarLoaderCompleto();
      if (!respuesta.ok || !resultado.success)
        throw new Error(
          resultado.message || "No fue posible guardar la configuración.",
        );
      await Swal.fire({
        icon: "success",
        title: "Configuración guardada",
        text: resultado.message || "Configuración actualizada correctamente.",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
        allowOutsideClick: false,
      });
      window.location.reload();
    } catch (error) {
      ocultarLoaderCompleto();
      Swal.fire({
        icon: "error",
        title: "No se pudo guardar",
        text: error.message || "Inténtalo nuevamente.",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });
    } finally {
      ocultarLoaderCompleto();
      botonGuardar.disabled = false;
    }
  });
});
