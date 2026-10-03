/*==================== SHOW NAVBAR ====================*/
const showMenu = (headerToggle, navbarId) => {
  const toggleBtn = document.getElementById(headerToggle),
    nav = document.getElementById(navbarId);

  // Validate that variables exist
  if (headerToggle && navbarId) {
    toggleBtn.addEventListener("click", () => {
      // We add the show-menu class to the div tag with the nav__menu class
      nav.classList.toggle("show-menu");
      // change icon
      toggleBtn.classList.toggle("bx-x");
    });
  }
};
showMenu("header-toggle", "navbar");

const closeMenuBtn = document.getElementById("navbar-close");
if (closeMenuBtn) {
  closeMenuBtn.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    document.getElementById("navbar").classList.remove("show-menu");
    document.getElementById("header-toggle").classList.remove("bx-x");
  });
}

/*==================== LINK ACTIVE ====================*/
const linkColor = document.querySelectorAll(".nav__link");

function colorLink() {
  linkColor.forEach((l) => l.classList.remove("active"));
  this.classList.add("active");
}

linkColor.forEach((l) => l.addEventListener("click", colorLink));

//---------------------------------

// Obtener los elementos
const profileImg = document.getElementById("profile-img");
const modal = document.getElementById("modal");
const notificationsToggle = document.getElementById("notifications-toggle");
const notificationsPanel = document.getElementById("notifications-panel");

const notificacionesHabilitadas =
  document.body?.dataset.notificacionesHabilitadas === "true";

if (notificationsToggle && notificationsPanel && notificacionesHabilitadas) {
  notificationsToggle.addEventListener("click", (event) => {
    event.stopPropagation();
    notificationsPanel.classList.toggle("show");
  });
  const confirmarEntrega = (notification) => {
    Swal.fire({
      title: "¿Confirmar entrega de efectivo?",
      html: `Confirmar la entrega de <strong>L. ${notification.dataset.monto}</strong>.`,
      icon: "question",
      showCancelButton: true,
      confirmButtonText: "Sí, confirmar",
      cancelButtonText: "Cancelar",
      reverseButtons: true,
      customClass: { confirmButton: "classbotones" },
    }).then((result) => {
      if (!result.isConfirmed) return;
      fetch(notification.dataset.url, {
        method: "POST",
        headers: { "X-CSRFToken": getCookie("csrftoken") },
      })
        .then((response) => response.json())
        .then((data) => {
          if (!data.ok) throw new Error(data.mensaje);
          return Swal.fire({
            title: "¡Entrega confirmada!",
            text: data.mensaje || "El retiro fue confirmado correctamente.",
            icon: "success",
            confirmButtonText: "Aceptar",
            customClass: { confirmButton: "classbotones" },
          });
        })
        .catch((error) =>
          Swal.fire({
            title: "No se pudo confirmar",
            text: error.message,
            icon: "error",
            confirmButtonText: "Aceptar",
            customClass: { confirmButton: "classbotones" },
          }),
        );
    });
  };

  const actualizarContadorNotificaciones = (pendientes) => {
    let badge = notificationsToggle.querySelector(".notifications-badge");
    if (pendientes > 0) {
      if (!badge) {
        badge = document.createElement("span");
        badge.className = "notifications-badge";
        notificationsToggle.appendChild(badge);
      }
      badge.textContent = pendientes;
    } else {
      badge?.remove();
    }
  };

  const retirarNotificacion = (notification, pendientes) => {
    const restantes = [...notificationsPanel.querySelectorAll(".notification-item")]
      .filter((item) => item !== notification);
    const posiciones = new Map(restantes.map((item) => [item, item.getBoundingClientRect().top]));
    notification.style.maxHeight = `${notification.offsetHeight}px`;
    requestAnimationFrame(() => notification.classList.add("notification-item--leaving"));

    window.setTimeout(() => {
      notification.remove();
      restantes.forEach((item) => {
        const desplazamiento = posiciones.get(item) - item.getBoundingClientRect().top;
        if (!desplazamiento) return;
        item.style.transition = "none";
        item.style.transform = `translateY(${desplazamiento}px)`;
        requestAnimationFrame(() => {
          item.style.transition = "";
          item.style.transform = "";
        });
      });
      if (!notificationsPanel.querySelector(".notification-item")) {
        const vacio = document.createElement("p");
        vacio.className = "notifications-empty";
        vacio.textContent = "No tienes notificaciones.";
        notificationsPanel.querySelector(".notifications-panel__list").appendChild(vacio);
      }
      actualizarContadorNotificaciones(pendientes);
    }, 460);
  };

  const marcarNotificacionLeida = (notification) => {
    if (notification.dataset.processing === "true") return;
    notification.dataset.processing = "true";
    notification.setAttribute("aria-busy", "true");
    fetch(notification.dataset.readUrl, {
      method: "POST",
      headers: { "X-CSRFToken": getCookie("csrftoken") },
      skipManagerLoader: true,
    })
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.mensaje || "No fue posible actualizar la notificación.");
        return data;
      })
      .then((data) => {
        if (!data.ok) throw new Error(data.mensaje || "No fue posible actualizar la notificación.");
        retirarNotificacion(notification, data.pendientes);
      })
      .catch((error) => {
        notification.dataset.processing = "false";
        notification.removeAttribute("aria-busy");
        Swal.fire({
          title: "No se pudo actualizar",
          text: error.message || "Inténtalo nuevamente.",
          icon: "error",
          confirmButtonText: "Aceptar",
          customClass: { confirmButton: "classbotones" },
        });
      });
  };

  const manejarAccionNotificacion = (notification) => {
    if (!notification || !notificationsPanel.contains(notification)) return;
    if (notification.classList.contains("notification-item--action")) {
      confirmarEntrega(notification);
    } else if (notification.dataset.readUrl) {
      marcarNotificacionLeida(notification);
    }
  };

  notificationsPanel.addEventListener("click", (event) => {
    manejarAccionNotificacion(event.target.closest(".notification-item"));
  });
  notificationsPanel.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    const notification = event.target.closest(".notification-item");
    if (notification) event.preventDefault();
    manejarAccionNotificacion(notification);
  });

  const iconosNotificacion = {
    RETIRO_CAJA: "bx-money-withdraw",
    STOCK_BAJO: "bx-error-circle",
    VENCIMIENTO: "bx-calendar-exclamation",
    CUENTA_COBRAR: "bx-wallet",
    CUENTA_PAGAR: "bx-credit-card",
  };

  const crearNotificacion = (notificacion) => {
    const item = document.createElement("div");
    item.className = "notification-item";
    item.dataset.notificationId = notificacion.id;

    if (notificacion.accion) {
      item.classList.add("notification-item--action");
      item.dataset.url = notificacion.url;
      item.dataset.monto = notificacion.monto;
      item.tabIndex = 0;
      item.setAttribute("role", "button");
    } else if (notificacion.read_url) {
      item.classList.add("notification-item--read");
      item.dataset.readUrl = notificacion.read_url;
      item.tabIndex = 0;
      item.setAttribute("role", "button");
    }

    const icono = document.createElement("span");
    icono.className = "notification-item__icon";
    const iconoInterno = document.createElement("i");
    iconoInterno.className = `bx ${iconosNotificacion[notificacion.tipo] || "bx-bell"}`;
    icono.appendChild(iconoInterno);

    const contenido = document.createElement("div");
    contenido.className = "notification-item__content";
    const titulo = document.createElement("strong");
    titulo.textContent = notificacion.titulo;
    const mensaje = document.createElement("p");
    mensaje.textContent = notificacion.mensaje;
    contenido.append(titulo, mensaje);

    if (notificacion.accion) {
      const estado = document.createElement("span");
      estado.className = "notification-item__state";
      estado.textContent = "Pendiente de entrega";
      contenido.appendChild(estado);
    }
    item.append(icono, contenido);
    return item;
  };

  const aplicarEstadoNotificaciones = (data) => {
    if (!data?.ok) return;
    const vigentes = new Set(data.ids.map(String));
    const removidas = [
      ...notificationsPanel.querySelectorAll(
        ".notification-item[data-notification-id]",
      ),
    ].filter((item) => !vigentes.has(item.dataset.notificationId));

    removidas.forEach((item) => retirarNotificacion(item, data.pendientes));
    const mostradas = new Set(
      [...notificationsPanel.querySelectorAll(".notification-item[data-notification-id]")]
        .map((item) => item.dataset.notificationId),
    );
    const vacio = notificationsPanel.querySelector(".notifications-empty");
    data.notificaciones.slice().reverse().forEach((notificacion) => {
      if (mostradas.has(String(notificacion.id))) return;
      vacio?.remove();
      const listado = notificationsPanel.querySelector(".notifications-panel__list");
      listado.insertBefore(
        crearNotificacion(notificacion),
        listado.firstChild,
      );
    });
    if (!removidas.length) actualizarContadorNotificaciones(data.pendientes);
  };

  let socketNotificaciones;
  let reintentoSocket = 0;
  let temporizadorReconexion;

  const conectarNotificaciones = () => {
    if (socketNotificaciones?.readyState === WebSocket.OPEN) return;
    const protocolo = window.location.protocol === "https:" ? "wss" : "ws";
    socketNotificaciones = new WebSocket(
      `${protocolo}://${window.location.host}/ws/notificaciones/`,
    );

    socketNotificaciones.addEventListener("open", () => {
      reintentoSocket = 0;
    });
    socketNotificaciones.addEventListener("message", (event) => {
      try {
        const mensaje = JSON.parse(event.data);
        if (mensaje.tipo === "estado_notificaciones") {
          aplicarEstadoNotificaciones(mensaje.estado);
        }
      } catch (_) {
        // Un mensaje inválido no debe afectar la navegación del usuario.
      }
    });
    socketNotificaciones.addEventListener("close", (event) => {
      // 4401 es el cierre intencional del servidor para usuarios sin sesión.
      // No se reintenta: evita conexiones repetidas en páginas públicas o al
      // finalizar una sesión.
      if (event.code === 4401 || event.code === 4403) return;
      const espera = Math.min(1000 * 2 ** reintentoSocket, 15000);
      reintentoSocket += 1;
      window.clearTimeout(temporizadorReconexion);
      temporizadorReconexion = window.setTimeout(conectarNotificaciones, espera);
    });
  };

  conectarNotificaciones();
}

/* ──────────────────────────────────────────────────────────
     Helpers
  ────────────────────────────────────────────────────────── */
const showModal = () => {
  modal.style.display = "block"; // primero mostrar
  requestAnimationFrame(() => {
    // luego animar con suavidad
    modal.style.opacity = "1";
    modal.style.transform = "translateX(-50%) translateY(0)";
  });
};

const hideModal = () => {
  modal.style.opacity = "0";
  modal.style.transform = "translateX(-50%) translateY(20px)";
  // Espera a que termine la transición para ocultar totalmente
  modal.addEventListener(
    "transitionend",
    () => {
      modal.style.display = "none";
    },
    { once: true },
  );
};

/* ──────────────────────────────────────────────────────────
     Toggle al clicar el círculo de iniciales
  ────────────────────────────────────────────────────────── */
profileImg.addEventListener("click", (e) => {
  e.stopPropagation(); // evita que se propague al doc
  modal.style.display === "block" ? hideModal() : showModal();
});

/* ──────────────────────────────────────────────────────────
     Cerrar si se hace clic fuera del modal
  ────────────────────────────────────────────────────────── */
document.addEventListener("click", (e) => {
  // Si el modal está abierto y el clic NO fue dentro de él
  if (modal.style.display === "block" && !modal.contains(e.target)) {
    hideModal();
  }
});

/* ──────────────────────────────────────────────────────────
     Cerrar sesion
  ────────────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", function () {
  const btn = document.getElementById("btn-logout");

  if (btn) {
    btn.addEventListener("click", function (e) {
      e.preventDefault();

      Swal.fire({
        title: "¿Cerrar sesión?",
        text: "Tu sesión se cerrará y tendrás que iniciar sesión nuevamente.",
        icon: "warning",
        showCancelButton: true,
        confirmButtonText: "Sí, cerrar sesión",
        cancelButtonText: "Cancelar",
        confirmButtonColor: "#d33", // rojo
        cancelButtonColor: "#6c757d", // gris
      }).then((result) => {
        if (result.isConfirmed) {
          fetch("/accounts/logout/", {
            method: "POST",
            headers: {
              "X-CSRFToken": getCookie("csrftoken"),
            },
          })
            .then(() => {
              window.location.href = "/accounts/login/";
            })
            .catch((error) => {
              console.error("Error logout:", error);
              window.location.href = "/accounts/login/";
            });
        }
      });
    });
  }
});

// Descarga el inventario sin dejar la interfaz sin respuesta mientras Excel se genera.
document.addEventListener("DOMContentLoaded", () => {
  const boton = document.getElementById("exportarInventarioExcel");
  if (!boton) return;

  boton.addEventListener("click", async (event) => {
    event.preventDefault();
    if (boton.dataset.loading === "true") return;

    const icono = boton.querySelector("i");
    const clasesOriginales = icono.className;
    boton.dataset.loading = "true";
    boton.setAttribute("aria-busy", "true");
    boton.setAttribute("aria-label", "Generando archivo de Excel");
    icono.className = "bx bx-loader-alt bx-spin";

    try {
      const respuesta = await fetch(boton.href);
      if (!respuesta.ok) throw new Error("No se pudo generar el archivo");

      const archivo = await respuesta.blob();
      const enlace = document.createElement("a");
      enlace.href = URL.createObjectURL(archivo);
      enlace.download = "inventario.xlsx";
      document.body.appendChild(enlace);
      enlace.click();
      enlace.remove();
      URL.revokeObjectURL(enlace.href);
    } catch (error) {
      if (window.Swal) {
        Swal.fire("Error", "No se pudo exportar el inventario", "error");
      } else {
        window.alert("No se pudo exportar el inventario");
      }
    } finally {
      boton.dataset.loading = "false";
      boton.removeAttribute("aria-busy");
      boton.setAttribute("aria-label", "Exportar inventario a Excel");
      icono.className = clasesOriginales;
    }
  });
});

// CSRF helper
function getCookie(name) {
  let cookieValue = null;

  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");

    for (let cookie of cookies) {
      cookie = cookie.trim();

      if (cookie.startsWith(name + "=")) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }

  return cookieValue;
}
