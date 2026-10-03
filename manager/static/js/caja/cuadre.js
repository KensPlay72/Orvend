function validateNumber(input) {
  // Solo permite números enteros
  input.value = input.value.replace(/[^0-9]/g, "");

  calcularCuadre();
}

function calcularCuadre() {
  const filas = document.querySelectorAll(".cantidad-billete");

  let totalContado = 0;

  filas.forEach((input) => {
    const fila = input.closest("tr");

    // Primera columna:
    // "L. 1.00", "L. 2.00", etc.
    const textoDenominacion = fila.querySelector("td").textContent;

    const denominacion =
      parseFloat(textoDenominacion.replace(window.MONEDA_SISTEMA || "L.", "").trim()) || 0;

    const cantidad = parseInt(input.value, 10) || 0;

    const subtotal = denominacion * cantidad;

    const subtotalElemento = fila.querySelector(".subtotal");

    subtotalElemento.textContent = `L. ${subtotal.toFixed(2)}`;

    totalContado += subtotal;
  });

  // =========================
  // TOTAL CONTADO
  // =========================

  const totalContadoElemento = document.getElementById("totalContado");

  if (totalContadoElemento) {
    totalContadoElemento.textContent = `L. ${totalContado.toFixed(2)}`;
  }

  // =========================
  // TOTAL ESPERADO
  // =========================

  const totalEsperadoElemento = document.getElementById("totalEsperado");

  const totalEsperado = totalEsperadoElemento
    ? parseFloat(
        totalEsperadoElemento.textContent
          .replace(window.MONEDA_SISTEMA || "L.", "")
          .replace(/,/g, "")
          .trim(),
      ) || 0
    : 0;

  // =========================
  // DIFERENCIA
  // =========================

  const diferencia = totalContado - totalEsperado;

  const diferenciaElemento = document.getElementById("diferencia");

  if (diferenciaElemento) {
    diferenciaElemento.textContent = `L. ${diferencia.toFixed(2)}`;
  }
}

document.addEventListener("DOMContentLoaded", function () {
  const inputs = document.querySelectorAll(".cantidad-billete");
  const btnCerrar = document.getElementById("btnCerrarCuadre");

  const totalContadoElement = document.getElementById("totalContado");
  const diferenciaElement = document.getElementById("diferencia");
  const totalEsperadoElement = document.getElementById("totalEsperado");
  const otrosPagosCards = document.querySelectorAll("[data-payment-type]");

  const denominaciones = (document.querySelector(".cuadre-table")?.dataset.denominaciones || "")
    .split(",")
    .map(Number)
    .filter(Number.isFinite);

  function normalizarMonto(input) {
    let valor = input.value.replace(",", ".").replace(/[^0-9.]/g, "");
    const partes = valor.split(".");

    if (partes.length > 2) {
      valor = `${partes.shift()}.${partes.join("")}`;
    }

    if (valor.includes(".")) {
      const [entero, decimal] = valor.split(".");
      valor = `${entero}.${(decimal || "").slice(0, 2)}`;
    }

    input.value = valor;
  }

  function obtenerOtrosPagos() {
    return Array.from(otrosPagosCards).map(function (card) {
      const input = card.querySelector(".monto-otro-pago");
      const esperado = parseFloat(card.dataset.expected) || 0;
      const recibido = parseFloat(input.value) || 0;

      return {
        tipo: card.dataset.paymentType,
        esperado: esperado,
        recibido: recibido,
        input: input,
        diferencia: recibido - esperado,
      };
    });
  }

  function calcularOtrosPagos() {
    obtenerOtrosPagos().forEach(function (pago) {
      const diferencia = pago.input
        .closest(".payment-reconciliation__card")
        .querySelector(".payment-difference");

      if (diferencia) {
        diferencia.textContent = `L. ${pago.diferencia.toFixed(2)}`;
      }
    });
  }

  otrosPagosCards.forEach(function (card) {
    const input = card.querySelector(".monto-otro-pago");
    input.addEventListener("input", function () {
      normalizarMonto(input);
      calcularOtrosPagos();
    });
  });

  // =========================
  // VALIDAR CANTIDAD
  // =========================

  window.validateNumber = function (input) {
    input.value = input.value.replace(/[^0-9]/g, "");

    calcularCuadre();
  };

  // =========================
  // CALCULAR CUADRE
  // =========================

  function calcularCuadre() {
    let totalContado = 0;

    inputs.forEach(function (input, index) {
      const cantidad = parseInt(input.value) || 0;
      const denominacion = denominaciones[index];

      const subtotal = denominacion * cantidad;

      const fila = input.closest("tr");
      const subtotalElement = fila.querySelector(".subtotal");

      subtotalElement.textContent = `L. ${subtotal.toFixed(2)}`;

      totalContado += subtotal;
    });

    // Total contado

    totalContadoElement.textContent = `L. ${totalContado.toFixed(2)}`;

    // Total esperado

    const totalEsperado = parseFloat(totalEsperadoElement.dataset.total) || 0;

    // Diferencia

    const diferencia = totalContado - totalEsperado;

    diferenciaElement.textContent = `L. ${diferencia.toFixed(2)}`;
  }

  // =========================
  // CERRAR CAJA
  // =========================

  btnCerrar.addEventListener("click", function () {
    const totalContadoTexto = totalContadoElement.textContent
      .replace(window.MONEDA_SISTEMA || "L.", "")
      .trim();

    const totalContado = parseFloat(totalContadoTexto) || 0;

    const totalEsperado = parseFloat(totalEsperadoElement.dataset.total) || 0;

    const diferencia = totalContado - totalEsperado;

    const otrosPagos = obtenerOtrosPagos();
    const pagoSinRegistrar = otrosPagos.find(function (pago) {
      return pago.esperado > 0 && pago.input.value.trim() === "";
    });

    if (pagoSinRegistrar) {
      Swal.fire({
        title: "Falta completar el cuadre",
        text: `Ingrese el monto recibido por ${pagoSinRegistrar.tipo}.`,
        icon: "warning",
        confirmButtonText: "Entendido",
        customClass: { confirmButton: "classbotones" },
      });
      pagoSinRegistrar.input.focus();
      return;
    }

    const resumenPagos = [
      {
        etiqueta: "Efectivo",
        icono: "bx-money",
        esperado: totalEsperado,
        recibido: totalContado,
        diferencia: diferencia,
      },
      ...otrosPagos.map(function (pago) {
        return {
          etiqueta:
            {
              deposito: "Depósitos bancarios",
              tarjeta: "Tarjetas",
              cheque: "Cheques",
            }[pago.tipo] || pago.tipo,
          icono:
            {
              deposito: "bx-building-house",
              tarjeta: "bx-credit-card",
              cheque: "bx-receipt",
            }[pago.tipo] || "bx-wallet",
          esperado: pago.esperado,
          recibido: pago.recibido,
          diferencia: pago.diferencia,
        };
      }),
    ];

    const totalGeneralEsperado = resumenPagos.reduce(function (total, pago) {
      return total + pago.esperado;
    }, 0);

    const totalGeneralRecibido = resumenPagos.reduce(function (total, pago) {
      return total + pago.recibido;
    }, 0);

    const diferenciaGeneral = totalGeneralRecibido - totalGeneralEsperado;

    const resumenFilas = resumenPagos
      .map(function (pago) {
        return `
                <div class="cuadre-confirmacion__row">
                    <span class="cuadre-confirmacion__method">
                        <i class="bx ${pago.icono}"></i>${pago.etiqueta}
                    </span>
                    <span>L. ${pago.esperado.toFixed(2)}</span>
                    <span>L. ${pago.recibido.toFixed(2)}</span>
                    <strong>L. ${pago.diferencia.toFixed(2)}</strong>
                </div>
            `;
      })
      .join("");

    // =========================
    // CONFIRMACIÓN SWEETALERT
    // =========================

    Swal.fire({
      title: "¿Cerrar cuadre de caja?",
      html: `
                <div class="cuadre-confirmacion">
                    <p class="cuadre-confirmacion__intro">Revisa los montos registrados antes de finalizar el día.</p>
                    <div class="cuadre-confirmacion__table">
                        <div class="cuadre-confirmacion__header">
                            <span>Método</span>
                            <span>Esperado</span>
                            <span>Recibido</span>
                            <span>Diferencia</span>
                        </div>
                        ${resumenFilas}
                    </div>
                    <div class="cuadre-confirmacion__total">
                        <span>Total general</span>
                        <div>
                            <small>Esperado <strong>L. ${totalGeneralEsperado.toFixed(2)}</strong></small>
                            <small>Recibido <strong>L. ${totalGeneralRecibido.toFixed(2)}</strong></small>
                            <b>Diferencia: L. ${diferenciaGeneral.toFixed(2)}</b>
                        </div>
                    </div>
                    <p class="cuadre-confirmacion__warning"><i class="bx bx-info-circle"></i> Una vez cerrada la caja no podrás modificar este cuadre.</p>
                </div>
            `,
      icon: "warning",
      showCancelButton: true,
      confirmButtonText: "Sí, cerrar caja",
      cancelButtonText: "Cancelar",
      reverseButtons: true,
      customClass: {
        popup: "cuadre-confirmacion-popup",
        confirmButton: "classbotones",
      },
    }).then(function (result) {
      if (!result.isConfirmed) {
        return;
      }

      cerrarCaja();
    });
  });

  // =========================
  // ENVIAR CIERRE
  // =========================

  function cerrarCaja() {
    const formData = new FormData();

    inputs.forEach(function (input, index) {
      const cantidad = parseInt(input.value) || 0;
      const denominacion = denominaciones[index];

      formData.append(`cantidad_${denominacion.toFixed(2)}`, cantidad);
    });

    obtenerOtrosPagos().forEach(function (pago) {
      formData.append(`monto_${pago.tipo}`, pago.recibido.toFixed(2));
    });

    // =========================
    // CSRF
    // =========================

    const csrfToken = document.querySelector(
      '[name="csrfmiddlewaretoken"]',
    ).value;

    // =========================
    // LOADING
    // =========================

    Swal.fire({
      title: "Cerrando caja...",
      text: "Guardando el cuadre.",
      allowOutsideClick: false,
      allowEscapeKey: false,
      didOpen: () => {
        Swal.showLoading();
      },
    });

    btnCerrar.disabled = true;

    // =========================
    // REQUEST
    // =========================

    fetch("/manager/caja/cuadre/cerrar/", {
      method: "POST",

      headers: {
        "X-CSRFToken": csrfToken,
      },

      body: formData,
    })
      .then(function (response) {
        return response.json();
      })

      .then(function (data) {
        if (!data.ok) {
          throw new Error(data.mensaje || "No se pudo cerrar la caja.");
        }

        // =========================
        // ÉXITO
        // =========================

        const pagosCerrados = [
          {
            etiqueta: "Efectivo",
            icono: "bx-money",
            esperado: parseFloat(data.total_esperado) || 0,
            recibido: parseFloat(data.total_contado) || 0,
            diferencia: parseFloat(data.diferencia) || 0,
          },
          ...Object.entries(data.otros_pagos || {})
            .filter(function ([, pago]) {
              return parseFloat(pago.esperado) > 0;
            })
            .map(function ([tipo, pago]) {
              const esperado = parseFloat(pago.esperado) || 0;
              const recibido = parseFloat(pago.recibido) || 0;
              return {
                etiqueta:
                  {
                    deposito: "Depósitos bancarios",
                    tarjeta: "Tarjetas",
                    cheque: "Cheques",
                  }[tipo] || tipo,
                icono:
                  {
                    deposito: "bx-building-house",
                    tarjeta: "bx-credit-card",
                    cheque: "bx-receipt",
                  }[tipo] || "bx-wallet",
                esperado: esperado,
                recibido: recibido,
                diferencia: recibido - esperado,
              };
            }),
        ];

        const totalGeneralEsperado = pagosCerrados.reduce(function (
          total,
          pago,
        ) {
          return total + pago.esperado;
        }, 0);
        const totalGeneralRecibido = pagosCerrados.reduce(function (
          total,
          pago,
        ) {
          return total + pago.recibido;
        }, 0);
        const diferenciaGeneral = totalGeneralRecibido - totalGeneralEsperado;

        const filasCierre = pagosCerrados
          .map(function (pago) {
            return `
                    <div class="cuadre-confirmacion__row">
                        <span class="cuadre-confirmacion__method">
                            <i class="bx ${pago.icono}"></i>${pago.etiqueta}
                        </span>
                        <span>L. ${pago.esperado.toFixed(2)}</span>
                        <span>L. ${pago.recibido.toFixed(2)}</span>
                        <strong>L. ${pago.diferencia.toFixed(2)}</strong>
                    </div>
                `;
          })
          .join("");

        Swal.fire({
          title: "¡Caja cerrada!",
          html: `
                    <div class="cuadre-confirmacion cuadre-confirmacion--success">
                        <p class="cuadre-confirmacion__intro"><i class="bx bx-check-circle"></i> El cuadre se guardó correctamente.</p>
                        <div class="cuadre-confirmacion__table">
                            <div class="cuadre-confirmacion__header">
                                <span>Método</span>
                                <span>Esperado</span>
                                <span>Recibido</span>
                                <span>Diferencia</span>
                            </div>
                            ${filasCierre}
                        </div>
                        <div class="cuadre-confirmacion__total">
                            <span>Total general</span>
                            <div>
                                <small>Esperado <strong>L. ${totalGeneralEsperado.toFixed(2)}</strong></small>
                                <small>Recibido <strong>L. ${totalGeneralRecibido.toFixed(2)}</strong></small>
                                <b>Diferencia: L. ${diferenciaGeneral.toFixed(2)}</b>
                            </div>
                        </div>
                    </div>
                `,
          icon: "success",
          confirmButtonText: "Aceptar",
          customClass: {
            popup: "cuadre-confirmacion-popup",
            confirmButton: "classbotones",
          },
        }).then(function () {
          window.location.href = "/manager/caja/";
        });
      })

      .catch(function (error) {
        console.error(error);

        // =========================
        // ERROR
        // =========================

        Swal.fire({
          title: "No se pudo cerrar",
          text: error.message || "Ocurrió un error.",
          icon: "error",
          confirmButtonText: "Aceptar",
        });

        btnCerrar.disabled = false;
      });
  }

  // =========================
  // INICIALIZAR
  // =========================

  calcularCuadre();
  calcularOtrosPagos();
});
