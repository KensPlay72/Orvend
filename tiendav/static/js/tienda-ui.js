(function () {
  const inicio = performance.now();
  const duracionMinima = 400;
  let cargaFinalizada = false;

  function ejecutarCierre() {
    if (cargaFinalizada) return;
    cargaFinalizada = true;
    const transcurrido = performance.now() - inicio;
    const restante = Math.max(0, duracionMinima - transcurrido);
    window.setTimeout(() => {
      document.documentElement.classList.add("tienda-lista");
    }, restante);
  }

  function asegurarLogoYCargar() {
    if (cargaFinalizada) return;
    const logoImg = document.querySelector(".tienda-marca img");
    if (logoImg && !logoImg.complete && logoImg.src) {
      logoImg.addEventListener("load", ejecutarCierre, { once: true });
      logoImg.addEventListener("error", ejecutarCierre, { once: true });
      window.setTimeout(ejecutarCierre, 2500);
      return;
    }
    ejecutarCierre();
  }

  if (document.readyState === "complete") {
    asegurarLogoYCargar();
  } else {
    window.addEventListener("load", asegurarLogoYCargar, { once: true });
    window.addEventListener("DOMContentLoaded", asegurarLogoYCargar, { once: true });
  }

  // ----------------------------------------------------
  // Carrusel de banners promocionales
  // ----------------------------------------------------
  const carrusel = document.querySelector(".tienda-carrusel");
  if (carrusel) {
    const diapositivas = [...carrusel.querySelectorAll(".tienda-slide")];
    const puntos = [...carrusel.querySelectorAll("[data-slide-target]")];
    let indice = 0;
    let timerAutoplay = null;

    const mostrarSlide = (nuevoIndice) => {
      indice = (nuevoIndice + diapositivas.length) % diapositivas.length;
      diapositivas.forEach((slide, posicion) =>
        slide.classList.toggle("is-active", posicion === indice)
      );
      puntos.forEach((punto, posicion) =>
        punto.classList.toggle("is-active", posicion === indice)
      );
    };

    const iniciarAutoplay = () => {
      detenerAutoplay();
      if (diapositivas.length > 1) {
        timerAutoplay = window.setInterval(() => mostrarSlide(indice + 1), 3000);
      }
    };

    const detenerAutoplay = () => {
      if (timerAutoplay) {
        clearInterval(timerAutoplay);
        timerAutoplay = null;
      }
    };

    carrusel.querySelector(".tienda-carrusel__prev")?.addEventListener("click", () => {
      mostrarSlide(indice - 1);
      iniciarAutoplay();
    });
    carrusel.querySelector(".tienda-carrusel__next")?.addEventListener("click", () => {
      mostrarSlide(indice + 1);
      iniciarAutoplay();
    });
    puntos.forEach((punto) =>
      punto.addEventListener("click", () => {
        mostrarSlide(Number(punto.dataset.slideTarget));
        iniciarAutoplay();
      })
    );

    // Soporte táctil (swipe) para teléfonos y tablets
    let touchStartX = 0;
    let touchStartY = 0;
    carrusel.addEventListener(
      "touchstart",
      (e) => {
        if (!e.changedTouches || !e.changedTouches.length) return;
        touchStartX = e.changedTouches[0].screenX;
        touchStartY = e.changedTouches[0].screenY;
      },
      { passive: true }
    );

    carrusel.addEventListener(
      "touchend",
      (e) => {
        if (!e.changedTouches || !e.changedTouches.length) return;
        const touchEndX = e.changedTouches[0].screenX;
        const touchEndY = e.changedTouches[0].screenY;
        const diffX = touchStartX - touchEndX;
        const diffY = touchStartY - touchEndY;
        if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > 35) {
          if (diffX > 0) {
            mostrarSlide(indice + 1);
          } else {
            mostrarSlide(indice - 1);
          }
          iniciarAutoplay();
        }
      },
      { passive: true }
    );

    // Pausar en PC cuando el cursor está encima
    carrusel.addEventListener("mouseenter", detenerAutoplay);
    carrusel.addEventListener("mouseleave", iniciarAutoplay);

    iniciarAutoplay();
  }

  // ----------------------------------------------------
  // Navegación en carruseles de productos por categoría
  // ----------------------------------------------------
  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-carousel-nav]");
    if (!btn) return;
    const direccion = btn.dataset.carouselNav;
    const selector = btn.dataset.target;
    const track = document.querySelector(selector);
    if (!track) return;
    const desplazamiento = Math.max(260, Math.round(track.clientWidth * 0.75));
    track.scrollBy({
      left: direccion === "next" ? desplazamiento : -desplazamiento,
      behavior: "smooth",
    });
  });

  // ----------------------------------------------------
  // Cargar más categorías en inicio (lotes de 10)
  // ----------------------------------------------------
  const btnCargarCategorias = document.getElementById("btn-cargar-mas-categorias");
  const wrapCargarCategorias = document.getElementById("wrap-cargar-categorias");
  if (btnCargarCategorias) {
    btnCargarCategorias.addEventListener("click", async () => {
      if (!wrapCargarCategorias || btnCargarCategorias.disabled) return;

      const texto = btnCargarCategorias.querySelector("span");
      const estado = wrapCargarCategorias.querySelector("[data-categorias-status]");
      const textoOriginal = "Cargar más categorías";
      const parametros = new URLSearchParams({
        cargar_categorias: "1",
        desde: wrapCargarCategorias.dataset.nextOffset || "0",
      });

      btnCargarCategorias.disabled = true;
      wrapCargarCategorias.setAttribute("aria-busy", "true");
      if (texto) texto.textContent = "Cargando categorías...";
      if (estado) estado.textContent = "Cargando más categorías.";

      try {
        const respuesta = await fetch(
          `${wrapCargarCategorias.dataset.categoriasUrl}?${parametros}`,
          { headers: { Accept: "application/json" } }
        );
        if (!respuesta.ok) {
          throw new Error(`La solicitud de categorías falló (${respuesta.status}).`);
        }

        const resultado = await respuesta.json();
        const contenido = document.createElement("template");
        contenido.innerHTML = resultado.html;
        const nuevasCategorias = contenido.content.querySelectorAll(
          ".tienda-seccion-categoria"
        );
        if (resultado.has_more && nuevasCategorias.length === 0) {
          throw new Error("La respuesta no incluyó las categorías esperadas.");
        }

        document
          .getElementById("categorias")
          .insertBefore(contenido.content, wrapCargarCategorias);
        wrapCargarCategorias.dataset.nextOffset = String(resultado.next_offset);
        if (estado) {
          estado.textContent = `${nuevasCategorias.length} categorías cargadas.`;
        }
        if (!resultado.has_more) {
          wrapCargarCategorias.remove();
        } else {
          btnCargarCategorias.disabled = false;
          if (texto) texto.textContent = textoOriginal;
        }
      } catch (error) {
        console.error("No se pudieron cargar más categorías.", error);
        btnCargarCategorias.disabled = false;
        if (texto) texto.textContent = "No se pudo cargar. Reintentar";
        if (estado) estado.textContent = "No se pudieron cargar las categorías. Inténtalo de nuevo.";
      } finally {
        wrapCargarCategorias.removeAttribute("aria-busy");
      }
    });
  }

  // ----------------------------------------------------
  // Galería de imágenes de producto (Múltiples imágenes)
  // ----------------------------------------------------
  const galeria = document.querySelector(".tienda-galeria");
  if (galeria) {
    const imagenes = [...galeria.querySelectorAll("[data-producto-slide]")];
    const puntos = [...galeria.querySelectorAll("[data-producto-slide-target]")];
    const miniaturas = [...document.querySelectorAll("[data-producto-thumb]")];
    const contadorSlide = document.querySelector("[data-current-slide]");
    let indice = 0;

    const mostrarImagen = (nuevoIndice) => {
      if (imagenes.length === 0) return;
      indice = (nuevoIndice + imagenes.length) % imagenes.length;

      // Actualizar slide activo
      imagenes.forEach((imagen, posicion) =>
        imagen.classList.toggle("is-active", posicion === indice)
      );

      // Actualizar puntos de paginación
      puntos.forEach((punto, posicion) =>
        punto.classList.toggle("is-active", posicion === indice)
      );

      // Actualizar miniaturas
      miniaturas.forEach((thumb, posicion) => {
        const esActivo = posicion === indice;
        thumb.classList.toggle("is-active", esActivo);
        if (esActivo) {
          thumb.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
        }
      });

      // Actualizar contador numérico
      if (contadorSlide) {
        contadorSlide.textContent = String(indice + 1);
      }
    };

    galeria.querySelector(".tienda-galeria__prev")?.addEventListener("click", (e) => {
      e.stopPropagation();
      mostrarImagen(indice - 1);
    });

    galeria.querySelector(".tienda-galeria__next")?.addEventListener("click", (e) => {
      e.stopPropagation();
      mostrarImagen(indice + 1);
    });

    puntos.forEach((punto) =>
      punto.addEventListener("click", (e) => {
        e.stopPropagation();
        mostrarImagen(Number(punto.dataset.productoSlideTarget));
      })
    );

    miniaturas.forEach((thumb) =>
      thumb.addEventListener("click", () =>
        mostrarImagen(Number(thumb.dataset.productoThumb))
      )
    );

    // Navegación por teclado cuando la galería tiene foco
    galeria.addEventListener("keydown", (e) => {
      if (e.key === "ArrowLeft") mostrarImagen(indice - 1);
      if (e.key === "ArrowRight") mostrarImagen(indice + 1);
    });

    // Soporte táctil / swipe en móviles
    let touchStartX = 0;
    let touchStartY = 0;
    galeria.addEventListener(
      "touchstart",
      (e) => {
        if (e.changedTouches.length === 1) {
          touchStartX = e.changedTouches[0].screenX;
          touchStartY = e.changedTouches[0].screenY;
        }
      },
      { passive: true }
    );

    galeria.addEventListener(
      "touchend",
      (e) => {
        if (e.changedTouches.length === 1) {
          const deltaX = e.changedTouches[0].screenX - touchStartX;
          const deltaY = e.changedTouches[0].screenY - touchStartY;
          // Solo si el gesto es principalmente horizontal y superior a 40px
          if (Math.abs(deltaX) > 40 && Math.abs(deltaX) > Math.abs(deltaY) * 1.5) {
            if (deltaX < 0) {
              mostrarImagen(indice + 1);
            } else {
              mostrarImagen(indice - 1);
            }
          }
        }
      },
      { passive: true }
    );
  }

  // ----------------------------------------------------
  // Toggle visibilidad de contraseñas
  // ----------------------------------------------------
  document.querySelectorAll("[data-toggle-password]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const input = btn.closest(".tienda-input-group")?.querySelector("input");
      if (!input) return;
      const icono = btn.querySelector("i");
      if (input.type === "password") {
        input.type = "text";
        if (icono) {
          icono.classList.remove("bx-show");
          icono.classList.add("bx-hide");
        }
        btn.setAttribute("aria-label", "Ocultar contraseña");
      } else {
        input.type = "password";
        if (icono) {
          icono.classList.remove("bx-hide");
          icono.classList.add("bx-show");
        }
        btn.setAttribute("aria-label", "Mostrar contraseña");
      }
    });
  });

  // ----------------------------------------------------
  // Notificaciones Toast / Avisos
  // ----------------------------------------------------
  function aviso(tipo, titulo, mensaje, duracion = 4200) {
    const contenedor = document.getElementById("tiendaAvisos");
    if (!contenedor) return null;
    const iconos = {
      success: "bx-check-circle",
      error: "bx-error-circle",
      loading: "bx-loader-alt bx-spin",
    };
    const elemento = document.createElement("article");
    elemento.className = `tienda-aviso tienda-aviso--${tipo}`;
    elemento.innerHTML = `
      <div class="tienda-aviso__icono"><i class="bx ${iconos[tipo] || iconos.loading}"></i></div>
      <div class="tienda-aviso__cuerpo"><strong></strong><p></p></div>
      <button type="button" class="tienda-aviso__cerrar" aria-label="Cerrar aviso"><i class="bx bx-x"></i></button>
    `;
    elemento.querySelector("strong").textContent = titulo;
    elemento.querySelector("p").textContent = mensaje;
    elemento.querySelector(".tienda-aviso__cerrar").addEventListener("click", () => elemento.remove());
    contenedor.prepend(elemento);
    if (duracion) window.setTimeout(() => elemento.remove(), duracion);
    return elemento;
  }

  window.TiendaUI = {
    exito: (titulo = "Listo", mensaje = "Operación realizada correctamente.") => aviso("success", titulo, mensaje),
    error: (titulo = "Ocurrió un problema", mensaje = "Inténtalo nuevamente.") => aviso("error", titulo, mensaje, 6000),
    cargando: (titulo = "Procesando", mensaje = "Espera un momento...") => aviso("loading", titulo, mensaje, 0),
    cerrar: (elemento) => elemento?.remove(),
  };

  // ----------------------------------------------------
  // Carrito de compras y Checkout
  // ----------------------------------------------------
  const carritoDialogo = document.getElementById("tiendaCarrito");
  const contenidoCarrito = carritoDialogo?.querySelector("[data-cart-items]");
  const contadorCarrito = document.querySelectorAll("[data-cart-count]");
  const STORAGE_KEY = "orvend:tienda:carrito:v1";
  const simboloMoneda = window.MONEDA_SISTEMA || "L.";
  let carrito = [];

  const formatoMoneda = (valor) => `${simboloMoneda} ${Number(valor).toFixed(2)}`;

  const guardarCarrito = () => {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(carrito));
      return true;
    } catch (error) {
      window.TiendaUI.error(
        "No se pudo guardar el carrito",
        "Revisa el espacio disponible del navegador e inténtalo de nuevo."
      );
      return false;
    }
  };

  const crearBotonCantidad = (accion, etiqueta, texto) => {
    const boton = document.createElement("button");
    boton.type = "button";
    boton.dataset.cartAction = accion;
    boton.setAttribute("aria-label", etiqueta);
    boton.textContent = texto;
    return boton;
  };

  const renderizarCarrito = () => {
    if (!contenidoCarrito || !carritoDialogo) return;
    contenidoCarrito.replaceChildren();
    const totalUnidades = carrito.reduce((total, item) => total + item.quantity, 0);
    const total = carrito.reduce((suma, item) => suma + item.price * item.quantity, 0);
    const etiquetaCantidad = `${totalUnidades} ${totalUnidades === 1 ? "producto" : "productos"}`;

    document.querySelectorAll("[data-cart-count]").forEach((badge) => {
      badge.textContent = totalUnidades > 99 ? "99+" : String(totalUnidades);
      badge.setAttribute("aria-label", etiquetaCantidad);
      if (totalUnidades > 0) {
        badge.removeAttribute("hidden");
        badge.style.display = "grid";
      } else {
        badge.setAttribute("hidden", "");
        badge.style.display = "none";
      }
    });

    document.querySelectorAll("[data-cart-open]").forEach((btn) => {
      btn.setAttribute("aria-label", `Abrir carrito, ${etiquetaCantidad}`);
    });

    carrito.forEach((item) => {
      const fila = document.createElement("article");
      fila.className = "tienda-carrito__item";
      const imagen = document.createElement("img");
      imagen.src = item.image;
      imagen.alt = item.name;
      imagen.loading = "lazy";
      imagen.addEventListener("error", () => {
        imagen.src = "/static/img/default.webp";
        imagen.classList.add("tienda-carrito__imagen-rota");
      }, { once: true });

      const detalle = document.createElement("div");
      detalle.className = "tienda-carrito__detalle";
      const nombre = document.createElement("span");
      nombre.className = "tienda-carrito__nombre";
      nombre.textContent = item.name;
      const precio = document.createElement("strong");
      precio.className = "tienda-carrito__precio";
      precio.textContent = formatoMoneda(item.price * item.quantity);
      detalle.append(nombre, precio);

      if (item.unavailableLocation) {
        fila.classList.add("tienda-carrito__item--no-disponible");
        const avisoDisponibilidad = document.createElement("small");
        avisoDisponibilidad.className = "tienda-carrito__disponibilidad";
        avisoDisponibilidad.textContent = item.availableQuantity === undefined
          ? `No disponible en ${item.unavailableLocation}.`
          : `No disponible en ${item.unavailableLocation}. Disponible: ${item.availableQuantity}.`;
        detalle.appendChild(avisoDisponibilidad);
      }

      const cantidad = document.createElement("div");
      cantidad.className = "tienda-carrito__cantidad";
      cantidad.append(
        crearBotonCantidad("decrease", `Quitar una unidad de ${item.name}`, "−")
      );
      const unidades = document.createElement("span");
      unidades.textContent = String(item.quantity);
      unidades.setAttribute("aria-label", "Cantidad");
      cantidad.append(unidades);
      cantidad.append(
        crearBotonCantidad("increase", `Agregar una unidad de ${item.name}`, "+")
      );

      const quitar = document.createElement("button");
      quitar.type = "button";
      quitar.dataset.cartAction = "remove";
      quitar.className = "tienda-carrito__quitar";
      quitar.setAttribute("aria-label", `Eliminar ${item.name} del carrito`);
      quitar.innerHTML = '<i class="bx bx-trash" aria-hidden="true"></i>';

      fila.dataset.productToken = item.token;
      fila.append(imagen, detalle, cantidad, quitar);
      contenidoCarrito.appendChild(fila);
    });

    const vacio = carritoDialogo.querySelector("[data-cart-empty]");
    const pie = carritoDialogo.querySelector("[data-cart-footer]");
    const totalElemento = carritoDialogo.querySelector("[data-cart-total]");

    if (vacio) {
      if (carrito.length > 0) {
        vacio.hidden = true;
        vacio.style.setProperty("display", "none", "important");
      } else {
        vacio.hidden = false;
        vacio.style.removeProperty("display");
      }
    }
    if (pie) {
      if (carrito.length === 0) {
        pie.hidden = true;
        pie.style.setProperty("display", "none", "important");
      } else {
        pie.hidden = false;
        pie.style.removeProperty("display");
      }
    }
    if (totalElemento) totalElemento.textContent = formatoMoneda(total);
    actualizarEstadoBotonesProductos();
  };

  const actualizarEstadoBotonesProductos = () => {
    const tokensEnCarrito = new Set(carrito.map((item) => item.token));

    // Botones de tarjetas en catálogo y carruseles
    document.querySelectorAll("[data-btn-card]").forEach((btn) => {
      const token = btn.dataset.productToken;
      const tieneStock = btn.dataset.stock === "1";
      if (!tieneStock) return;

      if (tokensEnCarrito.has(token)) {
        btn.classList.add("is-in-cart");
        btn.innerHTML = '<i class="bx bx-check-circle" aria-hidden="true"></i><span>En el carrito</span>';
        btn.setAttribute("aria-label", "Producto en el carrito. Haz clic para ver tu carrito");
        btn.setAttribute("title", "Ya está en tu carrito (haz clic para abrir)");
      } else {
        btn.classList.remove("is-in-cart");
        btn.innerHTML = '<i class="bx bx-shopping-bag" aria-hidden="true"></i><span>Comprar</span>';
        btn.setAttribute("aria-label", "Comprar");
        btn.removeAttribute("title");
      }
    });

    // Botón en detalle del producto
    document.querySelectorAll("[data-cart-add]").forEach((btn) => {
      const token = btn.dataset.productToken;
      const tieneStock = btn.dataset.stock !== "0" && !btn.disabled;
      if (!tieneStock) return;

      if (tokensEnCarrito.has(token)) {
        btn.classList.add("is-in-cart");
        btn.innerHTML = '<i class="bx bx-check-circle" aria-hidden="true"></i><span>En el carrito</span>';
        btn.setAttribute("aria-label", "Producto en el carrito. Haz clic para ver tu carrito");
        btn.setAttribute("title", "Ya está en tu carrito (haz clic para abrir)");
      } else {
        btn.classList.remove("is-in-cart");
        btn.innerHTML = '<i class="bx bx-shopping-bag" aria-hidden="true"></i><span>Comprar</span>';
        btn.setAttribute("aria-label", "Comprar");
        btn.removeAttribute("title");
      }
    });
  };

  try {
    const carritoGuardado = JSON.parse(window.localStorage.getItem(STORAGE_KEY) || "[]");
    if (Array.isArray(carritoGuardado)) {
      carrito = carritoGuardado.filter((item) =>
        item &&
        typeof item.token === "string" &&
        typeof item.name === "string" &&
        typeof item.image === "string" &&
        Number.isFinite(Number(item.price)) &&
        Number(item.price) >= 0 &&
        Number.isInteger(Number(item.quantity)) &&
        Number(item.quantity) > 0
      ).map((item) => ({
        token: item.token,
        name: item.name,
        image: item.image,
        price: Number(item.price),
        quantity: Number(item.quantity),
      }));
    }
  } catch (error) {
    carrito = [];
  }
  renderizarCarrito();

  // Delegación de eventos para agregar al carrito
  document.addEventListener("click", (event) => {
    // Si se presiona un botón de tarjeta que ya está en el carrito, abrir el carrito
    const cardInCart = event.target.closest("[data-btn-card].is-in-cart");
    if (cardInCart) {
      event.preventDefault();
      event.stopPropagation();
      if (carritoDialogo && !carritoDialogo.open) {
        carritoDialogo.showModal();
      }
      return;
    }

    const boton = event.target.closest("[data-cart-add]");
    if (!boton || boton.disabled) return;

    // Si el botón de detalle ya está en el carrito, abrir el carrito
    if (boton.classList.contains("is-in-cart")) {
      event.preventDefault();
      if (carritoDialogo && !carritoDialogo.open) {
        carritoDialogo.showModal();
      }
      return;
    }

    const token = boton.dataset.productToken;
    const name = boton.dataset.productName;
    const price = Number(boton.dataset.productPrice);
    const image = boton.dataset.productImage;
    if (!token || !name || !image || !Number.isFinite(price) || price < 0) {
      window.TiendaUI.error("No se pudo agregar el producto", "Actualiza la página e inténtalo de nuevo.");
      return;
    }

    const itemExistente = carrito.find((item) => item.token === token);
    if (itemExistente) {
      itemExistente.name = name;
      itemExistente.price = price;
      itemExistente.image = image;
      itemExistente.quantity += 1;
      itemExistente.unavailableLocation = "";
      itemExistente.availableQuantity = undefined;
    } else {
      carrito.push({ token, name, price, image, quantity: 1 });
    }
    const guardado = guardarCarrito();
    renderizarCarrito();
    document.querySelectorAll("[data-cart-count]").forEach((badge) => {
      badge.classList.remove("tienda-badge-pop");
      void badge.offsetWidth;
      badge.classList.add("tienda-badge-pop");
    });
    if (!guardado) return;

    // Efecto visual de confirmación en el botón
    boton.classList.add("is-added");
    window.setTimeout(() => boton.classList.remove("is-added"), 600);

    window.TiendaUI.exito("¡Agregado al carrito!", name);
  });


  // Apertura y Cierre del carrito
  document.querySelectorAll("[data-cart-open]").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (carritoDialogo && !carritoDialogo.open) carritoDialogo.showModal();
    });
  });

  if (
    carritoDialogo?.dataset.authenticated === "true" &&
    new URLSearchParams(window.location.search).get("abrir_carrito") === "1"
  ) {
    carritoDialogo.showModal();
  }

  carritoDialogo?.querySelectorAll("[data-cart-close]").forEach((btn) => {
    btn.addEventListener("click", () => carritoDialogo.close());
  });

  document.addEventListener("click", (event) => {
    document.querySelectorAll(".tienda-cuenta-menu[open]").forEach((menu) => {
      if (!menu.contains(event.target)) menu.removeAttribute("open");
    });
  });

  carritoDialogo?.addEventListener("click", (event) => {
    if (event.target === carritoDialogo) carritoDialogo.close();
  });

  // Acciones en items del carrito
  contenidoCarrito?.addEventListener("click", (event) => {
    const boton = event.target.closest("[data-cart-action]");
    if (!boton) return;
    const fila = boton.closest("[data-product-token]");
    const item = carrito.find((producto) => producto.token === fila?.dataset.productToken);
    if (!item) return;

    if (boton.dataset.cartAction === "increase") item.quantity += 1;
    if (boton.dataset.cartAction === "decrease") item.quantity -= 1;
    item.unavailableLocation = "";
    item.availableQuantity = undefined;
    if (boton.dataset.cartAction === "remove" || item.quantity < 1) {
      carrito = carrito.filter((producto) => producto.token !== item.token);
    }
    guardarCarrito();
    renderizarCarrito();
  });

  carritoDialogo?.querySelector("[data-cart-location]")?.addEventListener("change", () => {
    carrito.forEach((item) => {
      item.unavailableLocation = "";
      item.availableQuantity = undefined;
    });
    renderizarCarrito();
  });

  const vistaCarrito = carritoDialogo?.querySelector('[data-cart-view="cart"]');
  const vistaConfirmacion = carritoDialogo?.querySelector('[data-cart-view="confirm"]');
  const confirmLocation = carritoDialogo?.querySelector("[data-confirm-location]");
  const confirmCount = carritoDialogo?.querySelector("[data-confirm-items-count]");
  const confirmTotal = carritoDialogo?.querySelector("[data-confirm-total]");
  const confirmList = carritoDialogo?.querySelector("[data-confirm-items-list]");

  const mostrarPasoCarrito = () => {
    if (vistaCarrito) {
      vistaCarrito.hidden = false;
      vistaCarrito.style.removeProperty("display");
    }
    if (vistaConfirmacion) {
      vistaConfirmacion.hidden = true;
      vistaConfirmacion.style.display = "none";
    }
  };

  const mostrarPasoConfirmacion = () => {
    if (carrito.length === 0) return;
    if (carritoDialogo.dataset.authenticated !== "true") {
      const acceso = new URL(carritoDialogo.dataset.authUrl, window.location.origin);
      acceso.searchParams.set("next", `${window.location.origin}/tienda/?abrir_carrito=1`);
      window.location.href = acceso.href;
      return;
    }

    const selectUbicacion = carritoDialogo.querySelector("[data-cart-location]");
    const ubicacion = selectUbicacion?.value;
    if (!ubicacion) {
      window.TiendaUI.error("Selecciona una tienda", "Elige la sucursal donde recogerás tu pedido.");
      return;
    }

    const nombreUbicacion = selectUbicacion?.options[selectUbicacion.selectedIndex]?.text || "Sucursal seleccionada";
    const total = carrito.reduce((suma, item) => suma + item.price * item.quantity, 0);
    const totalUnidades = carrito.reduce((sum, item) => sum + item.quantity, 0);

    if (confirmLocation) confirmLocation.textContent = nombreUbicacion;
    if (confirmCount) confirmCount.textContent = `${totalUnidades} producto${totalUnidades === 1 ? '' : 's'}`;
    if (confirmTotal) confirmTotal.textContent = formatoMoneda(total);

    if (confirmList) {
      confirmList.replaceChildren();
      carrito.forEach((item) => {
        const itemFila = document.createElement("div");
        itemFila.className = "tienda-confirmacion__item";

        const imgWrap = document.createElement("div");
        imgWrap.className = "tienda-confirmacion__item-img";
        const img = document.createElement("img");
        img.src = item.image;
        img.alt = item.name;
        img.loading = "lazy";
        img.addEventListener("error", () => {
          img.src = "/static/img/default.webp";
        }, { once: true });
        imgWrap.appendChild(img);

        const info = document.createElement("div");
        info.className = "tienda-confirmacion__item-info";
        info.innerHTML = `<strong>${item.name}</strong><small>${item.quantity} ud${item.quantity > 1 ? 's' : ''} × ${formatoMoneda(item.price)}</small>`;

        const subtotal = document.createElement("div");
        subtotal.className = "tienda-confirmacion__item-subtotal";
        subtotal.innerHTML = `<strong>${formatoMoneda(item.price * item.quantity)}</strong>`;

        itemFila.append(imgWrap, info, subtotal);
        confirmList.appendChild(itemFila);
      });
    }

    if (vistaCarrito) {
      vistaCarrito.hidden = true;
      vistaCarrito.style.display = "none";
    }
    if (vistaConfirmacion) {
      vistaConfirmacion.hidden = false;
      vistaConfirmacion.style.removeProperty("display");
    }
  };

  // Botón "Continuar a confirmación"
  carritoDialogo?.querySelector("[data-cart-go-confirm]")?.addEventListener("click", () => {
    mostrarPasoConfirmacion();
  });

  // Botón "Modificar carrito" (volver del paso 2 al paso 1)
  carritoDialogo?.querySelector("[data-cart-back-cart]")?.addEventListener("click", () => {
    mostrarPasoCarrito();
  });

  // Cada vez que se cierra el carrito, resetear al paso 1
  carritoDialogo?.addEventListener("close", () => {
    mostrarPasoCarrito();
  });

  // Confirmar pedido y enviar
  carritoDialogo?.querySelector("[data-cart-submit-order]")?.addEventListener("click", async (event) => {
    if (carrito.length === 0) return;
    const ubicacion = carritoDialogo.querySelector("[data-cart-location]")?.value;
    if (!ubicacion) {
      mostrarPasoCarrito();
      window.TiendaUI.error("Selecciona una tienda", "Elige la sucursal donde recogerás tu pedido.");
      return;
    }

    const boton = event.currentTarget;
    const textoOriginal = boton.innerHTML;
    boton.disabled = true;
    boton.innerHTML = '<i class="bx bx-loader-alt bx-spin" aria-hidden="true"></i> Reservando pedido…';

    try {
      const respuesta = await fetch(carritoDialogo.dataset.checkoutUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": carritoDialogo.querySelector('[name="csrfmiddlewaretoken"]')?.value || "",
          "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify({
          ubicacion,
          items: carrito.map((item) => ({ token: item.token, quantity: item.quantity })),
        }),
      });
      const resultado = await respuesta.json();
      if (respuesta.status === 401 && resultado.auth_required) {
        carritoDialogo.dataset.authenticated = "false";
        boton.disabled = false;
        boton.innerHTML = textoOriginal;
        const acceso = new URL(carritoDialogo.dataset.authUrl, window.location.origin);
        acceso.searchParams.set("next", `${window.location.origin}/tienda/?abrir_carrito=1`);
        window.location.href = acceso.href;
        return;
      }
      if (!respuesta.ok || !resultado.success) {
        mostrarPasoCarrito();
        if (Array.isArray(resultado.unavailable_items)) {
          const noDisponibles = new Map(
            resultado.unavailable_items.map((item) => [
              typeof item === "string" ? item : item.token,
              typeof item === "string" ? {} : item,
            ]),
          );
          carrito.forEach((item) => {
            const noDisponible = noDisponibles.get(item.token);
            item.unavailableLocation = noDisponible ? resultado.location || "la tienda seleccionada" : "";
            item.availableQuantity = noDisponible?.available;
          });
          renderizarCarrito();
        }
        window.TiendaUI.error("No se pudo reservar", resultado.message || "Actualiza la página e inténtalo nuevamente.");
        return;
      }
      carrito = [];
      guardarCarrito();
      renderizarCarrito();

      if (carritoDialogo && typeof carritoDialogo.close === "function") {
        carritoDialogo.close();
      }

      mostrarConfirmacionExitosa(resultado);
    } catch (error) {
      window.TiendaUI.error("No se pudo enviar el pedido", "Comprueba tu conexión a internet e inténtalo nuevamente.");
    } finally {
      if (boton.isConnected) {
        boton.disabled = false;
        boton.innerHTML = textoOriginal;
      }
    }
  });

  document.querySelectorAll("[data-auto-submit]").forEach((control) => {
    control.addEventListener("change", () => control.form?.requestSubmit());
  });

  function mostrarConfirmacionExitosa(datos) {
    const overlay = document.getElementById("tiendaConfirmacionExito");
    if (!overlay) {
      window.location.href = datos?.pedidos_url || datos?.redirect || "/tienda/mis-pedidos/";
      return;
    }

    const numSpan = document.getElementById("tiendaExitoNumeroPedido");
    const btnPedidos = document.getElementById("tiendaExitoBtnPedidos");
    const btnInicio = document.getElementById("tiendaExitoBtnInicio");

    if (numSpan) {
      numSpan.textContent = datos?.numero_pedido || "---";
    }

    if (btnPedidos && (datos?.pedidos_url || datos?.redirect)) {
      btnPedidos.href = datos.pedidos_url || datos.redirect;
    }

    if (btnInicio && datos?.inicio_url) {
      btnInicio.href = datos.inicio_url;
    }

    // Reiniciar animación si fuese necesario
    overlay.classList.remove("is-active");
    void overlay.offsetWidth;
    overlay.classList.add("is-active");
    overlay.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
  }

  document.getElementById("tiendaExitoBtnPedidos")?.addEventListener("click", () => {
    document.body.style.overflow = "";
  });
  document.getElementById("tiendaExitoBtnInicio")?.addEventListener("click", () => {
    document.body.style.overflow = "";
  });

  window.mostrarConfirmacionPedido = mostrarConfirmacionExitosa;
}());
