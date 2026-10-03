// ==========================================================
// CAJA - SECCIÓN 1
// PRODUCTOS, BÚSQUEDA, MODAL Y TABLA
// ==========================================================

// ----------------------------------------------------------
// VARIABLES GLOBALES
// ----------------------------------------------------------

function validarNumeroCaja(input) {
  let valor = input.value.replace(/[^0-9.]/g, "");
  const primerPunto = valor.indexOf(".");
  if (primerPunto !== -1) {
    valor =
      valor.slice(0, primerPunto + 1) +
      valor.slice(primerPunto + 1).replace(/\./g, "");
  }
  input.value = valor;
}

// El archivo se carga como módulo; se expone la validación para los campos
// que la invocan desde el atributo HTML `oninput`.
window.validarNumeroCaja = validarNumeroCaja;

function validarEnteroCaja(input) {
  input.value = input.value.replace(/\D/g, "");
}

let datos = [];

let productos_dato = [];

let pagos = [];

let tarjetas = [];

let fila_descuento = null;

let total_m = 0;

let notaCreditoSeleccionada = null;

let clienteBusquedaControlador = null;

let clienteSeleccionado = null;

let cotizacionPendienteCliente = false;

let controlador = null;

let codex = 0;

// El precio de venta configurado ya incluye ISV. Caja únicamente lo separa
// para mostrar y guardar subtotal/impuesto, sin volver a sumarlo al total.
function recalcularLineaConIsvIncluido(producto) {
  const precio = Number(producto.precio_venta) || 0;
  const cantidad = Number(producto.cantidad) || 0;
  const tasa = Number(producto.tipos_isv) || 0;
  const impuestoUnitario = precio * (tasa / 100);

  producto.isv_15 = tasa === 15 ? impuestoUnitario : 0;
  producto.isv_18 = tasa === 18 ? impuestoUnitario : 0;
  producto.isv15_acumulable = producto.isv_15 * cantidad;
  producto.isv18_acumulable = producto.isv_18 * cantidad;
  producto.subtotal = (precio - impuestoUnitario) * cantidad;
  producto.total_linea = precio * cantidad;
}

function totalLineaCaja(producto) {
  return Number(producto.total_linea ?? (
    (Number(producto.precio_venta) || 0) * (Number(producto.cantidad) || 0)
  ));
}

// ==========================================================
// BUSQUEDA POR CODIGO
// ==========================================================

const codigoBusqueda = document.getElementById("codigo_busqueda");

if (codigoBusqueda) {
  codigoBusqueda.addEventListener("input", function () {
    const valor = this.value.toUpperCase();
    const prefijo = valor.match(/^C(?:O(?:T-?)?)?/);
    const textoPrefijo = prefijo ? prefijo[0] : "";

    if (textoPrefijo === "COT-") {
      this.value =
        textoPrefijo + valor.slice(textoPrefijo.length).replace(/\D/g, "");
    } else if (
      textoPrefijo === "C" ||
      textoPrefijo === "CO" ||
      textoPrefijo === "COT"
    ) {
      this.value = textoPrefijo;
    } else {
      this.value = valor.replace(/\D/g, "");
    }
  });

  codigoBusqueda.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
      event.preventDefault();

      const codigo = codigoBusqueda.value.trim();

      if (codigo === "") {
        mensaje("Ingrese un código válido", "error", "");

        return;
      }

      productos(codigo);
    }
  });
}

// ==========================================================
// DETERMINAR SI EXISTE EL CODIGO
// ==========================================================

function productos(codigo) {
  if (codigo === "") {
    console.log("Codigo no valido");

    return;
  }

  const producto = datos.findIndex((p) => p.codigo === codigo);

  if (producto === -1) {
    sin_codigo(codigo);
  } else {
    con_codigo(producto);

    tabla_detalle_total();
  }
}

// ==========================================================
// AGREGAR PRODUCTO QUE YA EXISTE EN LA TABLA
// ==========================================================

function con_codigo(i) {
  if (!datos[i]) {
    return;
  }

  // ------------------------------------------------------
  // STOCK REAL
  // ------------------------------------------------------

  const stockReal = parseFloat(datos[i].stock) || 0;

  // ------------------------------------------------------
  // STOCK VENDIBLE
  //
  // Ejemplo:
  // 6.83 -> 6
  // 7.50 -> 7
  // 10.00 -> 10
  // ------------------------------------------------------

  const stockVendible = Math.floor(stockReal);

  // ------------------------------------------------------
  // VALIDAR STOCK
  // ------------------------------------------------------

  if (datos[i].cantidad + 1 > stockVendible) {
    mensaje(
      `No puede vender más de ${stockVendible} unidades. Existencia real: ${stockReal}`,
      "error",
      "",
    );

    return;
  }

  // ------------------------------------------------------
  // AUMENTAR CANTIDAD
  // ------------------------------------------------------

  datos[i].cantidad += 1;

  // ------------------------------------------------------
  // DESCUENTO
  // ------------------------------------------------------

  if (datos[i].estado === 1) {
    descuento_cantidad(i);
  }

  // ------------------------------------------------------
  // SUBTOTAL
  // ------------------------------------------------------

  recalcularLineaConIsvIncluido(datos[i]);

  // ------------------------------------------------------
  // ACTUALIZAR TABLA
  // ------------------------------------------------------

  const tabla = document.getElementById("tablaProductos");

  if (!tabla) {
    return;
  }

  const fila = tabla.rows[i + 1];

  if (!fila) {
    return;
  }

  const cantidad = fila.cells[2]?.querySelector(".pre");

  const subtotal = fila.cells[5];

  const descuento = fila.cells[4];

  // ------------------------------------------------------
  // CANTIDAD
  // ------------------------------------------------------

  if (cantidad) {
    cantidad.textContent = `${datos[i].cantidad} / ${datos[i].stock}`;
  }

  // ------------------------------------------------------
  // SUBTOTAL
  // ------------------------------------------------------

  if (subtotal) {
    subtotal.textContent = "L. " + totalLineaCaja(datos[i]).toFixed(2);
  }

  // ------------------------------------------------------
  // DESCUENTO
  // ------------------------------------------------------

  if (descuento) {
    descuento.textContent = "L. " + datos[i].descuento.toFixed(2);
  }

  // ------------------------------------------------------
  // ACTUALIZAR TOTALES
  // ------------------------------------------------------

  tabla_detalle_total();
}

// ==========================================================
// BUSQUEDA POR CODIGO EN SERVIDOR
// ==========================================================

async function sin_codigo(codigo) {
  try {
    const response = await fetch(
      `/manager/busquedacodigo/${encodeURIComponent(codigo)}/`,
      {
        method: "GET",
        headers: {},
      },
    );

    if (!response.ok) {
      const dato = await response.json();

      throw new Error(dato.error || dato.mensaje || "Error desconocido");
    }

    const data = await response.json();

    if (data.es_cotizacion) {
      cargarCotizacionEnCaja(data);
      return;
    }

    let imp15 = 0;
    let imp18 = 0;

    if (parseFloat(data.tipos_isv) === 15) {
      imp15 = parseFloat(data.isv) || 0;
    } else if (parseFloat(data.tipos_isv) === 18) {
      imp18 = parseFloat(data.isv) || 0;
    }

    const producto = {
      id: data.id,

      combo_id: data.combo_id || null,

      es_combo: Boolean(data.es_combo),

      codigo: data.codigo_sku,

      nombre: data.nombre,

      precio_venta: parseFloat(data.precio_venta) || 0,

      precio_venta_min: parseFloat(data.precio_venta_min) || 0,

      precio_venta_max: parseFloat(data.precio_venta_max) || 0,

      tipos_isv: parseFloat(data.tipos_isv) || 0,

      stock: parseFloat(data.stock) || 0,

      cantidad: 1,

      descuento: parseFloat(data.descuentos) || 0,

      subtotal: parseFloat(data.precio_venta) || 0,

      valor_descuento: parseFloat(data.descuentos) || 0,

      acumulable: data.acumulable,

      estado: 1,

      isv_15: imp15,

      isv_18: imp18,

      isv15_acumulable: imp15,

      isv18_acumulable: imp18,

      lleva: parseInt(data.lleva) || 0,

      paga: parseInt(data.paga) || 0,

      restarlleva: 0,
    };

    recalcularLineaConIsvIncluido(producto);
    datos.push(producto);

    tabla_codigo(
      data.codigo_sku,

      data.nombre,

      1,

      parseFloat(data.precio_venta).toFixed(2),

      parseFloat(data.descuentos).toFixed(2),

      parseFloat(data.precio_venta).toFixed(2),
    );

    tabla_detalle_total();
  } catch (error) {
    mensaje(error.message, "error", "");
  }
}

// ==========================================================
// PRODUCTO SELECCIONADO
// ==========================================================

function seleccionarProducto(index) {
  codex = index;

  const producto = productos_dato[index];

  if (!producto) {
    mensaje("No se encontró el producto seleccionado", "error", "");

    return;
  }

  const codigo = document.getElementById("nCodigo");

  const nombre = document.getElementById("nNombre");

  const precio = document.getElementById("nPrecio");

  const cantidad = document.getElementById("nCanitdad");

  const existencia = document.getElementById("existenciaProducto");

  // ======================================================
  // OBTENER EXISTENCIA REAL
  // ======================================================

  const stock = parseFloat(producto.stock);

  if (isNaN(stock)) {
    console.error("Stock inválido:", producto.stock, producto);

    mensaje("La existencia del producto no es válida", "error", "");

    return;
  }

  // ======================================================
  // SOLO SE PUEDEN VENDER UNIDADES ENTERAS
  //
  // Ejemplo:
  //
  // Stock = 6.83
  // Se pueden vender solamente 6
  //
  // Stock = 10.00
  // Se pueden vender 10
  // ======================================================

  const stockVendible = Math.floor(stock);

  // ======================================================
  // VERIFICAR SI EXISTE AL MENOS UNA UNIDAD
  // ======================================================

  if (stockVendible < 1) {
    mensaje(
      `No hay unidades completas disponibles. Existencia: ${stock}`,
      "error",
      "",
    );

    return;
  }

  // ======================================================
  // LLENAR MODAL
  // ======================================================

  if (codigo) {
    codigo.value = producto.codigo_sku;
  }

  if (nombre) {
    nombre.value = producto.nombre;
  }

  if (precio) {
    precio.value = `${window.MONEDA_SISTEMA || "L."} ${parseFloat(producto.precio_venta).toFixed(2)}`;
  }

  if (cantidad) {
    cantidad.value = 1;

    cantidad.min = 1;

    cantidad.max = stockVendible;
  }

  // ======================================================
  // MOSTRAR EXISTENCIA
  //
  // IMPORTANTE:
  // existenciaProducto es un INPUT.
  // Por eso usamos .value
  // y NO .textContent
  // ======================================================

  if (existencia) {
    existencia.value = `1 / ${stock}`;
  }

  // ======================================================
  // ABRIR MODAL
  // ======================================================

  const modalElement = document.getElementById("modalagregar");

  if (!modalElement) {
    return;
  }

  const modal = bootstrap.Modal.getOrCreateInstance(modalElement);

  modal.show();
}
// ==========================================================
// CONTROL DE CANTIDAD DEL MODAL
// ==========================================================

const inputCantidad = document.getElementById("nCanitdad");

if (inputCantidad) {
  inputCantidad.addEventListener("input", function () {
    // Permite borrar el valor inicial para escribir otra cantidad.
    // La validación obligatoria se realiza al agregar el producto.
    if (this.value === "") {
      const existencia = document.getElementById("existenciaProducto");
      if (existencia) {
        existencia.value = "";
      }
      return;
    }

    const producto = productos_dato[codex];

    if (!producto) {
      return;
    }

    // ==================================================
    // STOCK REAL
    // ==================================================

    const stock = parseFloat(producto.stock);

    if (isNaN(stock)) {
      return;
    }

    // ==================================================
    // STOCK VENDIBLE
    //
    // 6.83 -> 6
    // 9.99 -> 9
    // 10.00 -> 10
    // ==================================================

    const stockVendible = Math.floor(stock);

    // ==================================================
    // CANTIDAD INGRESADA
    // ==================================================

    let cantidad = parseInt(this.value, 10);

    if (isNaN(cantidad)) {
      cantidad = 1;
    }

    // ==================================================
    // NO PERMITIR MENOS DE 1
    // ==================================================

    if (cantidad < 1) {
      cantidad = 1;
    }

    // ==================================================
    // NO SUPERAR UNIDADES ENTERAS DISPONIBLES
    //
    // Ejemplo:
    // stock = 6.83
    // máximo = 6
    // ==================================================

    if (cantidad > stockVendible) {
      cantidad = stockVendible;

      mensaje(
        `La cantidad máxima que puede vender es ${stockVendible}. Existencia real: ${stock}`,
        "error",
        "",
      );
    }

    // ==================================================
    // ACTUALIZAR INPUT
    // ==================================================

    this.value = cantidad;

    // ==================================================
    // ACTUALIZAR EXISTENCIA
    //
    // IMPORTANTE:
    // Es un INPUT -> .value
    // ==================================================

    const existencia = document.getElementById("existenciaProducto");

    if (existencia) {
      existencia.value = `${cantidad} / ${stock}`;
    }
  });
}

// ==========================================================
// AGREGAR PRODUCTO DESDE MODAL
// ==========================================================

const btnRegis = document.getElementById("btnregis");

if (btnRegis) {
  btnRegis.addEventListener("click", function (e) {
    e.preventDefault();

    // ------------------------------------------------
    // OBTENER INPUTS
    // ------------------------------------------------

    const codigoInput = document.getElementById("nCodigo");

    const cantidadInput = document.getElementById("nCanitdad");

    if (!codigoInput || !cantidadInput) {
      return;
    }

    // ------------------------------------------------
    // CODIGO
    // ------------------------------------------------

    const codigo = codigoInput.value.trim();

    // ------------------------------------------------
    // CANTIDAD
    // ------------------------------------------------

    const cantidad = parseInt(cantidadInput.value, 10);

    // ------------------------------------------------
    // VALIDAR CANTIDAD
    // ------------------------------------------------

    if (isNaN(cantidad) || cantidad <= 0) {
      mensaje("La cantidad debe ser mayor que 0", "error", "");

      return;
    }

    // ------------------------------------------------
    // PRODUCTO SELECCIONADO
    // ------------------------------------------------

    const productoSeleccionado = productos_dato[codex];

    if (!productoSeleccionado) {
      mensaje("No se encontró el producto seleccionado", "error", "");

      return;
    }

    // ------------------------------------------------
    // STOCK REAL
    // ------------------------------------------------

    const stockReal = parseFloat(productoSeleccionado.stock) || 0;

    // ------------------------------------------------
    // STOCK VENDIBLE
    //
    // 6.83 -> 6
    // 7.50 -> 7
    // 10.00 -> 10
    // ------------------------------------------------

    const stockVendible = Math.floor(stockReal);

    // ------------------------------------------------
    // VALIDAR STOCK DEL PRODUCTO
    // ------------------------------------------------

    if (cantidad > stockVendible) {
      mensaje(
        `La cantidad máxima que puede vender es ${stockVendible}. Existencia real: ${stockReal}`,
        "error",
        "",
      );

      return;
    }

    // ------------------------------------------------
    // BUSCAR SI YA ESTÁ EN LA TABLA
    // ------------------------------------------------

    const producto = datos.findIndex((p) => p.codigo === codigo);

    // =================================================
    // PRODUCTO NO EXISTE EN LA TABLA
    // =================================================

    if (producto === -1) {
      let imp15 = 0;

      let imp18 = 0;

      // ------------------------------------------------
      // ISV 15
      // ------------------------------------------------

      if (parseFloat(productoSeleccionado.tipos_isv) === 15) {
        imp15 = parseFloat(productoSeleccionado.isv) || 0;
      }

      // ------------------------------------------------
      // ISV 18
      // ------------------------------------------------
      else if (parseFloat(productoSeleccionado.tipos_isv) === 18) {
        imp18 = parseFloat(productoSeleccionado.isv) || 0;
      }

      // ------------------------------------------------
      // PRECIO
      // ------------------------------------------------

      const precio = parseFloat(productoSeleccionado.precio_venta) || 0;

      // ------------------------------------------------
      // DESCUENTO
      // ------------------------------------------------

      const descuentoBase = parseFloat(productoSeleccionado.descuento) || 0;

      // ------------------------------------------------
      // CREAR PRODUCTO
      // ------------------------------------------------

      let producto_b = {
        id: productoSeleccionado.id,

        combo_id: productoSeleccionado.combo_id || null,

        es_combo: Boolean(productoSeleccionado.es_combo),

        codigo: productoSeleccionado.codigo_sku,

        nombre: productoSeleccionado.nombre,

        precio_venta: precio,

        precio_venta_min:
          parseFloat(productoSeleccionado.precio_venta_min) || 0,

        precio_venta_max:
          parseFloat(productoSeleccionado.precio_venta_max) || 0,

        tipos_isv: parseFloat(productoSeleccionado.tipos_isv) || 0,

        stock: stockReal,

        cantidad: cantidad,

        descuento: descuentoBase * cantidad,

        subtotal: precio * cantidad,

        valor_descuento: descuentoBase,

        acumulable: productoSeleccionado.es_acumulable,

        estado: 1,

        lleva: parseInt(productoSeleccionado.lleva) || 0,

        paga: parseInt(productoSeleccionado.paga) || 0,

        restarlleva: 0,

        isv_15: imp15,

        isv_18: imp18,

        isv15_acumulable: imp15 * cantidad,

        isv18_acumulable: imp18 * cantidad,
      };

      // ------------------------------------------------
      // PROMOCION LLEVA / PAGA
      // ------------------------------------------------

      if (producto_b.lleva > 0) {
        if (cantidad >= producto_b.lleva) {
          const grupos = Math.floor(cantidad / producto_b.lleva);

          producto_b.descuento +=
            producto_b.precio_venta *
            (producto_b.lleva - producto_b.paga) *
            grupos;

          if (cantidad % producto_b.lleva === 0) {
            producto_b.restarlleva = 1;
          }
        }
      }

      // ------------------------------------------------
      // AGREGAR A DATOS
      // ------------------------------------------------

      recalcularLineaConIsvIncluido(producto_b);
      datos.push(producto_b);

      // ------------------------------------------------
      // AGREGAR A TABLA
      // ------------------------------------------------

      tabla_codigo(
        productoSeleccionado.codigo_sku,

        productoSeleccionado.nombre,

        cantidad,

        precio.toFixed(2),

        producto_b.descuento.toFixed(2),

        (precio * cantidad).toFixed(2),
      );

      // ------------------------------------------------
      // CERRAR MODAL
      // ------------------------------------------------

      cerrarModalProducto();

      // ------------------------------------------------
      // ACTUALIZAR TOTALES
      // ------------------------------------------------

      tabla_detalle_total();

      return;
    }

    // =================================================
    // PRODUCTO YA EXISTE EN LA TABLA
    // =================================================

    const cantidadActual = parseInt(datos[producto].cantidad, 10) || 0;

    // ------------------------------------------------
    // NUEVA CANTIDAD
    // ------------------------------------------------

    const nuevaCantidad = cantidadActual + cantidad;

    // ------------------------------------------------
    // VALIDAR CONTRA STOCK ENTERO
    //
    // IMPORTANTE:
    //
    // stock = 6.83
    // stockVendible = 6
    //
    // actual = 6
    // agregar = 1
    // nueva = 7
    //
    // 7 > 6 -> BLOQUEADO
    // ------------------------------------------------

    if (nuevaCantidad > stockVendible) {
      mensaje(
        `No puede vender más de ${stockVendible} unidades. Existencia real: ${stockReal}. Actualmente tiene ${cantidadActual} unidades en la venta.`,
        "error",
        "",
      );

      return;
    }

    // ------------------------------------------------
    // ACTUALIZAR CANTIDAD
    // ------------------------------------------------

    datos[producto].cantidad = nuevaCantidad;

    // ------------------------------------------------
    // DESCUENTO
    // ------------------------------------------------

    if (datos[producto].estado === 1) {
      descuento_cantidad(producto);
    }

    // ------------------------------------------------
    // SUBTOTAL
    // ------------------------------------------------

    recalcularLineaConIsvIncluido(datos[producto]);

    // ------------------------------------------------
    // OBTENER TABLA
    // ------------------------------------------------

    const tabla = document.getElementById("tablaProductos");

    if (!tabla) {
      return;
    }

    const fila = tabla.rows[producto + 1];

    if (fila) {
      const c = fila.querySelector(".pre");

      const s = fila.cells[5];

      const d = fila.cells[4];

      // --------------------------------------------
      // CANTIDAD
      // --------------------------------------------

      if (c) {
        c.textContent = `${datos[producto].cantidad} / ${datos[producto].stock}`;
      }

      // --------------------------------------------
      // SUBTOTAL
      // --------------------------------------------

      if (s) {
        s.textContent = "L. " + totalLineaCaja(datos[producto]).toFixed(2);
      }

      // --------------------------------------------
      // DESCUENTO
      // --------------------------------------------

      if (d) {
        d.textContent = "L. " + datos[producto].descuento.toFixed(2);
      }
    }

    // ------------------------------------------------
    // CERRAR MODAL
    // ------------------------------------------------

    cerrarModalProducto();

    // ------------------------------------------------
    // ACTUALIZAR TOTALES
    // ------------------------------------------------

    tabla_detalle_total();
  });
}

// ==========================================================
// CERRAR MODAL PRODUCTO
// ==========================================================

function cerrarModalProducto() {
  const modalElement = document.getElementById("modalagregar");

  if (modalElement) {
    const modal = bootstrap.Modal.getOrCreateInstance(modalElement);

    modal.hide();
  }

  const cantidad = document.getElementById("nCanitdad");

  if (cantidad) {
    cantidad.value = 1;
  }
}

// ==========================================================
// CREAR FILA EN TABLA
// ==========================================================

function tabla_codigo(codigo, nombre, canti, sub, des, total) {
  const tabla = document.querySelector("#tablaProductos tbody");

  if (!tabla) {
    console.error("No existe #tablaProductos tbody");

    return;
  }

  const fila = tabla.insertRow();

  fila.insertCell(0).textContent = codigo;

  fila.insertCell(1).textContent = nombre;

  const cantidad = fila.insertCell(2);

  const celdaPrecio = fila.insertCell(3);
  celdaPrecio.textContent = "L. " + sub;

  const puedeModificarPrecio =
    document.getElementById("tablaProductos")?.dataset.puedeModificarPrecio ===
    "true";

  if (puedeModificarPrecio) {
    celdaPrecio.classList.add("precio-editable");
    celdaPrecio.title = "Clic para modificar el precio";
    celdaPrecio.style.cursor = "pointer";
  }

  fila.insertCell(4).textContent = "L. " + des;

  fila.insertCell(5).textContent = "L. " + total;

  const boton = fila.insertCell(6);

  // ------------------------------------------------------
  // CONTENEDOR CANTIDAD
  // ------------------------------------------------------

  const div_row = document.createElement("div");

  div_row.className = "div_row";

  const div_pre = document.createElement("div");

  const p = document.createElement("p");

  p.className = "pre";

  p.textContent = canti;

  div_pre.appendChild(p);

  // ------------------------------------------------------
  // BOTONES + -
  // ------------------------------------------------------

  const button_mas = document.createElement("button");

  button_mas.type = "button";

  button_mas.className = "btn_add";

  button_mas.innerHTML = '<i class="bx bx-plus" aria-hidden="true"></i>';

  const button_men = document.createElement("button");

  button_men.type = "button";

  button_men.className = "btn_quantity-minus";

  button_men.innerHTML = '<i class="bx bx-minus" aria-hidden="true"></i>';

  div_row.appendChild(button_mas);
  div_row.appendChild(div_pre);
  div_row.appendChild(button_men);

  cantidad.appendChild(div_row);

  const botonEliminar = document.createElement("button");
  botonEliminar.type = "button";
  botonEliminar.className = "btn_remove";
  botonEliminar.title = "Eliminar producto";
  botonEliminar.setAttribute("aria-label", "Eliminar producto");
  botonEliminar.innerHTML = '<i class="bx bx-trash" aria-hidden="true"></i>';
  boton.appendChild(botonEliminar);

  tabla_detalle_total();
}

// ==========================================================
// EVENTOS DE LA TABLA
// ==========================================================

const tbody = document.querySelector("#tablaProductos tbody");

function restaurarPrecioCelda(celda, producto) {
  celda.textContent = "L. " + producto.precio_venta.toFixed(2);
}

function aplicarPrecioCaja(indice, celda, valor) {
  const producto = datos[indice];
  const nuevoPrecio = Number(valor);

  if (!Number.isFinite(nuevoPrecio)) {
    restaurarPrecioCelda(celda, producto);
    return;
  }

  if (nuevoPrecio < producto.precio_venta_min) {
    Swal.fire(
      "Precio no permitido",
      `El precio mínimo es L. ${producto.precio_venta_min.toFixed(2)}`,
      "warning",
    );
    restaurarPrecioCelda(celda, producto);
    return;
  }

  if (producto.precio_venta_max && nuevoPrecio > producto.precio_venta_max) {
    Swal.fire(
      "Precio no permitido",
      `El precio máximo es L. ${producto.precio_venta_max.toFixed(2)}`,
      "warning",
    );
    restaurarPrecioCelda(celda, producto);
    return;
  }

  producto.precio_venta = nuevoPrecio;
  recalcularLineaConIsvIncluido(producto);

  restaurarPrecioCelda(celda, producto);

  const fila = celda.closest("tr");
  fila.cells[5].textContent = "L. " + totalLineaCaja(producto).toFixed(2);
  tabla_detalle_total();
}

if (tbody) {
  tbody.addEventListener("click", function (e) {
    const fila = e.target.closest("tr");

    if (!fila) {
      return;
    }

    const indice = fila.sectionRowIndex;

    if (!datos[indice]) {
      return;
    }

    if (e.target.closest(".precio-editable")) {
      const celda = e.target.closest(".precio-editable");

      if (celda.querySelector("input")) return;

      const producto = datos[indice];
      const input = document.createElement("input");
      input.type = "number";
      input.step = "0.01";
      input.min = producto.precio_venta_min;
      input.value = producto.precio_venta.toFixed(2);
      input.className = "form-control form-control-sm";

      celda.textContent = "";
      celda.appendChild(input);
      input.focus();
      input.select();

      let precioAplicado = false;
      const confirmarPrecio = () => {
        if (precioAplicado) return;
        precioAplicado = true;
        aplicarPrecioCaja(indice, celda, input.value);
      };

      input.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          event.stopPropagation();
          confirmarPrecio();
        }

        if (event.key === "Escape") {
          precioAplicado = true;
          restaurarPrecioCelda(celda, producto);
        }
      });

      input.addEventListener("blur", () => {
        confirmarPrecio();
      });

      return;
    }

    // ==================================================
    // BOTON +
    // ==================================================

    if (e.target.closest(".btn_add")) {
      const producto = datos[indice];

      // ----------------------------------------------
      // STOCK REAL
      // ----------------------------------------------

      const stockReal = parseFloat(producto.stock) || 0;

      // ----------------------------------------------
      // STOCK VENDIBLE
      //
      // 6.83 -> 6
      // 7.99 -> 7
      // 10.00 -> 10
      // ----------------------------------------------

      const stockVendible = Math.floor(stockReal);

      // ----------------------------------------------
      // VALIDAR
      // ----------------------------------------------

      if (producto.cantidad + 1 > stockVendible) {
        mensaje(
          `No puede vender más de ${stockVendible} unidades. Existencia real: ${stockReal}`,
          "error",
          "",
        );

        return;
      }

      // ----------------------------------------------
      // AUMENTAR
      // ----------------------------------------------

      producto.cantidad++;

      // ----------------------------------------------
      // DESCUENTO
      // ----------------------------------------------

      if (producto.estado === 1) {
        descuento_cantidad(indice);
      }

      // ----------------------------------------------
      // SUBTOTAL
      // ----------------------------------------------

      recalcularLineaConIsvIncluido(producto);

      // ----------------------------------------------
      // ACTUALIZAR TABLA
      // ----------------------------------------------

      const c = fila.querySelector(".pre");

      const s = fila.cells[5];

      const d = fila.cells[4];

      if (c) {
        c.textContent = `${producto.cantidad} / ${producto.stock}`;
      }

      if (s) {
        s.textContent = "L. " + totalLineaCaja(producto).toFixed(2);
      }

      if (d) {
        d.textContent = "L. " + producto.descuento.toFixed(2);
      }

      tabla_detalle_total();

      return;
    }

    // ==================================================
    // ELIMINAR PRODUCTO
    // ==================================================

    if (e.target.closest(".btn_remove")) {
      datos.splice(indice, 1);
      fila.remove();
      tabla_detalle_total();
      return;
    }

    // ==================================================
    // BOTON -
    // ==================================================

    if (e.target.closest(".btn_quantity-minus")) {
      const producto = datos[indice];

      // ----------------------------------------------
      // DISMINUIR
      // ----------------------------------------------

      producto.cantidad--;

      // ----------------------------------------------
      // DESCUENTO
      // ----------------------------------------------

      if (producto.estado === 1) {
        if (producto.lleva > 0) {
          if (
            producto.cantidad % producto.lleva !== 0 &&
            producto.restarlleva === 1
          ) {
            producto.descuento -=
              producto.precio_venta * (producto.lleva - producto.paga);

            producto.restarlleva = 0;
          } else if (
            producto.cantidad % producto.lleva === 0 &&
            producto.restarlleva === 0
          ) {
            producto.restarlleva = 1;
          }
        } else {
          producto.descuento -= producto.valor_descuento;
        }
      }

      // ----------------------------------------------
      // SUBTOTAL
      // ----------------------------------------------

      recalcularLineaConIsvIncluido(producto);

      // ----------------------------------------------
      // ELIMINAR SI LLEGA A CERO
      // ----------------------------------------------

      if (producto.cantidad <= 0) {
        datos.splice(indice, 1);

        fila.remove();

        tabla_detalle_total();

        return;
      }

      // ----------------------------------------------
      // ACTUALIZAR TABLA
      // ----------------------------------------------

      const c = fila.querySelector(".pre");

      const s = fila.cells[5];

      const d = fila.cells[4];

      if (c) {
        c.textContent = `${producto.cantidad} / ${producto.stock}`;
      }

      if (s) {
        s.textContent = "L. " + totalLineaCaja(producto).toFixed(2);
      }

      if (d) {
        d.textContent = "L. " + producto.descuento.toFixed(2);
      }

      tabla_detalle_total();

      return;
    }
  });
}

// ==========================================================
// DESCUENTO POR CANTIDAD
// ==========================================================

function descuento_cantidad(indice) {
  if (!datos[indice]) {
    return;
  }

  if (datos[indice].lleva > 0) {
    if (datos[indice].cantidad % datos[indice].lleva === 0) {
      datos[indice].descuento +=
        datos[indice].precio_venta * (datos[indice].lleva - datos[indice].paga);

      datos[indice].restarlleva = 1;
    } else if (
      datos[indice].cantidad % datos[indice].lleva !== 0 &&
      datos[indice].restarlleva === 1
    ) {
      datos[indice].restarlleva = 0;
    }
  } else {
    datos[indice].descuento += datos[indice].valor_descuento;
  }
}

// ==========================================================
// ABRIR MODAL DESCUENTO
// ==========================================================

function add_descuento(fila) {
  if (!fila) {
    return;
  }

  fila_descuento = fila;

  const modalElement = document.getElementById("modalDescuento");

  if (!modalElement) {
    return;
  }

  const modal = bootstrap.Modal.getOrCreateInstance(modalElement);

  modal.show();
}

const btnCuponGlobal = document.getElementById("btnCuponGlobal");

if (btnCuponGlobal) {
  btnCuponGlobal.addEventListener("click", async () => {
    if (!datos.length) {
      mensaje("Agregue un producto antes de aplicar un cupón", "warning", "");
      return;
    }

    if (datos.length === 1) {
      add_descuento(tbody.rows[0]);
      return;
    }

    const opciones = Object.fromEntries(
      datos.map((producto, indice) => [
        indice,
        producto.nombre || producto.codigo || `Producto ${indice + 1}`,
      ]),
    );

    const resultado = await Swal.fire({
      title: "¿A qué producto aplicarás el cupón?",
      input: "select",
      inputOptions: opciones,
      inputPlaceholder: "Selecciona un producto",
      showCancelButton: true,
      confirmButtonText: "Continuar",
      cancelButtonText: "Cancelar",
      customClass: {
        confirmButton: "classbotones",
        input: "caja-descuento-select",
      },
    });

    if (resultado.isConfirmed && resultado.value !== "") {
      add_descuento(tbody.rows[Number(resultado.value)]);
    }
  });
}

function cargarCotizacionEnCaja(cotizacion) {
  const productos = cotizacion.productos || [];
  if (!productos.length) {
    mensaje("La cotización no contiene productos", "warning", "");
    return;
  }

  productos.forEach((item) => {
    const cantidad = Number(item.cantidad) || 1;
    const impuesto15 = Number(item.isv_15) || 0;
    const impuesto18 = Number(item.isv_18) || 0;
    const producto = {
      id: item.id,
      combo_id: item.combo_id || null,
      es_combo: Boolean(item.es_combo),
      codigo: item.codigo_sku,
      nombre: item.nombre,
      precio_venta: Number(item.precio_venta) || 0,
      precio_venta_min: 0,
      precio_venta_max: 0,
      tipos_isv: impuesto15 > 0 ? 15 : impuesto18 > 0 ? 18 : 0,
      stock: cantidad,
      cantidad: cantidad,
      descuento: Number(item.descuento) || 0,
      subtotal: Number(item.subtotal) || 0,
      valor_descuento: 0,
      acumulable: false,
      estado: 0,
      isv_15: impuesto15 / cantidad,
      isv_18: impuesto18 / cantidad,
      isv15_acumulable: impuesto15,
      isv18_acumulable: impuesto18,
      lleva: 0,
      paga: 0,
      restarlleva: 0,
    };
    recalcularLineaConIsvIncluido(producto);
    datos.push(producto);
    tabla_codigo(
      producto.codigo,
      producto.nombre,
      `${cantidad} / ${cantidad}`,
      producto.precio_venta.toFixed(2),
      producto.descuento.toFixed(2),
      totalLineaCaja(producto).toFixed(2),
    );
  });

  tabla_detalle_total();
  mensaje(
    `Cotización ${cotizacion.numero_cotizacion} agregada a la venta`,
    "success",
    "",
  );
}

const btnGenerarCotizacion = document.getElementById("btnGenerarCotizacion");

if (btnGenerarCotizacion) {
  btnGenerarCotizacion.addEventListener("click", async () => {
    if (!datos.length) {
      mensaje(
        "Agregue productos antes de generar la cotización",
        "warning",
        "",
      );
      return;
    }

    if (!btnGenerarCotizacion.dataset.clienteConfirmado) {
      cotizacionPendienteCliente = true;
      abrirSelectorClienteParaCotizacion();
      return;
    }
    delete btnGenerarCotizacion.dataset.clienteConfirmado;

    const confirmacion = await Swal.fire({
      title: "Generar cotización",
      text: "Se guardarán los productos y precios actuales.",
      icon: "question",
      showCancelButton: true,
      confirmButtonText: "Generar",
      cancelButtonText: "Cancelar",
      customClass: { confirmButton: "classbotones" },
    });
    if (!confirmacion.isConfirmed) return;

    const csrf = document.querySelector("[name=csrfmiddlewaretoken]");
    if (!csrf) {
      mensaje("No se encontró el token de seguridad", "error", "");
      return;
    }

    btnGenerarCotizacion.disabled = true;
    try {
      const respuesta = await fetch(btnGenerarCotizacion.dataset.url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrf.value,
        },
        body: JSON.stringify({
          productos: datos,
          cliente_id: document.getElementById("cliente_id")?.value || null,
          cliente_nombre:
            document.getElementById("cliente_nombre")?.value || "",
          con_rtn: clienteSeleccionado?.con_rtn || false,
        }),
      });
      const data = await respuesta.json();
      if (!respuesta.ok || !data.success) {
        throw new Error(data.message || "No fue posible generar la cotización");
      }

      await Swal.fire({
        title: "Cotización generada",
        html: `Número: <b>${data.numero}</b>`,
        icon: "success",
        confirmButtonText: "Descargar PDF",
        allowOutsideClick: false,
        customClass: { confirmButton: "classbotones" },
      });
      window.open(data.pdf_url, "_blank");
      window.location.reload();
    } catch (error) {
      mensaje(error.message, "error", "");
    } finally {
      btnGenerarCotizacion.disabled = false;
    }
  });
}

// ==========================================================
// APLICAR CUPON
// ==========================================================
//
// IMPORTANTE:
// En tu HTML el botón del descuento tiene:
//
// id="btndescuento"
//
// Este ID debería cambiarse en HTML a:
//
// id="btnAplicarDescuento"
//
// El JS soporta ambos para que no se rompa.
// ==========================================================

const btnAplicarDescuento =
  document.getElementById("btnAplicarDescuento") ||
  document.getElementById("btndescuento");

if (btnAplicarDescuento) {
  btnAplicarDescuento.addEventListener("click", function (e) {
    e.preventDefault();

    if (!fila_descuento) {
      mensaje("Seleccione un producto", "warning", "");

      return;
    }

    const descuento = document.getElementById("Ddescuento");

    if (!descuento) {
      return;
    }

    const indice = fila_descuento.sectionRowIndex;

    if (!datos[indice]) {
      return;
    }

    const d = fila_descuento.cells[4];

    fetch(`/manager/cupon_descuento/${descuento.value}/${datos[indice].id}/`, {
      method: "GET",
      headers: {},
    })
      .then(async (response) => {
        if (!response.ok) {
          const dato = await response.json();

          throw new Error(dato.error || dato.mensaje || "Error desconocido");
        }

        return response.json();
      })

      .then((data) => {
        const valor = parseFloat(data.descuento) || 0;

        if (datos[indice].acumulable) {
          datos[indice].descuento += valor;
        } else {
          if (datos[indice].estado === 1) {
            datos[indice].descuento = valor;

            datos[indice].estado = 0;
          } else {
            datos[indice].descuento += valor;
          }
        }

        if (d) {
          d.textContent = "L. " + datos[indice].descuento.toFixed(2);
        }

        fila_descuento = null;

        tabla_detalle_total();

        const modalElement = document.getElementById("modalDescuento");

        if (modalElement) {
          const modal = bootstrap.Modal.getOrCreateInstance(modalElement);

          modal.hide();
        }
      })

      .catch((error) => {
        mensaje(error.message, "error", "");
      });
  });
}

// ==========================================================
// CALCULAR TOTALES
// ==========================================================

function tabla_detalle_total() {
  pagos = [];

  let subtotal = 0;

  let descuento = 0;

  let isv15 = 0;

  let isv18 = 0;

  datos.forEach((item) => {
    subtotal += parseFloat(item.subtotal) || 0;

    descuento += parseFloat(item.descuento) || 0;

    isv15 += parseFloat(item.isv15_acumulable) || 0;

    isv18 += parseFloat(item.isv18_acumulable) || 0;
  });

  const totalOriginal = subtotal + isv15 + isv18 - descuento;

  const montoNotaCredito = notaCreditoSeleccionada
    ? Number(notaCreditoSeleccionada.monto)
    : 0;

  const total = totalOriginal - montoNotaCredito;

  const tabla = document.getElementById("detalle-total");

  if (!tabla) {
    return;
  }

  const celda_subtotal = tabla.rows[0]?.cells[1];

  const celda_descuento = tabla.rows[1]?.cells[1];

  const celda_nota_credito = tabla.rows[2]?.cells[1];

  const fila_nota_credito = tabla.querySelector(".nota-credito-row");

  const celda_isv15 = tabla.rows[3]?.cells[1];

  const celda_isv18 = tabla.rows[4]?.cells[1];

  const celda_total = tabla.rows[5]?.cells[1];

  total_m = total;

  pagos.push({
    rtn: "",

    subtotal: subtotal,

    descuento: descuento,

    isv15: isv15,

    isv18: isv18,

    total_original: totalOriginal,

    nota_credito: montoNotaCredito,

    total: total,

    tipo_pago: "",

    cliente_id: clienteSeleccionado ? clienteSeleccionado.id : "",

    cliente_nombre: clienteSeleccionado ? clienteSeleccionado.nombre : "",
  });

  if (celda_subtotal) {
    celda_subtotal.textContent = "L. " + subtotal.toFixed(2);
  }

  if (celda_descuento) {
    celda_descuento.textContent = "L. " + descuento.toFixed(2);
  }

  if (celda_nota_credito) {
    celda_nota_credito.textContent = "- L. " + montoNotaCredito.toFixed(2);
  }

  if (fila_nota_credito) {
    fila_nota_credito.style.display =
      montoNotaCredito > 0 ? "table-row" : "none";
  }

  if (celda_isv15) {
    celda_isv15.textContent = "L. " + isv15.toFixed(2);
  }

  if (celda_isv18) {
    celda_isv18.textContent = "L. " + isv18.toFixed(2);
  }

  if (celda_total) {
    celda_total.textContent = "L. " + total.toFixed(2);
  }
}

// ==========================================================
// NOTAS DE CREDITO
// ==========================================================

const btnNotasCredito = document.getElementById("btnNotasCredito");
const notasCreditoBody = document.getElementById("notasCreditoBody");
const buscarNotaCredito = document.getElementById("buscarNotaCredito");
const btnBuscarNotaCredito = document.getElementById("btnBuscarNotaCredito");
const modalNotasCreditoElement = document.getElementById("modalNotasCredito");
const modalNotasCredito = modalNotasCreditoElement
  ? new bootstrap.Modal(modalNotasCreditoElement)
  : null;

function dinero(valor) {
  return Number(valor || 0).toFixed(2);
}

function renderNotasCredito(notas) {
  if (!notasCreditoBody) return;

  if (!notas.length) {
    notasCreditoBody.innerHTML = `
            <tr>
                <td colspan="5" class="text-center text-muted py-4">
                    No hay notas de crédito disponibles.
                </td>
            </tr>`;
    return;
  }

  notasCreditoBody.innerHTML = "";

  notas.forEach((nota) => {
    const fila = document.createElement("tr");
    const estaAplicada = notaCreditoSeleccionada?.id === nota.id;
    const textoBoton = estaAplicada
      ? '<i class="bx bx-x"></i> Quitar'
      : '<i class="bx bx-check"></i> Aplicar';
    const claseBoton = estaAplicada ? "btn-danger" : "btn-success";

    fila.innerHTML = `
            <td></td><td></td><td></td><td></td>
            <td class="text-end">
                <button type="button" class="btn btn-sm ${claseBoton} btn-aplicar-nota">
                    ${textoBoton}
                </button>
            </td>`;

    fila.cells[0].textContent = nota.nota;
    fila.cells[1].textContent = `#${nota.factura}`;
    fila.cells[2].textContent = nota.cliente;
    fila.cells[3].textContent = `L. ${dinero(nota.monto)}`;

    fila.querySelector(".btn-aplicar-nota").addEventListener("click", () => {
      if (estaAplicada) {
        notaCreditoSeleccionada = null;
        tabla_detalle_total();
        modalNotasCredito?.hide();
        return;
      }

      tabla_detalle_total();
      const totalOriginal = pagos[0]?.total_original || 0;
      if (Number(nota.monto) > Number(totalOriginal)) {
        Swal.fire({
          title: "Nota no aplicable",
          text: "La compra debe ser igual o mayor al valor de la nota de crédito.",
          icon: "warning",
          confirmButtonText: "Aceptar",
          customClass: { confirmButton: "classbotones" },
        });
        return;
      }

      notaCreditoSeleccionada = nota;
      tabla_detalle_total();
      modalNotasCredito?.hide();
    });

    notasCreditoBody.appendChild(fila);
  });
}

async function cargarNotasCredito() {
  if (!btnNotasCredito || !notasCreditoBody) return;

  const referencia = buscarNotaCredito?.value.trim() || "";
  if (!referencia) {
    notasCreditoBody.innerHTML = `
            <tr><td colspan="5" class="text-center text-muted py-4">
                Ingrese una referencia y presione buscar.
            </td></tr>`;
    return;
  }

  notasCreditoBody.innerHTML = `
        <tr><td colspan="5" class="text-center text-muted py-4">
            <i class="bx bx-loader-alt bx-spin"></i> Cargando notas...
        </td></tr>`;

  try {
    const url = new URL(
      btnNotasCredito.dataset.notasUrl,
      window.location.origin,
    );
    url.searchParams.set("search", referencia);
    const respuesta = await fetch(url);
    const data = await respuesta.json();
    if (!respuesta.ok || !data.success) {
      throw new Error(
        data.message || "No se pudieron cargar las notas de crédito",
      );
    }
    renderNotasCredito(data.notas);
  } catch (error) {
    notasCreditoBody.innerHTML = `
            <tr><td colspan="5" class="text-center text-danger py-4"></td></tr>`;
    notasCreditoBody.querySelector("td").textContent = error.message;
  }
}

if (btnNotasCredito) {
  btnNotasCredito.addEventListener("click", () => {
    if (modalNotasCredito) modalNotasCredito.show();
    if (buscarNotaCredito) buscarNotaCredito.value = "";
    if (notasCreditoBody) {
      notasCreditoBody.innerHTML = `
                <tr><td colspan="5" class="text-center text-muted py-4">
                    Ingrese una referencia y presione buscar.
                </td></tr>`;
    }
  });
}

if (btnBuscarNotaCredito) {
  btnBuscarNotaCredito.addEventListener("click", cargarNotasCredito);
}

if (buscarNotaCredito) {
  buscarNotaCredito.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      cargarNotasCredito();
    }
  });
}

// ==========================================================
// CAJA - SECCIÓN 2
// CLIENTES, PAGOS, APERTURA Y CIERRE
// ==========================================================

// ==========================================================
// SELECCIONAR CLIENTE
// ==========================================================

const btnSeleccionarCliente = document.getElementById("btnSeleccionarCliente");

function abrirSelectorClienteParaCotizacion() {
  const buscar = document.getElementById("buscarClienteInput");
  const resultados = document.getElementById("tablaClientesResultados");
  const conRtn = document.getElementById("clienteConRtn");
  if (buscar) buscar.value = "";
  if (resultados) resultados.innerHTML = "";
  if (conRtn) conRtn.checked = false;

  const modalElement = document.getElementById("modalSeleccionarCliente");
  if (modalElement) {
    bootstrap.Modal.getOrCreateInstance(modalElement).show();
  }
}

if (btnSeleccionarCliente) {
  btnSeleccionarCliente.addEventListener("click", function () {
    abrirSelectorClienteParaCotizacion();
  });
}

// ==========================================================
// BUSCAR CLIENTE
// ==========================================================

const buscarClienteInput = document.getElementById("buscarClienteInput");

const btnBuscarCliente = document.getElementById("btnBuscarCliente");

function buscarClientes() {
  const texto = buscarClienteInput?.value.trim() || "";
  const resultados = document.getElementById("tablaClientesResultados");

  if (!resultados) return;
  resultados.innerHTML = "";

  if (texto.length < 2) {
    mensaje("Ingrese al menos 2 caracteres para buscar", "error", "");
    return;
  }

  if (clienteBusquedaControlador) clienteBusquedaControlador.abort();
  clienteBusquedaControlador = new AbortController();

  fetch(`/manager/clientes/search/?search=${encodeURIComponent(texto)}`, {
    method: "GET",
    signal: clienteBusquedaControlador.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        const dato = await response.json();
        throw new Error(dato.error || "Error al buscar clientes");
      }
      return response.json();
    })
    .then((data) => {
      if (!data.length) {
        resultados.innerHTML = `
                    <tr><td colspan="5" class="text-center text-muted">
                        No se encontraron clientes
                    </td></tr>`;
        return;
      }

      data.forEach((cliente) => {
        const fila = document.createElement("tr");
        fila.style.cursor = "pointer";

        [
          cliente.id,
          cliente.nombre_completo || "Sin nombre",
          cliente.dni || "-",
          cliente.empresa || "-",
          cliente.telefono || "-",
        ].forEach((valor) => {
          const celda = document.createElement("td");
          celda.textContent = valor;
          fila.appendChild(celda);
        });

        fila.addEventListener("click", () => seleccionarCliente(cliente));
        resultados.appendChild(fila);
      });
    })
    .catch((error) => {
      if (error.name !== "AbortError") mensaje(error.message, "error", "");
    });
}

if (btnBuscarCliente)
  btnBuscarCliente.addEventListener("click", buscarClientes);

if (buscarClienteInput) {
  buscarClienteInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      buscarClientes();
    }
  });
}

// ==========================================================
// GUARDAR CLIENTE SELECCIONADO
// ==========================================================

function seleccionarCliente(cliente) {
  if (!cliente) {
    return;
  }

  const conRtn = document.getElementById("clienteConRtn")?.checked || false;
  const nombreCliente = cliente.nombre_completo || cliente.dni || "Cliente";
  const nombreFactura = conRtn
    ? cliente.empresa || nombreCliente
    : nombreCliente;

  clienteSeleccionado = {
    id: cliente.id,

    nombre: nombreFactura,

    con_rtn: conRtn,
  };

  const clienteId = document.getElementById("cliente_id");

  const clienteNombre = document.getElementById("cliente_nombre");

  const clienteSeleccionadoInput = document.getElementById(
    "clienteSeleccionado",
  );

  const detalle = document.getElementById("detalleClienteSeleccionado");

  if (clienteId) {
    clienteId.value = cliente.id;
  }

  if (clienteNombre) {
    clienteNombre.value = clienteSeleccionado.nombre;
  }

  if (clienteSeleccionadoInput) {
    clienteSeleccionadoInput.value = clienteSeleccionado.nombre;
  }

  if (detalle) {
    detalle.textContent = conRtn
      ? `RTN: ${cliente.dni || "-"} • Teléfono: ${cliente.telefono || "-"}`
      : `DNI: ${cliente.dni || "-"} • Teléfono: ${cliente.telefono || "-"}`;
  }

  // ------------------------------------------------------
  // CERRAR MODAL
  // ------------------------------------------------------

  const modalElement = document.getElementById("modalSeleccionarCliente");

  if (modalElement) {
    const modal = bootstrap.Modal.getInstance(modalElement);

    if (modal) {
      modal.hide();
    }
  }

  if (cotizacionPendienteCliente) {
    cotizacionPendienteCliente = false;
    const botonCotizacion = document.getElementById("btnGenerarCotizacion");
    if (botonCotizacion) {
      botonCotizacion.dataset.clienteConfirmado = "true";
      botonCotizacion.click();
    }
  }

  // ------------------------------------------------------
  // ACTUALIZAR PAGO
  // ------------------------------------------------------

  if (pagos.length > 0) {
    pagos[0].cliente_id = cliente.id;

    pagos[0].cliente_nombre = clienteSeleccionado.nombre;

    pagos[0].con_rtn = clienteSeleccionado.con_rtn;
  }
}

// ==========================================================
// PAGOS
// ==========================================================

let ventaEnProceso = false;

const postPagar = document.getElementById("postpagar");

if (postPagar) {
  postPagar.addEventListener("submit", function (e) {
    e.preventDefault();

    // Evitar doble envío
    if (ventaEnProceso) {
      return;
    }

    // ------------------------------------------------
    // VALIDAR PRODUCTOS
    // ------------------------------------------------

    if (datos.length === 0) {
      mensaje("Agregue productos a la venta", "error", "");
      return;
    }

    const tipoPago = document.getElementById("tipo_pago")?.value;

    const tarjeta = [];

    const cantidadDinero = document.getElementById("Pdinero")?.value || "";

    const digitos = document.getElementById("Pdigitos")?.value.trim() || "";

    const autorizacion =
      document.getElementById("Pautorizacion")?.value.trim() || "";

    const clienteId = document.getElementById("cliente_id")?.value || "";

    const clienteNombre =
      document.getElementById("cliente_nombre")?.value || "";

    // ------------------------------------------------
    // CLIENTE
    // ------------------------------------------------

    if (!clienteId) {
      mensaje("Seleccione un cliente antes de realizar la venta", "error", "");
      return;
    }

    // =================================================
    // PAGO CONTADO
    // =================================================

    if (tipoPago === "pago_contado" || tipoPago === "pago_deposito") {
      if (
        (pagos[0].total > 0 && cantidadDinero.trim() === "") ||
        isNaN(cantidadDinero || "0") ||
        parseFloat(cantidadDinero) < pagos[0].total
      ) {
        mensaje("Ingrese una cantidad válida", "error", "");
        return;
      }

      pagos[0].tipo_pago =
        tipoPago === "pago_contado" ? "contado" : "depostivo";

      tarjeta.push({
        digitos: "",
        numero_autorizacion: "",
      });

      // =================================================
      // PAGO CON CHEQUE
      // =================================================
    } else if (tipoPago === "pago_cheque") {
      pagos[0].tipo_pago = "cheque";

      // =================================================
      // PAGO TARJETA
      // =================================================
    } else if (tipoPago === "pago_tarjeta") {
      if (autorizacion === "") {
        mensaje("Escriba el número de autorización", "error", "");
        return;
      }

      if (!/^\d{4}$/.test(digitos)) {
        mensaje(
          "Ingrese únicamente los últimos 4 dígitos de la tarjeta",
          "error",
          "",
        );
        return;
      }

      pagos[0].tipo_pago = "tarjeta";

      tarjeta.push({
        digitos: digitos,
        numero_autorizacion: autorizacion,
      });

      // =================================================
      // PAGO A CRÉDITO
      // =================================================
    } else if (tipoPago === "pago_credito") {
      pagos[0].tipo_pago = "credito";
    } else {
      mensaje("Seleccione un tipo de pago", "error", "");
      return;
    }

    // ------------------------------------------------
    // PREPARAR DATA
    // ------------------------------------------------

    const data = {
      productos: datos,
      pagos: pagos,
      tarjeta: tarjeta,
      nota_credito_id: notaCreditoSeleccionada?.id || null,
      cliente: {
        id: clienteId,
        nombre: clienteNombre,
        con_rtn: clienteSeleccionado?.con_rtn || false,
      },
    };

    // =================================================
    // CONFIRMAR TARJETA
    // =================================================

    if (tipoPago === "pago_tarjeta") {
      Swal.fire({
        title: "Confirmar pago con tarjeta",
        html: `
                    <div style="text-align:left">
                        <b>Total:</b>
                        L. ${pagos[0].total.toFixed(2)}
                        <br>
                        <b>Autorización:</b>
                        ${autorizacion}
                        <br>
                        <b>Tarjeta:</b>
                        ****${digitos}
                    </div>
                `,
        icon: "question",
        showCancelButton: true,
        confirmButtonText: "Procesar venta",
        cancelButtonText: "Cancelar",
        customClass: {
          confirmButton: "classbotones",
        },
      }).then((result) => {
        if (result.isConfirmed) {
          enviarVenta(data, tipoPago, cantidadDinero);
        }
      });

      return;
    }

    // =================================================
    // CONTADO
    // =================================================

    enviarVenta(data, tipoPago, cantidadDinero);
  });
}

// ==========================================================
// ENVIAR VENTA
// ==========================================================

function limpiarCajaDespuesDeVenta() {
  // La venta ya fue persistida por el servidor. Se reinicia únicamente el
  // estado de la interfaz para conservar esta página y su WebSocket abiertos.
  datos = [];
  productos_dato = [];
  pagos = [];
  tarjetas = [];
  fila_descuento = null;
  notaCreditoSeleccionada = null;
  clienteSeleccionado = null;
  cotizacionPendienteCliente = false;
  total_m = 0;
  codex = 0;

  controlador?.abort();
  controlador = null;
  clienteBusquedaControlador?.abort();
  clienteBusquedaControlador = null;

  document.querySelector("#tablaProductos tbody")?.replaceChildren();
  document.getElementById("postpagar")?.reset();
  document.getElementById("formDescuento")?.reset();

  const codigo = document.getElementById("codigo_busqueda");
  if (codigo) codigo.value = "";
  const clienteId = document.getElementById("cliente_id");
  const clienteNombre = document.getElementById("cliente_nombre");
  const clienteVisible = document.getElementById("clienteSeleccionado");
  const detalleCliente = document.getElementById("detalleClienteSeleccionado");
  if (clienteId) clienteId.value = "";
  if (clienteNombre) clienteNombre.value = "";
  if (clienteVisible) clienteVisible.value = "";
  if (detalleCliente) detalleCliente.textContent = "";

  ["div_dinero", "div_nuemro", "div_digito", "div_banco", "div_red"].forEach(
    (id) => {
      const campo = document.getElementById(id);
      if (campo) campo.style.display = "none";
    },
  );
  const dineroRecibido = document.getElementById("Pdinero");
  if (dineroRecibido) dineroRecibido.value = "0.00";

  const notasBody = document.getElementById("notasCreditoBody");
  if (notasBody) {
    notasBody.innerHTML =
      '<tr><td colspan="5" class="text-center text-muted py-4">Ingrese una referencia y presione buscar.</td></tr>';
  }
  const buscarNota = document.getElementById("buscarNotaCredito");
  if (buscarNota) buscarNota.value = "";

  tabla_detalle_total();
  ventaEnProceso = false;
  actualizarAccionesPorCaja(
    document.getElementById("accionesCaja")?.dataset.cajaAbierta === "true",
  );

  const modalPago = document.getElementById("modalPago");
  if (modalPago) bootstrap.Modal.getInstance(modalPago)?.hide();
  window.setTimeout(() => codigo?.focus(), 180);
}

function finalizarVentaExitosa(respuesta) {
  if (respuesta.pdf_url) window.open(respuesta.pdf_url, "_blank");
  limpiarCajaDespuesDeVenta();
}

function enviarVenta(data, tipoPago, cantidadDinero) {
  // ======================================================
  // BLOQUEAR DOBLE ENVÍO
  // ======================================================

  if (ventaEnProceso) {
    return;
  }

  ventaEnProceso = true;

  // ------------------------------------------------------
  // BLOQUEAR BOTONES
  // ------------------------------------------------------

  const botonFormulario = document.getElementById("btnPagar");

  const botonCaja = document.getElementById("Pagar");

  if (botonFormulario) {
    botonFormulario.disabled = true;
    botonFormulario.innerText = "Procesando venta...";
  }

  if (botonCaja) {
    botonCaja.disabled = true;
  }

  // ------------------------------------------------------
  // CSRF
  // ------------------------------------------------------

  const csrf = document.querySelector("[name=csrfmiddlewaretoken]");

  if (!csrf) {
    ventaEnProceso = false;

    if (botonFormulario) {
      botonFormulario.disabled = false;
      botonFormulario.innerText = "Realizar compra";
    }

    if (botonCaja) {
      botonCaja.disabled = false;
    }

    mensaje("No se encontró el token CSRF", "error", "");

    return;
  }

  // ======================================================
  // ENVIAR
  // ======================================================

  fetch("/manager/realizar_venta/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrf.value,
    },
    body: JSON.stringify(data),
  })
    .then(async (response) => {
      const respuesta = await response.json();

      if (!response.ok) {
        throw new Error(
          respuesta.error ||
            respuesta.message ||
            "Ocurrió un error al realizar la venta",
        );
      }

      return respuesta;
    })
    .then((data) => {
      // ==================================================
      // CONTADO
      // ==================================================

      if (tipoPago === "pago_contado") {
        const cambio = (
          Number(cantidadDinero || 0) - parseFloat(pagos[0].total)
        ).toFixed(2);

        Swal.fire({
          title: "Venta realizada",
          html: `
                    <b>Cambio:</b> L. ${cambio}
                `,
          icon: "success",
          confirmButtonText: "Aceptar",
          allowOutsideClick: false,
          allowEscapeKey: false,
          customClass: {
            confirmButton: "classbotones",
          },
        }).then(() => {
          finalizarVentaExitosa(data);
        });

        // ==================================================
        // DEPÓSITO BANCARIO
        // ==================================================
      } else if (tipoPago === "pago_deposito") {
        Swal.fire({
          title: "Venta realizada",
          html: `
                    <b>Factura:</b> ${data.numero_factura}
                    <br>
                    <b>Depósito bancario registrado correctamente</b>
                `,
          icon: "success",
          confirmButtonText: "Aceptar",
          allowOutsideClick: false,
          allowEscapeKey: false,
          customClass: { confirmButton: "classbotones" },
        }).then(() => {
          finalizarVentaExitosa(data);
        });

        // ==================================================
        // CHEQUE
        // ==================================================
      } else if (tipoPago === "pago_cheque") {
        Swal.fire({
          title: "Venta realizada",
          html: `
                    <b>Factura:</b> ${data.numero_factura}
                    <br>
                    <b>Pago con cheque registrado correctamente</b>
                `,
          icon: "success",
          confirmButtonText: "Aceptar",
          allowOutsideClick: false,
          allowEscapeKey: false,
          customClass: { confirmButton: "classbotones" },
        }).then(() => {
          finalizarVentaExitosa(data);
        });

        // ==================================================
        // TARJETA
        // ==================================================
      } else if (tipoPago === "pago_tarjeta") {
        Swal.fire({
          title: "Venta realizada",
          html: `
                    <b>Factura:</b>
                    ${data.numero_factura}
                    <br>
                    <b>Pago con tarjeta registrado correctamente</b>
                `,
          icon: "success",
          confirmButtonText: "Aceptar",
          allowOutsideClick: false,
          allowEscapeKey: false,
          customClass: {
            confirmButton: "classbotones",
          },
        }).then(() => {
          finalizarVentaExitosa(data);
        });

        // ==================================================
        // CRÉDITO
        // ==================================================
      } else {
        Swal.fire({
          title: "Venta a crédito realizada",
          html: `
                    <b>Factura:</b>
                    ${data.numero_factura}
                    <br>
                    <b>La cuenta por cobrar fue creada correctamente</b>
                `,
          icon: "success",
          confirmButtonText: "Aceptar",
          allowOutsideClick: false,
          allowEscapeKey: false,
          customClass: {
            confirmButton: "classbotones",
          },
        }).then(() => {
          finalizarVentaExitosa(data);
        });
      }
    })
    .catch((error) => {
      // ==================================================
      // ERROR: PERMITIR REINTENTAR
      // ==================================================

      ventaEnProceso = false;

      if (botonFormulario) {
        botonFormulario.disabled = false;
        botonFormulario.innerText = "Realizar compra";
      }

      if (botonCaja) {
        botonCaja.disabled = false;
      }

      mensaje(error.message, "error", "");
    });
}

// ==========================================================
// BOTÓN PAGAR
// ==========================================================

const btnPagar = document.getElementById("Pagar");

if (btnPagar) {
  btnPagar.addEventListener("click", function (e) {
    if (this.disabled || ventaEnProceso) {
      e.preventDefault();
      return;
    }

    const modalElement = document.getElementById("modalPago");

    if (!modalElement) {
      return;
    }

    const modal = bootstrap.Modal.getOrCreateInstance(modalElement);

    modal.show();
  });
}

// ==========================================================
// CAMBIO DE TIPO DE PAGO
// ==========================================================

const tipoPagoSelect = document.getElementById("tipo_pago");

if (tipoPagoSelect) {
  tipoPagoSelect.addEventListener("change", function (e) {
    const opcion = e.target.value;

    const dinero = document.getElementById("div_dinero");

    const numero = document.getElementById("div_nuemro");

    const digito = document.getElementById("div_digito");

    // ------------------------------------------------
    // PAGO CONTADO
    // ------------------------------------------------

    if (opcion === "pago_contado" || opcion === "pago_deposito") {
      if (dinero) dinero.style.display = "block";

      if (numero) numero.style.display = "none";

      if (digito) digito.style.display = "none";

      // ------------------------------------------------
      // PAGO CON CHEQUE
      // ------------------------------------------------
    } else if (opcion === "pago_cheque") {
      if (dinero) dinero.style.display = "none";

      if (numero) numero.style.display = "none";

      if (digito) digito.style.display = "none";

      // ------------------------------------------------
      // PAGO TARJETA
      // ------------------------------------------------
    } else if (opcion === "pago_tarjeta") {
      if (dinero) dinero.style.display = "none";

      if (numero) numero.style.display = "block";

      if (digito) digito.style.display = "block";

      // ------------------------------------------------
      // PAGO A CRÉDITO
      // ------------------------------------------------
    } else if (opcion === "pago_credito") {
      if (dinero) dinero.style.display = "none";

      if (numero) numero.style.display = "none";

      if (digito) digito.style.display = "none";

      // ------------------------------------------------
      // SIN SELECCION
      // ------------------------------------------------
    } else {
      if (dinero) dinero.style.display = "none";

      if (numero) numero.style.display = "none";

      if (digito) digito.style.display = "none";
    }
  });
}

// ==========================================================
// MENSAJES
// ==========================================================

function mensaje(texto, tipo, funcion) {
  Swal.fire({
    title: texto,

    icon: tipo,

    confirmButtonText: "Aceptar",

    customClass: {
      confirmButton: "classbotones",
    },
  }).then(() => {
    if (typeof funcion === "function") {
      funcion();
    }
  });
}

// ==========================================================
// APERTURA DE CAJA
// ==========================================================

const btnAbrirCaja = document.getElementById("btnAbrirCaja");

if (btnAbrirCaja) {
  btnAbrirCaja.addEventListener("click", function () {
    const montoInput = document.getElementById("monto_apertura");

    if (!montoInput) {
      return;
    }

    const monto = montoInput.value.trim();

    const url = btnAbrirCaja.dataset.url;

    if (!monto || parseFloat(monto) < 0) {
      Swal.fire({
        icon: "warning",

        title: "Monto inválido",

        text: "Ingrese un monto válido para abrir la caja.",

        confirmButtonText: "Aceptar",

        customClass: {
          confirmButton: "classbotones",
        },
      });

      return;
    }

    const csrf = document.querySelector("[name=csrfmiddlewaretoken]");

    if (!csrf) {
      mensaje("No se encontró el token CSRF", "error", "");

      return;
    }

    const formData = new FormData();

    formData.append("monto_apertura", monto);

    btnAbrirCaja.disabled = true;

    fetch(url, {
      method: "POST",

      headers: {
        "X-CSRFToken": csrf.value,
      },

      body: formData,
    })
      .then((response) => response.json())

      .then((data) => {
        if (data.ok) {
          Swal.fire({
            icon: "success",

            title: "Caja abierta",

            text: data.mensaje,

            confirmButtonText: "Continuar",

            customClass: {
              confirmButton: "classbotones",
            },
          }).then(() => {
            const modalElement = document.getElementById("modalAperturaCaja");

            if (modalElement) {
              const modal = bootstrap.Modal.getInstance(modalElement);

              if (modal) {
                modal.hide();
              }
            }

            montoInput.value = "";

            actualizarAccionesPorCaja(true);

            location.reload();
          });
        } else {
          Swal.fire({
            icon: "warning",

            title: "No se pudo abrir la caja",

            text: data.mensaje,

            confirmButtonText: "Aceptar",

            customClass: {
              confirmButton: "classbotones",
            },
          });
        }
      })

      .catch((error) => {
        console.error("Error:", error);

        Swal.fire({
          icon: "error",

          title: "Error",

          text: "Ocurrió un error al abrir la caja.",

          confirmButtonText: "Aceptar",

          customClass: {
            confirmButton: "classbotones",
          },
        });
      })

      .finally(() => {
        btnAbrirCaja.disabled = false;
      });
  });
}

// ==========================================================
// CIERRE DE CAJA
// ==========================================================

const btnCierreCaja = document.getElementById("btnCierreCaja");

if (btnCierreCaja) {
  btnCierreCaja.addEventListener("click", function (e) {
    if (this.disabled) {
      e.preventDefault();

      return;
    }

    Swal.fire({
      icon: "warning",

      title: "¿Iniciar cierre de caja?",

      text: "La caja pasará al proceso de cuadre.",

      showCancelButton: true,

      confirmButtonText: "Sí, continuar",

      cancelButtonText: "Cancelar",

      customClass: {
        confirmButton: "classbotones",
      },
    }).then((result) => {
      if (!result.isConfirmed) {
        return;
      }

      const csrf = document.querySelector("[name=csrfmiddlewaretoken]");

      if (!csrf) {
        mensaje("No se encontró el token CSRF", "error", "");

        return;
      }

      fetch(btnCierreCaja.dataset.url, {
        method: "POST",

        headers: {
          "X-CSRFToken": csrf.value,
        },
      })
        .then((response) => response.json())

        .then((data) => {
          if (data.ok) {
            Swal.fire({
              icon: "success",

              title: "Cuadre iniciado",

              text: "Serás dirigido al cuadre de caja.",

              confirmButtonText: "Continuar",

              customClass: {
                confirmButton: "classbotones",
              },
            }).then(() => {
              window.location.href = data.redirect_url;
            });
          } else {
            Swal.fire({
              icon: "error",

              title: "Error",

              text: data.mensaje,

              customClass: {
                confirmButton: "classbotones",
              },
            });
          }
        })

        .catch((error) => {
          console.error(error);

          Swal.fire({
            icon: "error",

            title: "Error",

            text: "Ocurrió un problema al iniciar el cuadre.",

            customClass: {
              confirmButton: "classbotones",
            },
          });
        });
    });
  });
}

// Mantiene sincronizados los controles de Caja al cargar la vista y justo
// después de abrirla, sin depender de que el navegador conserve atributos viejos.
function actualizarAccionesPorCaja(cajaAbierta) {
  const accionesCaja = document.getElementById("accionesCaja");
  if (!accionesCaja) return;

  accionesCaja.dataset.cajaAbierta = cajaAbierta ? "true" : "false";
  accionesCaja
    .querySelectorAll("[data-requiere-caja-abierta]")
    .forEach((boton) => {
      boton.disabled = !cajaAbierta;
      if (cajaAbierta) {
        boton.removeAttribute("title");
      } else if (!boton.title) {
        boton.title = "La caja debe estar abierta para usar esta acción";
      }
    });
}

document.addEventListener("DOMContentLoaded", () => {
  const accionesCaja = document.getElementById("accionesCaja");
  if (accionesCaja) {
    actualizarAccionesPorCaja(accionesCaja.dataset.cajaAbierta === "true");
  }
});

// Selector de productos para escritorio, tableta y teléfono. Reutiliza
// sin_codigo(), por lo que conserva las validaciones de existencias, impuestos
// y descuentos de Caja.
(() => {
  const form = document.getElementById("buscarProductosMovilForm");
  const input = document.getElementById("buscarProductosMovil");
  const lista = document.getElementById("listaProductosMovil");
  const paginas = document.getElementById("paginacionProductosMovil");
  const boton = document.getElementById("agregarProductosMovil");
  const contenidoModal = document.querySelector(
    "#modalProductosMovil .modal-content",
  );
  const seleccionados = new Set();
  if (!form || !lista || !paginas || !boton) return;
  let busqueda = "";

  const truncarExistencia = (valor) => {
    const texto = String(valor ?? "0").trim().replace(",", ".");
    const [entero, decimales = ""] = texto.split(".");
    return decimales ? `${entero}.${decimales.slice(0, 2)}` : entero;
  };

  const actualizarListaConAnimacion = (contenido) => {
    const alturaInicial = lista.getBoundingClientRect().height;
    const alturaModalInicial = contenidoModal?.getBoundingClientRect().height || 0;
    lista.style.height = alturaInicial ? `${alturaInicial}px` : "";
    if (alturaModalInicial) {
      contenidoModal.style.height = `${alturaModalInicial}px`;
    }
    lista.innerHTML = contenido;

    // Medimos la altura natural sin el alto anterior fijado. Si conservamos el
    // alto grande, scrollHeight también sería grande y el modal no se encogería.
    lista.style.height = "auto";
    const alturaFinal = Math.min(lista.getBoundingClientRect().height, 390);
    lista.style.height = alturaInicial ? `${alturaInicial}px` : "";
    if (!alturaInicial) {
      lista.style.height = "";
      contenidoModal?.style.removeProperty("height");
      return;
    }

    requestAnimationFrame(() => {
      lista.style.height = `${alturaFinal}px`;
      if (alturaModalInicial) {
        const diferencia = alturaFinal - alturaInicial;
        contenidoModal.style.height = `${alturaModalInicial + diferencia}px`;
      }
      const terminarTransicion = (evento) => {
        if (evento.propertyName !== "height") return;
        lista.style.height = "";
        contenidoModal?.style.removeProperty("height");
        lista.removeEventListener("transitionend", terminarTransicion);
      };
      lista.addEventListener("transitionend", terminarTransicion);
    });
  };

  const cargar = async (pagina = 1) => {
    if (!lista.children.length) {
      lista.innerHTML = '<div class="text-center py-4">Cargando productos...</div>';
    }
    lista.classList.add("is-loading");
    const url = new URL("/manager/api/caja/productos/", window.location.origin);
    url.searchParams.set("page", pagina);
    url.searchParams.set("limit", 10);
    if (busqueda) url.searchParams.set("search", busqueda);
    try {
      const respuesta = await fetch(url);
      const data = await respuesta.json();
      actualizarListaConAnimacion(
        data.results
          .map(
            (p) =>
              `<article class="caja-product-option ${seleccionados.has(p.codigoSKU) ? "seleccionado" : ""}" data-codigo="${p.codigoSKU}"><img class="caja-product-option__image" src="${p.imagenUrl || "/static/img/default.png"}" onerror="this.src='/static/img/default.png'"><div class="caja-product-option__info"><strong>${p.nombre}</strong><small>Existencia: ${truncarExistencia(p.stock)} ${p.unidad || ""}</small></div><span class="caja-product-option__action"><i class="bx ${seleccionados.has(p.codigoSKU) ? "bx-check-circle" : "bx-plus-circle"}"></i> ${seleccionados.has(p.codigoSKU) ? "Seleccionado" : "Seleccionar"}</span></article>`,
          )
          .join("") ||
          '<p class="text-center py-4">No se encontraron productos disponibles.</p>',
      );
      lista.classList.remove("is-loading");
      lista.querySelectorAll("[data-codigo]").forEach(
        (item) =>
          (item.onclick = () => {
            const codigo = item.dataset.codigo;
            seleccionados.has(codigo)
              ? seleccionados.delete(codigo)
              : seleccionados.add(codigo);
            item.classList.toggle("seleccionado", seleccionados.has(codigo));
            const accion = item.querySelector(".caja-product-option__action");
            accion.innerHTML = `<i class="bx ${seleccionados.has(codigo) ? "bx-check-circle" : "bx-plus-circle"}"></i> ${seleccionados.has(codigo) ? "Seleccionado" : "Seleccionar"}`;
          }),
      );
      const inicioPagina = Math.max(1, pagina - 2);
      const finPagina = Math.min(data.totalPages, pagina + 2);
      const paginasNumeradas = Array.from(
        { length: finPagina - inicioPagina + 1 },
        (_, indice) => {
          const numeroPagina = inicioPagina + indice;
          return `<li class="page-item ${numeroPagina === pagina ? "active" : ""}"><button class="page-link" data-page="${numeroPagina}">${numeroPagina}</button></li>`;
        },
      ).join("");
      paginas.innerHTML = `<li class="page-item ${pagina <= 1 ? "disabled" : ""}"><button class="page-link" data-page="${pagina - 1}">«</button></li>${paginasNumeradas}<li class="page-item ${pagina >= data.totalPages ? "disabled" : ""}"><button class="page-link" data-page="${pagina + 1}">»</button></li>`;
      paginas
        .querySelectorAll("[data-page]")
        .forEach((b) =>
          (b.onclick = () => {
            if (!b.closest(".page-item")?.classList.contains("disabled")) {
              cargar(Number(b.dataset.page));
            }
          }),
        );
    } catch {
      actualizarListaConAnimacion(
        '<p class="text-center text-danger py-4">No fue posible cargar los productos.</p>',
      );
      lista.classList.remove("is-loading");
    }
  };
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    busqueda = input.value.trim();
    cargar(1);
  });
  document
    .getElementById("modalProductosMovil")
    .addEventListener("shown.bs.modal", () => {
      busqueda = "";
      input.value = "";
      cargar(1);
      input.focus();
    });
  boton.onclick = () => {
    seleccionados.forEach((codigo) => productos(codigo));
    seleccionados.clear();
    bootstrap.Modal.getInstance(
      document.getElementById("modalProductosMovil"),
    ).hide();
  };
})();
