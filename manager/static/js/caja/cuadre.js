function validateNumber(input) {

    // Solo permite números enteros
    input.value = input.value.replace(/[^0-9]/g, "");

    calcularCuadre();
}


function calcularCuadre() {

    const filas = document.querySelectorAll(
        ".cantidad-billete"
    );

    let totalContado = 0;

    filas.forEach(input => {

        const fila = input.closest("tr");

        // Primera columna:
        // "L. 1.00", "L. 2.00", etc.
        const textoDenominacion =
            fila.querySelector("td").textContent;

        const denominacion = parseFloat(
            textoDenominacion.replace("L.", "").trim()
        ) || 0;

        const cantidad = parseInt(
            input.value,
            10
        ) || 0;

        const subtotal = denominacion * cantidad;

        const subtotalElemento =
            fila.querySelector(".subtotal");

        subtotalElemento.textContent =
            `L. ${subtotal.toFixed(2)}`;

        totalContado += subtotal;
    });


    // =========================
    // TOTAL CONTADO
    // =========================

    const totalContadoElemento =
        document.getElementById("totalContado");

    if (totalContadoElemento) {

        totalContadoElemento.textContent =
            `L. ${totalContado.toFixed(2)}`;

    }


    // =========================
    // TOTAL ESPERADO
    // =========================

    const totalEsperadoElemento =
        document.getElementById("totalEsperado");

    const totalEsperado = totalEsperadoElemento
        ? parseFloat(
            totalEsperadoElemento.textContent
                .replace("L.", "")
                .replace(/,/g, "")
                .trim()
        ) || 0
        : 0;


    // =========================
    // DIFERENCIA
    // =========================

    const diferencia =
        totalContado - totalEsperado;

    const diferenciaElemento =
        document.getElementById("diferencia");

    if (diferenciaElemento) {

        diferenciaElemento.textContent =
            `L. ${diferencia.toFixed(2)}`;

    }

}

document.addEventListener("DOMContentLoaded", function () {

    const inputs = document.querySelectorAll(".cantidad-billete");
    const btnCerrar = document.getElementById("btnCerrarCuadre");

    const totalContadoElement = document.getElementById("totalContado");
    const diferenciaElement = document.getElementById("diferencia");
    const totalEsperadoElement = document.getElementById("totalEsperado");

    const denominaciones = [
        1,
        2,
        5,
        10,
        20,
        50,
        100,
        200,
        500
    ];


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

            subtotalElement.textContent =
                `L. ${subtotal.toFixed(2)}`;

            totalContado += subtotal;
        });


        // Total contado

        totalContadoElement.textContent =
            `L. ${totalContado.toFixed(2)}`;


        // Total esperado

        const totalEsperado =
            parseFloat(totalEsperadoElement.dataset.total) || 0;


        // Diferencia

        const diferencia =
            totalContado - totalEsperado;

        diferenciaElement.textContent =
            `L. ${diferencia.toFixed(2)}`;
    }


    // =========================
    // CERRAR CAJA
    // =========================

    btnCerrar.addEventListener("click", function () {

        const totalContadoTexto =
            totalContadoElement.textContent.replace("L.", "").trim();

        const totalContado =
            parseFloat(totalContadoTexto) || 0;

        const totalEsperado =
            parseFloat(totalEsperadoElement.dataset.total) || 0;

        const diferencia =
            totalContado - totalEsperado;


        // =========================
        // CONFIRMACIÓN SWEETALERT
        // =========================

        Swal.fire({
            title: "¿Cerrar cuadre de caja?",
            html: `
                <div style="text-align:left">
                    <p>
                        <strong>Total esperado:</strong>
                        L. ${totalEsperado.toFixed(2)}
                    </p>

                    <p>
                        <strong>Total contado:</strong>
                        L. ${totalContado.toFixed(2)}
                    </p>

                    <p>
                        <strong>Diferencia:</strong>
                        L. ${diferencia.toFixed(2)}
                    </p>

                    <hr>

                    <p>
                        Una vez cerrada la caja no podrás modificar este cuadre.
                    </p>
                </div>
            `,
            icon: "warning",
            showCancelButton: true,
            confirmButtonText: "Sí, cerrar caja",
            cancelButtonText: "Cancelar",
            reverseButtons: true,
            customClass: {
            confirmButton:
                "classbotones"
            }
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

            formData.append(
                `cantidad_${denominacion.toFixed(2)}`,
                cantidad
            );
        });


        // =========================
        // CSRF
        // =========================

        const csrfToken =
            document.querySelector(
                '[name="csrfmiddlewaretoken"]'
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
            }
        });


        btnCerrar.disabled = true;


        // =========================
        // REQUEST
        // =========================

        fetch("/manager/caja/cuadre/cerrar/", {

            method: "POST",

            headers: {
                "X-CSRFToken": csrfToken
            },

            body: formData

        })

        .then(function (response) {

            return response.json();

        })

        .then(function (data) {

            if (!data.ok) {
                throw new Error(
                    data.mensaje || "No se pudo cerrar la caja."
                );
            }


            // =========================
            // ÉXITO
            // =========================

            Swal.fire({
                title: "¡Caja cerrada!",
                html: `
                    <p>
                        El cuadre se guardó correctamente.
                    </p>

                    <hr>

                    <p>
                        <strong>Total contado:</strong>
                        L. ${parseFloat(data.total_contado).toFixed(2)}
                    </p>

                    <p>
                        <strong>Total esperado:</strong>
                        L. ${parseFloat(data.total_esperado).toFixed(2)}
                    </p>

                    <p>
                        <strong>Diferencia:</strong>
                        L. ${parseFloat(data.diferencia).toFixed(2)}
                    </p>
                `,
                icon: "success",
                confirmButtonText: "Aceptar",
                customClass: {
                    confirmButton:
                        "classbotones"
                }
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
                confirmButtonText: "Aceptar"
            });


            btnCerrar.disabled = false;
        });

    }


    // =========================
    // INICIALIZAR
    // =========================

    calcularCuadre();

});