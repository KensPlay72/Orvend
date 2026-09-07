// ==========================================================
// CAJA - SECCIÓN 1
// PRODUCTOS, BÚSQUEDA, MODAL Y TABLA
// ==========================================================

// ----------------------------------------------------------
// VARIABLES GLOBALES
// ----------------------------------------------------------

let datos = [];

let productos_dato = [];

let pagos = [];

let tarjetas = [];

let fila_descuento = null;

let total_m = 0;

let clienteBusquedaControlador = null;

let clienteSeleccionado = null;

let controlador = null;

let codex = 0;


// ==========================================================
// BUSQUEDA POR CODIGO
// ==========================================================

const codigoBusqueda = document.getElementById("codigo_busqueda");

if (codigoBusqueda) {

    codigoBusqueda.addEventListener("keydown", function (event) {

        if (event.key === "Enter") {

            event.preventDefault();

            const codigo = codigoBusqueda.value.trim();

            if (codigo === "" || isNaN(codigo)) {

                mensaje(
                    "Ingrese un codigo válido",
                    "error",
                    ""
                );

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

    if (
        codigo === "" ||
        !Number.isInteger(Number(codigo))
    ) {

        console.log("Codigo no valido");

        return;
    }

    const producto = datos.findIndex(
        p => p.codigo === codigo
    );

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

    const stockReal =
        parseFloat(datos[i].stock) || 0;


    // ------------------------------------------------------
    // STOCK VENDIBLE
    //
    // Ejemplo:
    // 6.83 -> 6
    // 7.50 -> 7
    // 10.00 -> 10
    // ------------------------------------------------------

    const stockVendible =
        Math.floor(stockReal);


    // ------------------------------------------------------
    // VALIDAR STOCK
    // ------------------------------------------------------

    if (
        datos[i].cantidad + 1 >
        stockVendible
    ) {

        mensaje(
            `No puede vender más de ${stockVendible} unidades. Existencia real: ${stockReal}`,
            "error",
            ""
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

    if (
        datos[i].estado === 1
    ) {

        descuento_cantidad(i);
    }


    // ------------------------------------------------------
    // SUBTOTAL
    // ------------------------------------------------------

    datos[i].subtotal =
        datos[i].cantidad *
        datos[i].precio_venta;


    // ------------------------------------------------------
    // ISV
    // ------------------------------------------------------

    datos[i].isv15_acumulable +=
        datos[i].isv_15;


    datos[i].isv18_acumulable +=
        datos[i].isv_18;


    // ------------------------------------------------------
    // ACTUALIZAR TABLA
    // ------------------------------------------------------

    const tabla =
        document.getElementById(
            "tablaProductos"
        );


    if (!tabla) {
        return;
    }


    const fila =
        tabla.rows[i + 1];


    if (!fila) {
        return;
    }


    const cantidad =
        fila.cells[2]?.querySelector(
            ".pre"
        );


    const subtotal =
        fila.cells[5];


    const descuento =
        fila.cells[4];


    // ------------------------------------------------------
    // CANTIDAD
    // ------------------------------------------------------

    if (cantidad) {

        cantidad.textContent =
            `${datos[i].cantidad} / ${datos[i].stock}`;
    }


    // ------------------------------------------------------
    // SUBTOTAL
    // ------------------------------------------------------

    if (subtotal) {

        subtotal.textContent =
            "L. " +
            datos[i].subtotal.toFixed(2);
    }


    // ------------------------------------------------------
    // DESCUENTO
    // ------------------------------------------------------

    if (descuento) {

        descuento.textContent =
            "L. " +
            datos[i].descuento.toFixed(2);
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
            `/manager/busquedacodigo/${codigo}/`,
            {
                method: "GET",
                headers: {}
            }
        );


        if (!response.ok) {

            const dato = await response.json();

            throw new Error(
                dato.error ||
                dato.mensaje ||
                "Error desconocido"
            );
        }


        const data = await response.json();


        let imp15 = 0;
        let imp18 = 0;


        if (parseFloat(data.tipos_isv) === 15) {

            imp15 = parseFloat(data.isv) || 0;

        } else if (parseFloat(data.tipos_isv) === 18) {

            imp18 = parseFloat(data.isv) || 0;
        }


        const producto = {

            id: data.id,

            codigo: data.codigo_sku,

            nombre: data.nombre,

            precio_venta:
                parseFloat(data.precio_venta) || 0,

            stock:
                parseFloat(data.stock) || 0,

            cantidad: 1,

            descuento:
                parseFloat(data.descuentos) || 0,

            subtotal:
                parseFloat(data.precio_venta) || 0,

            valor_descuento:
                parseFloat(data.descuentos) || 0,

            acumulable:
                data.acumulable,

            estado: 1,

            isv_15: imp15,

            isv_18: imp18,

            isv15_acumulable: imp15,

            isv18_acumulable: imp18,

            lleva:
                parseInt(data.lleva) || 0,

            paga:
                parseInt(data.paga) || 0,

            restarlleva: 0
        };


        datos.push(producto);


        tabla_codigo(

            data.codigo_sku,

            data.nombre,

            1,

            parseFloat(data.precio_venta).toFixed(2),

            parseFloat(data.descuentos).toFixed(2),

            parseFloat(data.precio_venta).toFixed(2)
        );


        tabla_detalle_total();


    } catch (error) {

        mensaje(
            error.message,
            "error",
            ""
        );
    }
}


// ==========================================================
// BUSQUEDA POR NOMBRE
// ==========================================================

const busqueda =
    document.getElementById("busqueda");

const resultados =
    document.getElementById("resultadoBusquda");


if (busqueda && resultados) {


    // ------------------------------------------------------
    // EVITAR SUBMIT CON ENTER
    // ------------------------------------------------------

    busqueda.addEventListener(
        "keydown",
        function (event) {

            if (event.key === "Enter") {

                event.preventDefault();
            }
        }
    );


    // ------------------------------------------------------
    // EVENTO BUSQUEDA
    // ------------------------------------------------------

    busqueda.addEventListener(
        "input",
        function () {

            resultados.innerHTML = "";

            resultados.style.display = "none";


            const texto =
                busqueda.value.trim();


            if (texto.length < 2) {

                return;
            }


            if (controlador) {

                controlador.abort();
            }


            controlador =
                new AbortController();


            fetch(
                `/manager/busquedanombre/${texto}/`,
                {
                    method: "GET",
                    signal: controlador.signal
                }
            )
                .then(async response => {

                    if (!response.ok) {

                        const dato =
                            await response.json();

                        throw new Error(
                            dato.error ||
                            "Error al buscar productos"
                        );
                    }

                    return response.json();
                })

                .then(data => {

                    productos_dato = [];

                    resultados.innerHTML = "";


                    if (data.length > 0) {

                        resultados.style.display =
                            "block";


                        data.forEach(
                            (p, index) => {

                                productos_dato.push(p);


                                const div =
                                    document.createElement("div");


                                div.className =
                                    "item-resultado";


                                div.textContent =
                                    `${p.nombre} | Existencia: ${p.stock}`;


                                div.addEventListener(
                                    "click",
                                    () => {

                                        seleccionarProducto(index);
                                    }
                                );


                                resultados.appendChild(div);
                            }
                        );


                    } else {

                        resultados.style.display =
                            "block";


                        resultados.innerHTML = `
                            <div class="item-resultado">
                                Sin existencia en esta sucursal
                            </div>
                        `;
                    }
                })

                .catch(error => {

                    if (
                        error.name !==
                        "AbortError"
                    ) {

                        mensaje(
                            error.message,
                            "error",
                            ""
                        );
                    }
                });
        }
    );
}


// ==========================================================
// PRODUCTO SELECCIONADO
// ==========================================================

function seleccionarProducto(index) {

    codex = index;

    const producto = productos_dato[index];

    if (!producto) {

        mensaje(
            "No se encontró el producto seleccionado",
            "error",
            ""
        );

        return;
    }


    const codigo =
        document.getElementById("nCodigo");

    const nombre =
        document.getElementById("nNombre");

    const precio =
        document.getElementById("nPrecio");

    const cantidad =
        document.getElementById("nCanitdad");

    const existencia =
        document.getElementById("existenciaProducto");


    // ======================================================
    // OBTENER EXISTENCIA REAL
    // ======================================================

    const stock =
        parseFloat(producto.stock);


    if (isNaN(stock)) {

        console.error(
            "Stock inválido:",
            producto.stock,
            producto
        );

        mensaje(
            "La existencia del producto no es válida",
            "error",
            ""
        );

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

    const stockVendible =
        Math.floor(stock);


    // ======================================================
    // VERIFICAR SI EXISTE AL MENOS UNA UNIDAD
    // ======================================================

    if (stockVendible < 1) {

        mensaje(
            `No hay unidades completas disponibles. Existencia: ${stock}`,
            "error",
            ""
        );

        return;
    }


    // ======================================================
    // LLENAR MODAL
    // ======================================================

    if (codigo) {

        codigo.value =
            producto.codigo_sku;
    }


    if (nombre) {

        nombre.value =
            producto.nombre;
    }


    if (precio) {

        precio.value =
            "L. " +
            parseFloat(
                producto.precio_venta
            ).toFixed(2);
    }


    if (cantidad) {

        cantidad.value = 1;

        cantidad.min = 1;

        cantidad.max =
            stockVendible;
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

        existencia.value =
            `1 / ${stock}`;
    }


    // ======================================================
    // ABRIR MODAL
    // ======================================================

    const modalElement =
        document.getElementById(
            "modalagregar"
        );


    if (!modalElement) {
        return;
    }


    const modal =
        bootstrap.Modal.getOrCreateInstance(
            modalElement
        );


    modal.show();
}
// ==========================================================
// CONTROL DE CANTIDAD DEL MODAL
// ==========================================================

const inputCantidad =
    document.getElementById(
        "nCanitdad"
    );


if (inputCantidad) {

    inputCantidad.addEventListener(
        "input",
        function () {

            const producto =
                productos_dato[codex];


            if (!producto) {
                return;
            }


            // ==================================================
            // STOCK REAL
            // ==================================================

            const stock =
                parseFloat(
                    producto.stock
                );


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

            const stockVendible =
                Math.floor(stock);


            // ==================================================
            // CANTIDAD INGRESADA
            // ==================================================

            let cantidad =
                parseInt(
                    this.value,
                    10
                );


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

            if (
                cantidad >
                stockVendible
            ) {

                cantidad =
                    stockVendible;


                mensaje(
                    `La cantidad máxima que puede vender es ${stockVendible}. Existencia real: ${stock}`,
                    "error",
                    ""
                );
            }


            // ==================================================
            // ACTUALIZAR INPUT
            // ==================================================

            this.value =
                cantidad;


            // ==================================================
            // ACTUALIZAR EXISTENCIA
            //
            // IMPORTANTE:
            // Es un INPUT -> .value
            // ==================================================

            const existencia =
                document.getElementById(
                    "existenciaProducto"
                );


            if (existencia) {

                existencia.value =
                    `${cantidad} / ${stock}`;
            }
        }
    );
}



// ==========================================================
// AGREGAR PRODUCTO DESDE MODAL
// ==========================================================

const btnRegis =
    document.getElementById("btnregis");


if (btnRegis) {

    btnRegis.addEventListener(
        "click",
        function (e) {

            e.preventDefault();


            // ------------------------------------------------
            // OBTENER INPUTS
            // ------------------------------------------------

            const codigoInput =
                document.getElementById(
                    "nCodigo"
                );


            const cantidadInput =
                document.getElementById(
                    "nCanitdad"
                );


            if (
                !codigoInput ||
                !cantidadInput
            ) {

                return;
            }


            // ------------------------------------------------
            // CODIGO
            // ------------------------------------------------

            const codigo =
                codigoInput.value.trim();


            // ------------------------------------------------
            // CANTIDAD
            // ------------------------------------------------

            const cantidad =
                parseInt(
                    cantidadInput.value,
                    10
                );


            // ------------------------------------------------
            // VALIDAR CANTIDAD
            // ------------------------------------------------

            if (
                isNaN(cantidad) ||
                cantidad <= 0
            ) {

                mensaje(
                    "La cantidad debe ser mayor que 0",
                    "error",
                    ""
                );

                return;
            }


            // ------------------------------------------------
            // PRODUCTO SELECCIONADO
            // ------------------------------------------------

            const productoSeleccionado =
                productos_dato[codex];


            if (!productoSeleccionado) {

                mensaje(
                    "No se encontró el producto seleccionado",
                    "error",
                    ""
                );

                return;
            }


            // ------------------------------------------------
            // STOCK REAL
            // ------------------------------------------------

            const stockReal =
                parseFloat(
                    productoSeleccionado.stock
                ) || 0;


            // ------------------------------------------------
            // STOCK VENDIBLE
            //
            // 6.83 -> 6
            // 7.50 -> 7
            // 10.00 -> 10
            // ------------------------------------------------

            const stockVendible =
                Math.floor(stockReal);


            // ------------------------------------------------
            // VALIDAR STOCK DEL PRODUCTO
            // ------------------------------------------------

            if (
                cantidad >
                stockVendible
            ) {

                mensaje(
                    `La cantidad máxima que puede vender es ${stockVendible}. Existencia real: ${stockReal}`,
                    "error",
                    ""
                );

                return;
            }


            // ------------------------------------------------
            // BUSCAR SI YA ESTÁ EN LA TABLA
            // ------------------------------------------------

            const producto =
                datos.findIndex(
                    p =>
                        p.codigo ===
                        codigo
                );


            // =================================================
            // PRODUCTO NO EXISTE EN LA TABLA
            // =================================================

            if (
                producto === -1
            ) {

                let imp15 = 0;

                let imp18 = 0;


                // ------------------------------------------------
                // ISV 15
                // ------------------------------------------------

                if (
                    parseFloat(
                        productoSeleccionado.tipos_isv
                    ) === 15
                ) {

                    imp15 =
                        parseFloat(
                            productoSeleccionado.isv
                        ) || 0;
                }


                // ------------------------------------------------
                // ISV 18
                // ------------------------------------------------

                else if (
                    parseFloat(
                        productoSeleccionado.tipos_isv
                    ) === 18
                ) {

                    imp18 =
                        parseFloat(
                            productoSeleccionado.isv
                        ) || 0;
                }


                // ------------------------------------------------
                // PRECIO
                // ------------------------------------------------

                const precio =
                    parseFloat(
                        productoSeleccionado.precio_venta
                    ) || 0;


                // ------------------------------------------------
                // DESCUENTO
                // ------------------------------------------------

                const descuentoBase =
                    parseFloat(
                        productoSeleccionado.descuento
                    ) || 0;


                // ------------------------------------------------
                // CREAR PRODUCTO
                // ------------------------------------------------

                let producto_b = {

                    id:
                        productoSeleccionado.id,

                    codigo:
                        productoSeleccionado.codigo_sku,

                    nombre:
                        productoSeleccionado.nombre,

                    precio_venta:
                        precio,

                    stock:
                        stockReal,

                    cantidad:
                        cantidad,

                    descuento:
                        descuentoBase *
                        cantidad,

                    subtotal:
                        precio *
                        cantidad,

                    valor_descuento:
                        descuentoBase,

                    acumulable:
                        productoSeleccionado.es_acumulable,

                    estado:
                        1,

                    lleva:
                        parseInt(
                            productoSeleccionado.lleva
                        ) || 0,

                    paga:
                        parseInt(
                            productoSeleccionado.paga
                        ) || 0,

                    restarlleva:
                        0,

                    isv_15:
                        imp15,

                    isv_18:
                        imp18,

                    isv15_acumulable:
                        imp15 *
                        cantidad,

                    isv18_acumulable:
                        imp18 *
                        cantidad
                };


                // ------------------------------------------------
                // PROMOCION LLEVA / PAGA
                // ------------------------------------------------

                if (
                    producto_b.lleva > 0
                ) {

                    if (
                        cantidad >=
                        producto_b.lleva
                    ) {

                        const grupos =
                            Math.floor(
                                cantidad /
                                producto_b.lleva
                            );


                        producto_b.descuento +=
                            producto_b.precio_venta *
                            (
                                producto_b.lleva -
                                producto_b.paga
                            ) *
                            grupos;


                        if (
                            cantidad %
                            producto_b.lleva ===
                            0
                        ) {

                            producto_b.restarlleva =
                                1;
                        }
                    }
                }


                // ------------------------------------------------
                // AGREGAR A DATOS
                // ------------------------------------------------

                datos.push(
                    producto_b
                );


                // ------------------------------------------------
                // AGREGAR A TABLA
                // ------------------------------------------------

                tabla_codigo(

                    productoSeleccionado.codigo_sku,

                    productoSeleccionado.nombre,

                    cantidad,

                    precio.toFixed(2),

                    producto_b.descuento.toFixed(2),

                    (
                        precio *
                        cantidad
                    ).toFixed(2)
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

            const cantidadActual =
                parseInt(
                    datos[producto].cantidad,
                    10
                ) || 0;


            // ------------------------------------------------
            // NUEVA CANTIDAD
            // ------------------------------------------------

            const nuevaCantidad =
                cantidadActual +
                cantidad;


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

            if (
                nuevaCantidad >
                stockVendible
            ) {

                mensaje(
                    `No puede vender más de ${stockVendible} unidades. Existencia real: ${stockReal}. Actualmente tiene ${cantidadActual} unidades en la venta.`,
                    "error",
                    ""
                );

                return;
            }


            // ------------------------------------------------
            // ACTUALIZAR CANTIDAD
            // ------------------------------------------------

            datos[producto].cantidad =
                nuevaCantidad;


            // ------------------------------------------------
            // DESCUENTO
            // ------------------------------------------------

            if (
                datos[producto].estado === 1
            ) {

                descuento_cantidad(
                    producto
                );
            }


            // ------------------------------------------------
            // SUBTOTAL
            // ------------------------------------------------

            datos[producto].subtotal =
                datos[producto].cantidad *
                datos[producto].precio_venta;


            // ------------------------------------------------
            // ISV
            // ------------------------------------------------

            datos[producto].isv15_acumulable +=
                datos[producto].isv_15 *
                cantidad;


            datos[producto].isv18_acumulable +=
                datos[producto].isv_18 *
                cantidad;


            // ------------------------------------------------
            // OBTENER TABLA
            // ------------------------------------------------

            const tabla =
                document.getElementById(
                    "tablaProductos"
                );


            if (!tabla) {
                return;
            }


            const fila =
                tabla.rows[
                    producto + 1
                ];


            if (fila) {

                const c =
                    fila.querySelector(
                        ".pre"
                    );


                const s =
                    fila.cells[5];


                const d =
                    fila.cells[4];


                // --------------------------------------------
                // CANTIDAD
                // --------------------------------------------

                if (c) {

                    c.textContent =
                        `${datos[producto].cantidad} / ${datos[producto].stock}`;
                }


                // --------------------------------------------
                // SUBTOTAL
                // --------------------------------------------

                if (s) {

                    s.textContent =
                        "L. " +
                        datos[producto]
                            .subtotal
                            .toFixed(2);
                }


                // --------------------------------------------
                // DESCUENTO
                // --------------------------------------------

                if (d) {

                    d.textContent =
                        "L. " +
                        datos[producto]
                            .descuento
                            .toFixed(2);
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
        }
    );
}

// ==========================================================
// CERRAR MODAL PRODUCTO
// ==========================================================

function cerrarModalProducto() {

    const modalElement =
        document.getElementById(
            "modalagregar"
        );


    if (modalElement) {

        const modal =
            bootstrap.Modal.getOrCreateInstance(
                modalElement
            );

        modal.hide();
    }


    const cantidad =
        document.getElementById(
            "nCanitdad"
        );


    if (cantidad) {

        cantidad.value = 1;
    }
}


// ==========================================================
// CERRAR RESULTADOS DE BUSQUEDA
// ==========================================================

if (busqueda && resultados) {

    busqueda.addEventListener(
        "blur",
        function () {

            setTimeout(() => {

                resultados.style.display =
                    "none";

                resultados.innerHTML = "";

            }, 300);
        }
    );


    busqueda.addEventListener(
        "focus",
        function () {

            if (
                busqueda.value.length < 2
            ) {

                resultados.innerHTML = `
                    <div class="item-resultado">
                        ______________________
                        <br>
                        Sin Resultados
                    </div>
                `;

                resultados.style.display =
                    "block";
            }


            setTimeout(() => {

                resultados.style.display =
                    "block";

            }, 200);
        }
    );
}


// ==========================================================
// CREAR FILA EN TABLA
// ==========================================================

function tabla_codigo(
    codigo,
    nombre,
    canti,
    sub,
    des,
    total
) {

    const tabla =
        document.querySelector(
            "#tablaProductos tbody"
        );


    if (!tabla) {

        console.error(
            "No existe #tablaProductos tbody"
        );

        return;
    }


    const fila =
        tabla.insertRow();


    fila.insertCell(0)
        .textContent = codigo;


    fila.insertCell(1)
        .textContent = nombre;


    const cantidad =
        fila.insertCell(2);


    fila.insertCell(3)
        .textContent =
        "L. " + sub;


    fila.insertCell(4)
        .textContent =
        "L. " + des;


    fila.insertCell(5)
        .textContent =
        "L. " + total;


    const boton =
        fila.insertCell(6);


    // ------------------------------------------------------
    // CONTENEDOR CANTIDAD
    // ------------------------------------------------------

    const div_row =
        document.createElement("div");

    div_row.className =
        "div_row";


    const div_pre =
        document.createElement("div");


    const p =
        document.createElement("p");

    p.className =
        "pre";

    p.textContent =
        canti;


    div_pre.appendChild(p);


    // ------------------------------------------------------
    // BOTONES + -
    // ------------------------------------------------------

    const div_button_action =
        document.createElement("div");

    div_button_action.className =
        "button_action";


    const button_mas =
        document.createElement("button");

    button_mas.type =
        "button";

    button_mas.className =
        "btn_add";

    button_mas.textContent =
        "+";


    const button_men =
        document.createElement("button");

    button_men.type =
        "button";

    button_men.className =
        "btn_remove";

    button_men.textContent =
        "-";


    div_button_action.appendChild(
        button_mas
    );

    div_button_action.appendChild(
        button_men
    );


    div_row.appendChild(
        div_pre
    );

    div_row.appendChild(
        div_button_action
    );


    cantidad.appendChild(
        div_row
    );


    // ------------------------------------------------------
    // BOTON CUPON
    // ------------------------------------------------------

    const div_descuento =
        document.createElement("div");

    div_descuento.className =
        "button_action";


    const boton_descuento =
        document.createElement("button");

    boton_descuento.type =
        "button";

    boton_descuento.className =
        "btn_discunt";

    boton_descuento.textContent =
        "cupon";


    div_descuento.appendChild(
        boton_descuento
    );


    boton.appendChild(
        div_descuento
    );


    tabla_detalle_total();
}


// ==========================================================
// EVENTOS DE LA TABLA
// ==========================================================

const tbody =
    document.querySelector(
        "#tablaProductos tbody"
    );


if (tbody) {

    tbody.addEventListener(
        "click",
        function (e) {

            const fila =
                e.target.closest("tr");


            if (!fila) {
                return;
            }


            const indice =
                fila.sectionRowIndex;


            if (!datos[indice]) {
                return;
            }


            // ==================================================
            // BOTON +
            // ==================================================

            if (
                e.target.classList.contains(
                    "btn_add"
                )
            ) {

                const producto =
                    datos[indice];


                // ----------------------------------------------
                // STOCK REAL
                // ----------------------------------------------

                const stockReal =
                    parseFloat(
                        producto.stock
                    ) || 0;


                // ----------------------------------------------
                // STOCK VENDIBLE
                //
                // 6.83 -> 6
                // 7.99 -> 7
                // 10.00 -> 10
                // ----------------------------------------------

                const stockVendible =
                    Math.floor(
                        stockReal
                    );


                // ----------------------------------------------
                // VALIDAR
                // ----------------------------------------------

                if (
                    producto.cantidad + 1 >
                    stockVendible
                ) {

                    mensaje(
                        `No puede vender más de ${stockVendible} unidades. Existencia real: ${stockReal}`,
                        "error",
                        ""
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

                if (
                    producto.estado === 1
                ) {

                    descuento_cantidad(
                        indice
                    );
                }


                // ----------------------------------------------
                // SUBTOTAL
                // ----------------------------------------------

                producto.subtotal =
                    producto.cantidad *
                    producto.precio_venta;


                // ----------------------------------------------
                // ISV
                // ----------------------------------------------

                producto.isv15_acumulable +=
                    producto.isv_15;


                producto.isv18_acumulable +=
                    producto.isv_18;


                // ----------------------------------------------
                // ACTUALIZAR TABLA
                // ----------------------------------------------

                const c =
                    fila.querySelector(
                        ".pre"
                    );


                const s =
                    fila.cells[5];


                const d =
                    fila.cells[4];


                if (c) {

                    c.textContent =
                        `${producto.cantidad} / ${producto.stock}`;
                }


                if (s) {

                    s.textContent =
                        "L. " +
                        producto.subtotal
                            .toFixed(2);
                }


                if (d) {

                    d.textContent =
                        "L. " +
                        producto.descuento
                            .toFixed(2);
                }


                tabla_detalle_total();

                return;
            }


            // ==================================================
            // BOTON -
            // ==================================================

            if (
                e.target.classList.contains(
                    "btn_remove"
                )
            ) {

                const producto =
                    datos[indice];


                // ----------------------------------------------
                // DISMINUIR
                // ----------------------------------------------

                producto.cantidad--;


                // ----------------------------------------------
                // DESCUENTO
                // ----------------------------------------------

                if (
                    producto.estado === 1
                ) {

                    if (
                        producto.lleva > 0
                    ) {

                        if (
                            producto.cantidad %
                                producto.lleva !== 0 &&
                            producto.restarlleva === 1
                        ) {

                            producto.descuento -=
                                producto.precio_venta *
                                (
                                    producto.lleva -
                                    producto.paga
                                );


                            producto.restarlleva =
                                0;


                        } else if (
                            producto.cantidad %
                                producto.lleva === 0 &&
                            producto.restarlleva === 0
                        ) {

                            producto.restarlleva =
                                1;
                        }


                    } else {

                        producto.descuento -=
                            producto.valor_descuento;
                    }
                }


                // ----------------------------------------------
                // SUBTOTAL
                // ----------------------------------------------

                producto.subtotal =
                    producto.cantidad *
                    producto.precio_venta;


                // ----------------------------------------------
                // ISV
                // ----------------------------------------------

                producto.isv15_acumulable -=
                    producto.isv_15;


                producto.isv18_acumulable -=
                    producto.isv_18;


                // ----------------------------------------------
                // ELIMINAR SI LLEGA A CERO
                // ----------------------------------------------

                if (
                    producto.cantidad <= 0
                ) {

                    datos.splice(
                        indice,
                        1
                    );


                    fila.remove();


                    tabla_detalle_total();

                    return;
                }


                // ----------------------------------------------
                // ACTUALIZAR TABLA
                // ----------------------------------------------

                const c =
                    fila.querySelector(
                        ".pre"
                    );


                const s =
                    fila.cells[5];


                const d =
                    fila.cells[4];


                if (c) {

                    c.textContent =
                        `${producto.cantidad} / ${producto.stock}`;
                }


                if (s) {

                    s.textContent =
                        "L. " +
                        producto.subtotal
                            .toFixed(2);
                }


                if (d) {

                    d.textContent =
                        "L. " +
                        producto.descuento
                            .toFixed(2);
                }


                tabla_detalle_total();

                return;
            }


            // ==================================================
            // CUPON
            // ==================================================

            if (
                e.target.classList.contains(
                    "btn_discunt"
                )
            ) {

                add_descuento(
                    fila
                );
            }
        }
    );
}

// ==========================================================
// DESCUENTO POR CANTIDAD
// ==========================================================

function descuento_cantidad(indice) {

    if (!datos[indice]) {
        return;
    }


    if (
        datos[indice].lleva > 0
    ) {

        if (
            datos[indice].cantidad %
            datos[indice].lleva === 0
        ) {

            datos[indice].descuento +=
                datos[indice].precio_venta *
                (
                    datos[indice].lleva -
                    datos[indice].paga
                );


            datos[indice].restarlleva =
                1;


        } else if (
            datos[indice].cantidad %
            datos[indice].lleva !== 0 &&
            datos[indice].restarlleva === 1
        ) {

            datos[indice].restarlleva =
                0;
        }


    } else {

        datos[indice].descuento +=
            datos[indice].valor_descuento;
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


    const modalElement =
        document.getElementById(
            "modalDescuento"
        );


    if (!modalElement) {
        return;
    }


    const modal =
        bootstrap.Modal.getOrCreateInstance(
            modalElement
        );


    modal.show();
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
    document.getElementById(
        "btnAplicarDescuento"
    ) ||
    document.getElementById(
        "btndescuento"
    );


if (btnAplicarDescuento) {

    btnAplicarDescuento.addEventListener(
        "click",
        function (e) {

            e.preventDefault();


            if (!fila_descuento) {

                mensaje(
                    "Seleccione un producto",
                    "warning",
                    ""
                );

                return;
            }


            const descuento =
                document.getElementById(
                    "Ddescuento"
                );


            if (!descuento) {
                return;
            }


            const indice =
                fila_descuento.sectionRowIndex;


            if (!datos[indice]) {
                return;
            }


            const d =
                fila_descuento.cells[4];


            fetch(
                `/manager/cupon_descuento/${descuento.value}/${datos[indice].id}/`,
                {
                    method: "GET",
                    headers: {}
                }
            )
                .then(async response => {

                    if (!response.ok) {

                        const dato =
                            await response.json();

                        throw new Error(
                            dato.error ||
                            dato.mensaje ||
                            "Error desconocido"
                        );
                    }


                    return response.json();
                })

                .then(data => {

                    const valor =
                        parseFloat(
                            data.descuento
                        ) || 0;


                    if (
                        datos[indice].acumulable
                    ) {

                        datos[indice].descuento +=
                            valor;


                    } else {

                        if (
                            datos[indice].estado === 1
                        ) {

                            datos[indice].descuento =
                                valor;

                            datos[indice].estado =
                                0;


                        } else {

                            datos[indice].descuento +=
                                valor;
                        }
                    }


                    if (d) {

                        d.textContent =
                            "L. " +
                            datos[indice]
                                .descuento
                                .toFixed(2);
                    }


                    fila_descuento =
                        null;


                    tabla_detalle_total();


                    const modalElement =
                        document.getElementById(
                            "modalDescuento"
                        );


                    if (modalElement) {

                        const modal =
                            bootstrap.Modal.getOrCreateInstance(
                                modalElement
                            );

                        modal.hide();
                    }
                })

                .catch(error => {

                    mensaje(
                        error.message,
                        "error",
                        ""
                    );
                });
        }
    );
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


    datos.forEach(item => {

        subtotal +=
            parseFloat(
                item.subtotal
            ) || 0;


        descuento +=
            parseFloat(
                item.descuento
            ) || 0;


        isv15 +=
            parseFloat(
                item.isv15_acumulable
            ) || 0;


        isv18 +=
            parseFloat(
                item.isv18_acumulable
            ) || 0;
    });


    const total =
        subtotal +
        isv15 +
        isv18 -
        descuento;


    const tabla =
        document.getElementById(
            "detalle-total"
        );


    if (!tabla) {
        return;
    }


    const celda_subtotal =
        tabla.rows[0]?.cells[1];

    const celda_descuento =
        tabla.rows[1]?.cells[1];

    const celda_isv15 =
        tabla.rows[2]?.cells[1];

    const celda_isv18 =
        tabla.rows[3]?.cells[1];

    const celda_total =
        tabla.rows[4]?.cells[1];


    total_m =
        total;


    pagos.push({

        rtn: "",

        subtotal: subtotal,

        descuento: descuento,

        isv15: isv15,

        isv18: isv18,

        total: total,

        tipo_pago: "",

        cliente_id:
            clienteSeleccionado
                ? clienteSeleccionado.id
                : "",

        cliente_nombre:
            clienteSeleccionado
                ? clienteSeleccionado.nombre
                : ""
    });


    if (celda_subtotal) {

        celda_subtotal.textContent =
            "L. " +
            subtotal.toFixed(2);
    }


    if (celda_descuento) {

        celda_descuento.textContent =
            "L. " +
            descuento.toFixed(2);
    }


    if (celda_isv15) {

        celda_isv15.textContent =
            "L. " +
            isv15.toFixed(2);
    }


    if (celda_isv18) {

        celda_isv18.textContent =
            "L. " +
            isv18.toFixed(2);
    }


    if (celda_total) {

        celda_total.textContent =
            "L. " +
            total.toFixed(2);
    }
}

// ==========================================================
// CAJA - SECCIÓN 2
// CLIENTES, PAGOS, APERTURA Y CIERRE
// ==========================================================


// ==========================================================
// SELECCIONAR CLIENTE
// ==========================================================

const btnSeleccionarCliente =
    document.getElementById(
        "btnSeleccionarCliente"
    );


if (btnSeleccionarCliente) {

    btnSeleccionarCliente.addEventListener(
        "click",
        function () {

            const buscar =
                document.getElementById(
                    "buscarClienteInput"
                );

            const resultados =
                document.getElementById(
                    "tablaClientesResultados"
                );


            if (buscar) {

                buscar.value = "";
            }


            if (resultados) {

                resultados.innerHTML = "";
            }


            const modalElement =
                document.getElementById(
                    "modalSeleccionarCliente"
                );


            if (!modalElement) {
                return;
            }


            const modal =
                bootstrap.Modal.getOrCreateInstance(
                    modalElement
                );


            modal.show();
        }
    );
}


// ==========================================================
// BUSCAR CLIENTE
// ==========================================================

const buscarClienteInput =
    document.getElementById(
        "buscarClienteInput"
    );


if (buscarClienteInput) {

    buscarClienteInput.addEventListener(
        "input",
        function () {

            const texto =
                this.value.trim();


            const resultados =
                document.getElementById(
                    "tablaClientesResultados"
                );


            if (!resultados) {
                return;
            }


            resultados.innerHTML = "";


            if (texto.length < 2) {

                return;
            }


            if (
                clienteBusquedaControlador
            ) {

                clienteBusquedaControlador.abort();
            }


            clienteBusquedaControlador =
                new AbortController();


            fetch(
                `/manager/clientes/search/?search=${encodeURIComponent(texto)}`,
                {
                    method: "GET",
                    signal:
                        clienteBusquedaControlador.signal
                }
            )
                .then(async response => {

                    if (!response.ok) {

                        const dato =
                            await response.json();

                        throw new Error(
                            dato.error ||
                            "Error al buscar clientes"
                        );
                    }


                    return response.json();
                })

                .then(data => {

                    if (data.length === 0) {

                        resultados.innerHTML = `
                            <tr>
                                <td
                                    colspan="5"
                                    class="text-center text-muted"
                                >
                                    No se encontraron clientes
                                </td>
                            </tr>
                        `;

                        return;
                    }


                    data.forEach(cliente => {

                        const fila =
                            document.createElement(
                                "tr"
                            );


                        fila.style.cursor =
                            "pointer";


                        const celdas = [

                            cliente.id,

                            cliente.nombre_completo ||
                                "Sin nombre",

                            cliente.dni ||
                                "-",

                            cliente.empresa ||
                                "-",

                            cliente.telefono ||
                                "-"
                        ];


                        celdas.forEach(valor => {

                            const celda =
                                document.createElement(
                                    "td"
                                );


                            celda.textContent =
                                valor;


                            fila.appendChild(
                                celda
                            );
                        });


                        fila.addEventListener(
                            "click",
                            () => {

                                seleccionarCliente(
                                    cliente
                                );
                            }
                        );


                        resultados.appendChild(
                            fila
                        );
                    });
                })

                .catch(error => {

                    if (
                        error.name !==
                        "AbortError"
                    ) {

                        mensaje(
                            error.message,
                            "error",
                            ""
                        );
                    }
                });
        }
    );
}


// ==========================================================
// GUARDAR CLIENTE SELECCIONADO
// ==========================================================

function seleccionarCliente(cliente) {

    if (!cliente) {
        return;
    }


    clienteSeleccionado = {

        id: cliente.id,

        nombre:
            cliente.nombre_completo ||
            cliente.dni ||
            "Cliente"
    };


    const clienteId =
        document.getElementById(
            "cliente_id"
        );


    const clienteNombre =
        document.getElementById(
            "cliente_nombre"
        );


    const clienteSeleccionadoInput =
        document.getElementById(
            "clienteSeleccionado"
        );


    const detalle =
        document.getElementById(
            "detalleClienteSeleccionado"
        );


    if (clienteId) {

        clienteId.value =
            cliente.id;
    }


    if (clienteNombre) {

        clienteNombre.value =
            clienteSeleccionado.nombre;
    }


    if (clienteSeleccionadoInput) {

        clienteSeleccionadoInput.value =
            clienteSeleccionado.nombre;
    }


    if (detalle) {

        detalle.textContent =
            `DNI: ${cliente.dni || "-"} • Teléfono: ${cliente.telefono || "-"}`;
    }


    // ------------------------------------------------------
    // CERRAR MODAL
    // ------------------------------------------------------

    const modalElement =
        document.getElementById(
            "modalSeleccionarCliente"
        );


    if (modalElement) {

        const modal =
            bootstrap.Modal.getInstance(
                modalElement
            );


        if (modal) {

            modal.hide();
        }
    }


    // ------------------------------------------------------
    // ACTUALIZAR PAGO
    // ------------------------------------------------------

    if (pagos.length > 0) {

        pagos[0].cliente_id =
            cliente.id;


        pagos[0].cliente_nombre =
            clienteSeleccionado.nombre;
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
            mensaje(
                "Agregue productos a la venta",
                "error",
                ""
            );
            return;
        }

        const tipoPago =
            document.getElementById("tipo_pago")?.value;

        const tarjeta = [];

        const cantidadDinero =
            document.getElementById("Pdinero")?.value || "";

        const digitos =
            document.getElementById("Pdigitos")?.value.trim() || "";

        const autorizacion =
            document.getElementById("Pautorizacion")?.value.trim() || "";

        const clienteId =
            document.getElementById("cliente_id")?.value || "";

        const clienteNombre =
            document.getElementById("cliente_nombre")?.value || "";

        // ------------------------------------------------
        // CLIENTE
        // ------------------------------------------------

        if (!clienteId) {
            mensaje(
                "Seleccione un cliente antes de realizar la venta",
                "error",
                ""
            );
            return;
        }

        // =================================================
        // PAGO CONTADO
        // =================================================

        if (tipoPago === "pago_contado") {

            if (
                cantidadDinero.trim() === "" ||
                isNaN(cantidadDinero) ||
                parseFloat(cantidadDinero) < pagos[0].total
            ) {
                mensaje(
                    "Ingrese una cantidad válida",
                    "error",
                    ""
                );
                return;
            }

            pagos[0].tipo_pago = "contado";

            tarjeta.push({
                digitos: "",
                numero_autorizacion: ""
            });

        // =================================================
        // PAGO TARJETA
        // =================================================

        } else if (tipoPago === "pago_tarjeta") {

            if (autorizacion === "") {
                mensaje(
                    "Escriba el número de autorización",
                    "error",
                    ""
                );
                return;
            }

            if (!/^\d{4}$/.test(digitos)) {
                mensaje(
                    "Ingrese únicamente los últimos 4 dígitos de la tarjeta",
                    "error",
                    ""
                );
                return;
            }

            pagos[0].tipo_pago = "tarjeta";

            tarjeta.push({
                digitos: digitos,
                numero_autorizacion: autorizacion
            });

        // =================================================
        // PAGO A CRÉDITO
        // =================================================

        } else if (tipoPago === "pago_credito") {

            pagos[0].tipo_pago = "credito";

        } else {
            mensaje(
                "Seleccione un tipo de pago",
                "error",
                ""
            );
            return;
        }

        // ------------------------------------------------
        // PREPARAR DATA
        // ------------------------------------------------

        const data = {
            productos: datos,
            pagos: pagos,
            tarjeta: tarjeta,
            cliente: {
                id: clienteId,
                nombre: clienteNombre
            }
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
                    confirmButton: "classbotones"
                }
            }).then(result => {

                if (result.isConfirmed) {

                    enviarVenta(
                        data,
                        tipoPago,
                        cantidadDinero
                    );
                }
            });

            return;
        }

        // =================================================
        // CONTADO
        // =================================================

        enviarVenta(
            data,
            tipoPago,
            cantidadDinero
        );
    });
}


// ==========================================================
// ENVIAR VENTA
// ==========================================================

function enviarVenta(
    data,
    tipoPago,
    cantidadDinero
) {

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

    const botonFormulario =
        document.getElementById("btnPagar");

    const botonCaja =
        document.getElementById("Pagar");

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

    const csrf =
        document.querySelector(
            "[name=csrfmiddlewaretoken]"
        );

    if (!csrf) {

        ventaEnProceso = false;

        if (botonFormulario) {
            botonFormulario.disabled = false;
            botonFormulario.innerText = "Realizar compra";
        }

        if (botonCaja) {
            botonCaja.disabled = false;
        }

        mensaje(
            "No se encontró el token CSRF",
            "error",
            ""
        );

        return;
    }

    // ======================================================
    // ENVIAR
    // ======================================================

    fetch(
        "/manager/realizar_venta/",
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrf.value
            },
            body: JSON.stringify(data)
        }
    )
    .then(async response => {

        const respuesta =
            await response.json();

        if (!response.ok) {
            throw new Error(
                respuesta.error ||
                respuesta.message ||
                "Ocurrió un error al realizar la venta"
            );
        }

        return respuesta;
    })
    .then(data => {

        // ==================================================
        // CONTADO
        // ==================================================

        if (tipoPago === "pago_contado") {

            const cambio =
                (
                    parseFloat(cantidadDinero) -
                    parseFloat(pagos[0].total)
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
                    confirmButton: "classbotones"
                }
            }).then(() => {

                window.open(
                    `/manager/recibo_pdf/${data.id_factura}/`,
                    "_blank"
                );

                location.reload();
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
                    confirmButton: "classbotones"
                }
            }).then(() => {

                window.open(
                    `/manager/recibo_pdf/${data.id_factura}/`,
                    "_blank"
                );

                location.reload();
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
                    confirmButton: "classbotones"
                }
            }).then(() => {

                window.open(
                    `/manager/recibo_pdf/${data.id_factura}/`,
                    "_blank"
                );

                location.reload();
            });
        }
    })
    .catch(error => {

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

        mensaje(
            error.message,
            "error",
            ""
        );
    });
}


// ==========================================================
// BOTÓN PAGAR
// ==========================================================

const btnPagar =
    document.getElementById("Pagar");

if (btnPagar) {

    btnPagar.addEventListener(
        "click",
        function (e) {

            if (this.disabled || ventaEnProceso) {
                e.preventDefault();
                return;
            }

            const modalElement =
                document.getElementById("modalPago");

            if (!modalElement) {
                return;
            }

            const modal =
                bootstrap.Modal.getOrCreateInstance(
                    modalElement
                );

            modal.show();
        }
    );
}

// ==========================================================
// CAMBIO DE TIPO DE PAGO
// ==========================================================

const tipoPagoSelect =
    document.getElementById(
        "tipo_pago"
    );


if (tipoPagoSelect) {

    tipoPagoSelect.addEventListener(
        "change",
        function (e) {

            const opcion =
                e.target.value;


            const dinero =
                document.getElementById(
                    "div_dinero"
                );


            const numero =
                document.getElementById(
                    "div_nuemro"
                );


            const digito =
                document.getElementById(
                    "div_digito"
                );


            // ------------------------------------------------
            // PAGO CONTADO
            // ------------------------------------------------

            if (
                opcion ===
                "pago_contado"
            ) {

                if (dinero)
                    dinero.style.display =
                        "block";

                if (numero)
                    numero.style.display =
                        "none";

                if (digito)
                    digito.style.display =
                        "none";


            // ------------------------------------------------
            // PAGO TARJETA
            // ------------------------------------------------

            } else if (
                opcion ===
                "pago_tarjeta"
            ) {

                if (dinero)
                    dinero.style.display =
                        "none";

                if (numero)
                    numero.style.display =
                        "block";

                if (digito)
                    digito.style.display =
                        "block";


            // ------------------------------------------------
            // PAGO A CRÉDITO
            // ------------------------------------------------

            } else if (
                opcion ===
                "pago_credito"
            ) {

                if (dinero)
                    dinero.style.display =
                        "none";

                if (numero)
                    numero.style.display =
                        "none";

                if (digito)
                    digito.style.display =
                        "none";


            // ------------------------------------------------
            // SIN SELECCION
            // ------------------------------------------------

            } else {

                if (dinero)
                    dinero.style.display =
                        "none";

                if (numero)
                    numero.style.display =
                        "none";

                if (digito)
                    digito.style.display =
                        "none";
            }
        }
    );
}


// ==========================================================
// MENSAJES
// ==========================================================

function mensaje(
    texto,
    tipo,
    funcion
) {

    Swal.fire({

        title:
            texto,

        icon:
            tipo,

        confirmButtonText:
            "Aceptar",

        customClass: {

            confirmButton:
                "classbotones"
        }

    }).then(() => {

        if (
            typeof funcion ===
            "function"
        ) {

            funcion();
        }
    });
}


// ==========================================================
// APERTURA DE CAJA
// ==========================================================

const btnAbrirCaja =
    document.getElementById(
        "btnAbrirCaja"
    );


if (btnAbrirCaja) {

    btnAbrirCaja.addEventListener(
        "click",
        function () {

            const montoInput =
                document.getElementById(
                    "monto_apertura"
                );


            if (!montoInput) {
                return;
            }


            const monto =
                montoInput.value.trim();


            const url =
                btnAbrirCaja.dataset.url;


            if (
                !monto ||
                parseFloat(monto) < 0
            ) {

                Swal.fire({

                    icon:
                        "warning",

                    title:
                        "Monto inválido",

                    text:
                        "Ingrese un monto válido para abrir la caja.",

                    confirmButtonText:
                        "Aceptar",

                    customClass: {

                        confirmButton:
                            "classbotones"
                    }
                });


                return;
            }


            const csrf =
                document.querySelector(
                    '[name=csrfmiddlewaretoken]'
                );


            if (!csrf) {

                mensaje(
                    "No se encontró el token CSRF",
                    "error",
                    ""
                );

                return;
            }


            const formData =
                new FormData();


            formData.append(
                "monto_apertura",
                monto
            );


            btnAbrirCaja.disabled =
                true;


            fetch(
                url,
                {

                    method:
                        "POST",

                    headers: {

                        "X-CSRFToken":
                            csrf.value
                    },

                    body:
                        formData
                }
            )

                .then(
                    response =>
                        response.json()
                )

                .then(data => {

                    if (data.ok) {

                        Swal.fire({

                            icon:
                                "success",

                            title:
                                "Caja abierta",

                            text:
                                data.mensaje,

                            confirmButtonText:
                                "Continuar",

                            customClass: {

                                confirmButton:
                                    "classbotones"
                            }

                        }).then(() => {

                            const modalElement =
                                document.getElementById(
                                    "modalAperturaCaja"
                                );


                            if (modalElement) {

                                const modal =
                                    bootstrap.Modal.getInstance(
                                        modalElement
                                    );


                                if (modal) {

                                    modal.hide();
                                }
                            }


                            montoInput.value =
                                "";


                            location.reload();
                        });


                    } else {

                        Swal.fire({

                            icon:
                                "warning",

                            title:
                                "No se pudo abrir la caja",

                            text:
                                data.mensaje,

                            confirmButtonText:
                                "Aceptar",

                            customClass: {

                                confirmButton:
                                    "classbotones"
                            }
                        });
                    }
                })

                .catch(error => {

                    console.error(
                        "Error:",
                        error
                    );


                    Swal.fire({

                        icon:
                            "error",

                        title:
                            "Error",

                        text:
                            "Ocurrió un error al abrir la caja.",

                        confirmButtonText:
                            "Aceptar",

                        customClass: {

                            confirmButton:
                                "classbotones"
                        }
                    });
                })

                .finally(() => {

                    btnAbrirCaja.disabled =
                        false;
                });
        }
    );
}


// ==========================================================
// CIERRE DE CAJA
// ==========================================================

const btnCierreCaja =
    document.getElementById(
        "btnCierreCaja"
    );


if (btnCierreCaja) {

    btnCierreCaja.addEventListener(
        "click",
        function (e) {

            if (this.disabled) {

                e.preventDefault();

                return;
            }


            Swal.fire({

                icon:
                    "warning",

                title:
                    "¿Iniciar cierre de caja?",

                text:
                    "La caja pasará al proceso de cuadre.",

                showCancelButton:
                    true,

                confirmButtonText:
                    "Sí, continuar",

                cancelButtonText:
                    "Cancelar",

                customClass: {

                    confirmButton:
                        "classbotones"
                }

            }).then(result => {

                if (
                    !result.isConfirmed
                ) {

                    return;
                }


                const csrf =
                    document.querySelector(
                        '[name=csrfmiddlewaretoken]'
                    );


                if (!csrf) {

                    mensaje(
                        "No se encontró el token CSRF",
                        "error",
                        ""
                    );

                    return;
                }


                fetch(
                    btnCierreCaja.dataset.url,
                    {

                        method:
                            "POST",

                        headers: {

                            "X-CSRFToken":
                                csrf.value
                        }
                    }
                )

                    .then(
                        response =>
                            response.json()
                    )

                    .then(data => {

                        if (data.ok) {

                            Swal.fire({

                                icon:
                                    "success",

                                title:
                                    "Cuadre iniciado",

                                text:
                                    "Serás dirigido al cuadre de caja.",

                                confirmButtonText:
                                    "Continuar",

                                customClass: {

                                    confirmButton:
                                        "classbotones"
                                }

                            }).then(() => {

                                window.location.href =
                                    data.redirect_url;
                            });


                        } else {

                            Swal.fire({

                                icon:
                                    "error",

                                title:
                                    "Error",

                                text:
                                    data.mensaje,

                                customClass: {

                                    confirmButton:
                                        "classbotones"
                                }
                            });
                        }
                    })

                    .catch(error => {

                        console.error(
                            error
                        );


                        Swal.fire({

                            icon:
                                "error",

                            title:
                                "Error",

                            text:
                                "Ocurrió un problema al iniciar el cuadre.",

                            customClass: {

                                confirmButton:
                                    "classbotones"
                            }
                        });
                    });
            });
        }
    );
}
