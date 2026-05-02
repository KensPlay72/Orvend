document.addEventListener("DOMContentLoaded", () => {

    const tbody = document.querySelector(".tablas-todo tbody");

    tbody.addEventListener("click", (e) => {
        const fila = e.target.closest("tr.fila-producto");
        if (!fila) return;

        // quitar selección de TODAS las filas visibles
        document.querySelectorAll(".fila-producto.selected")
            .forEach(f => f.classList.remove("selected"));

        // activar seleccionada
        fila.classList.add("selected");
    });

});


document.addEventListener("DOMContentLoaded", () => {

    const tbody = document.querySelector(".tablas-todo tbody");
    const loader = document.getElementById("loader");

    tbody.addEventListener("click", async (e) => {
        const fila = e.target.closest("tr.fila-producto");
        if (!fila) return;

        const idProducto = fila.dataset.id;

        // selección visual
        document.querySelectorAll(".fila-producto.selected")
            .forEach(f => f.classList.remove("selected"));

        fila.classList.add("selected");

        // loader
        if (loader) loader.style.display = "flex";

        try {
            const response = await fetch(`/manager/inventario/${idProducto}/`, {
                method: "GET",
                headers: {
                    "Content-Type": "application/json"
                }
            });

            const data = await response.json();

            console.log("Respuesta Python:", data);

            //aquí luego pintamos imagen + tabla
            renderInventario(data);

        } catch (err) {
            console.error("Error:", err);
        } finally {
            if (loader) loader.style.display = "none";
        }
    });

});


function renderInventario(data) {

    if (data.error) {
        console.error(data.error);
        return;
    }

    const producto = data.producto;

    // imagen
    const img = document.getElementById("imgProducto");
    img.src = producto.imagenUrl;
    img.style.display = "block";

    // =========================
    // RESET: poner todo en 0
    // =========================
    document.querySelectorAll("#tablaInventarioBody tr").forEach(tr => {
        tr.querySelector(".cantidad").textContent = "0";
    });

    // =========================
    // ACTUALIZAR SOLO EXISTENTES
    // =========================
    data.inventario.forEach(item => {

        // buscar fila por ubicación
        const fila = document.querySelector(
        `#tablaInventarioBody tr[data-id="${item.ubicacion}"]`
        );
        if (fila) {
            const tdCantidad = fila.querySelector(".cantidad");

            tdCantidad.textContent = item.cantidad;
        }

    });
}