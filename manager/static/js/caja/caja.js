//contiene los productos que se van a agregar a caja
let datos = [];
//contiene los datos del filtro de busqueda
let productos_dato = [];

let pagos= []

let tarjetas = [];

let fila_descuento;

let total_m = 0;

//evento de busqueda por codigo
document.getElementById('codigo_busqueda').addEventListener('keydown', function (event) {
    if (event.key == "Enter") {
        event.preventDefault();
        let codigo = document.getElementById('codigo_busqueda').value;

        if(codigo.trim()==="" || isNaN(codigo)){
            mensaje('Ingrese un codigo Valido','error','');
            return;
        }

        productos(codigo);
    }
});


//determinar si existe el codigo o no.
function productos(codigo) {
    if (codigo === "" || !Number.isInteger(Number(codigo))) {
        return console.log('Codigo no valido');
    }

    let producto = datos.findIndex(p => p.codigo === codigo);

    if (producto === -1) {
        sin_codigo(codigo);
    }
    else {
        con_codigo(producto);
        tabla_detalle_total();
    }
}

//agregar producto si existe el codigo en la tabla
function con_codigo(i) {
    datos[i].cantidad += 1;

    if (datos[i].estado === 1) {
        descuento_cantidad(i);
    }

    datos[i].subtotal = datos[i].cantidad * datos[i].precio_venta;
    datos[i].isv15_acumulable += datos[i].isv_15;
    datos[i].isv18_acumulable += datos[i].isv_18;

    let tabla = document.getElementById('tablaProductos');
    let cantidad = tabla.rows[i + 1].cells[2].querySelector('.pre');
    let subtotal = tabla.rows[i + 1].cells[5];
    let descuento = tabla.rows[i + 1].cells[4];

    cantidad.textContent = datos[i].cantidad;
    subtotal.textContent = 'L. ' + datos[i].subtotal.toFixed(2);
    descuento.textContent = 'L. ' + datos[i].descuento.toFixed(2);


}

//fecth de busqueda sin el codigo no esta en la tabla
async function sin_codigo(codigo) {
    await fetch(`/manager/busquedacodigo/${codigo}/`, {
        method: 'GET',
        headers: {

        },
    })
        .then(async response => {
            if (!response.ok) {
                const dato = await response.json();
                throw new Error(
                dato.error || dato.mensaje || "Error desconocido"
                );
            }

            return response.json();
        })
        .then(data => {

            let imp15 = 0;
            let imp18 = 0;
            if (parseFloat(data.tipos_isv) === 15) {
                imp15 = parseFloat(data.isv);
            }
            else if (parseFloat(data.tipos_isv) === 18) {
                imp18 = parseFloat(data.isv);
            }

            let producto = {
                id: data.id,
                codigo: data.codigo_sku,
                nombre: data.nombre,
                precio_venta: parseFloat(data.precio_venta),
                cantidad: 1,
                descuento: parseFloat(data.descuentos),
                subtotal: parseFloat(data.precio_venta),
                valor_descuento: parseFloat(data.descuentos),
                acumulable: data.acumulable,
                estado: 1,
                isv_15: imp15,
                isv_18: imp18,
                isv15_acumulable: imp15,
                isv18_acumulable: imp18,
                lleva: parseInt(data.lleva),
                paga: parseInt(data.paga),
                restarlleva: 0
            }

            datos.push(producto)

            tabla_codigo(data.codigo_sku, data.nombre, 1, parseFloat(data.precio_venta).toFixed(2), parseFloat(data.descuentos).toFixed(2), parseFloat(data.precio_venta).toFixed(2));
        })
        .catch(error => {
            mensaje(error.message,"error",'');
        })
}

//busqueda por nombre
let busqueda = document.getElementById('busqueda');
let resultados = document.getElementById('resultadoBusquda');

//evitar el evento de submit.
busqueda.addEventListener('keydown', function (event) {
    if (event.key == "Enter") {
        event.preventDefault();
    }
});

//controlador para que cuando se escribe rapido cancele el fetch hasta que termine la escritura.
let controlador = null;

//evento de input para buscar los productos de la base de datos y agregarlo a la lista.
busqueda.addEventListener('input', function () {

    resultados.innerHTML = "";
    resultados.style.display = "none";

    const texto = busqueda.value.trim();

    if (texto.length < 2) return;

    if (controlador) {
        controlador.abort();
    }

    controlador = new AbortController();

    fetch(`/manager/busquedanombre/${texto}`, {
        method: 'GET',
        signal: controlador.signal
    })
        .then(response => {
            if (!response.ok) {
                throw new Error("Error en la petición");
            }
            return response.json();
        })
        .then(data => {

            productos_dato = [];
            resultados.innerHTML = "";

            if (data.length > 0) {

                resultados.style.display = 'block';

                data.forEach((p, index) => {

                    productos_dato.push(p);

                    const div = document.createElement('div');
                    div.className = 'item-resultado';
                    div.textContent = p.nombre;

                    div.addEventListener('click', () => {
                        seleccionarProducto(index);
                    });

                    resultados.appendChild(div);
                });

            } else {
                resultados.style.display = 'block';
                resultados.innerHTML = `
                <div class="item-resultado">
                    Sin resultados
                </div>
            `;
            }
        })
        .catch(error => {
            if (error.name !== "AbortError") {
                console.log(error);
            }
        });
});

//numero de indicie de producto seleccionado.
let codex = 0;

//funcion para agregar los datos seleccionados de busqueda por nombre al modal.
function seleccionarProducto(index) {
    codex = index;

    let codigo = document.getElementById('nCodigo');
    let nombre = document.getElementById('nNombre');
    let precio = document.getElementById('nPrecio');

    codigo.value = productos_dato[index].codigo_sku;
    nombre.value = productos_dato[index].nombre;
    precio.value = 'L. ' + productos_dato[index].precio_venta;


    const modal = new bootstrap.Modal(document.getElementById('modalagregar'));
    modal.show();
}

//evento de boton del modal agregar los datos seleccionados a la tabla y al arreglo de datos.
document.getElementById('btnregis').addEventListener('click', function (e) {
    e.preventDefault();

    let codigo = document.getElementById('nCodigo').value;

    let cantidad = document.getElementById('nCanitdad').value;

    if (cantidad.trim() === "" || cantidad<=0||isNaN(cantidad)) {
        mensaje('La cantidad debe ser mayor que 0','error','')
        return;
    }

    let producto = datos.findIndex(p => p.codigo === codigo);

    if (producto === -1) {

        let imp15 = 0;
        let imp18 = 0;
        if (parseFloat(productos_dato[codex].tipos_isv) === 15) {
            imp15 = parseFloat(productos_dato[codex].isv);
        }
        else if (parseFloat(productos_dato[codex].tipos_isv) === 18) {
            imp18 = parseFloat(productos_dato[codex].isv);
        }

        let producto_b = {
            id: productos_dato[codex].id,
            codigo: productos_dato[codex].codigo_sku,
            nombre: productos_dato[codex].nombre,
            precio_venta: productos_dato[codex].precio_venta,
            cantidad: parseInt(cantidad),
            descuento: parseFloat(productos_dato[codex].descuento * cantidad),
            subtotal: (productos_dato[codex].precio_venta * cantidad),
            valor_descuento: parseFloat(productos_dato[codex].descuento),
            acumulable: productos_dato[codex].es_acumulable,
            estado: 1,
            lleva: parseInt(productos_dato[codex].lleva),
            paga: parseInt(productos_dato[codex].paga),
            restarlleva: 0,
            isv_15: imp15,
            isv_18: imp18,
            isv15_acumulable: imp15 * cantidad,
            isv18_acumulable: imp18 * cantidad
        }
        if (producto_b.lleva > 0) {
            if (cantidad >= producto_b.lleva) {
                                
                let grupos = Math.floor(cantidad / producto_b.lleva);
                producto_b.descuento += (producto_b.precio_venta * (producto_b.lleva - producto_b.paga)) * grupos;
                
                if(cantidad % producto_b.lleva === 0){
                producto_b.restarlleva = 1;
                }

            }
        }


        datos.push(producto_b)


        tabla_codigo(productos_dato[codex].codigo_sku, productos_dato[codex].nombre, parseInt(cantidad),
            productos_dato[codex].precio_venta, parseFloat(producto_b.descuento).toFixed(2), parseFloat(productos_dato[codex].precio_venta * parseInt(cantidad)).toFixed(2));

        const modalEl = document.getElementById('modalagregar');
        const modal = bootstrap.Modal.getOrCreateInstance(modalEl);

        modal.hide();

        document.getElementById('nCanitdad').value = 0;

        tabla_detalle_total();

    }
    else {

        tabla_detalle_total();
    }

});

// cerrar selector
busqueda.addEventListener('blur', function () {
    setTimeout(() => {
        resultados.style.display = 'none';
        resultados.innerHTML = '';
    }, 300);
});

//abrir el selector de productos por nombre
busqueda.addEventListener('focus', function () {
    if (busqueda.value.length < 2) {
        resultados.innerHTML = '';
        resultados.style.display = 'block';
        resultados.innerHTML += `
                            <div class="item-resultado">
                                _______________________
                                      Sin Resultados
                            </div>`;
    }
    setTimeout(() => {
        resultados.style.display = 'block';
    }, 200);
});

//agregar producto tabla
function tabla_codigo(codigo, nombre, canti, sub, des, total) {
    let tabla = document.querySelector(`#tablaProductos tbody`);

    let fila = tabla.insertRow();

    fila.insertCell(0).textContent = codigo;
    fila.insertCell(1).textContent = nombre;
    let cantidad = fila.insertCell(2);
    fila.insertCell(3).textContent = 'L. ' + sub;
    fila.insertCell(4).textContent = 'L. ' + des;
    fila.insertCell(5).textContent = 'L. ' + total;

    let boton = fila.insertCell(6);

    let div_row = document.createElement('div');
    div_row.className = 'div_row';

    let div_pre = document.createElement('div');

    let p = document.createElement('p');
    p.className = 'pre';
    p.textContent = canti;

    div_pre.appendChild(p)

    let div_button_action = document.createElement('div');
    div_button_action.className = 'button_action';

    let button_mas = document.createElement('button');
    button_mas.classList.add = 'btn_add';
    button_mas.className = 'btn_add';
    button_mas.textContent = '+';

    let button_men = document.createElement('button');
    button_men.classList.add = 'btn_remove';
    button_men.className = 'btn_remove';
    button_men.textContent = '-';

    div_button_action.appendChild(button_mas);
    div_button_action.appendChild(button_men);

    div_row.appendChild(div_pre);
    div_row.appendChild(div_button_action);

    cantidad.appendChild(div_row);

    let div_descueto = document.createElement('div');
    div_descueto.className = 'button_action';

    let buton_descueto = document.createElement('button');
    buton_descueto.classList.add = 'btn_add';
    buton_descueto.className = 'btn_discunt';
    buton_descueto.textContent = 'cupon';

    div_descueto.appendChild(buton_descueto);

    boton.appendChild(div_descueto);
    tabla_detalle_total();
}

const tbody = document.querySelector("#tablaProductos tbody");

tbody.addEventListener("click", (e) => {

    const fila = e.target.closest("tr");

    if (e.target.classList.contains("btn_add")) {

        const fila = e.target.closest("tr");

        let indice = fila.sectionRowIndex;

        datos[indice].cantidad++;
        if (datos[indice].estado === 1) {
            descuento_cantidad(indice);
        }

        datos[indice].subtotal = datos[indice].cantidad * datos[indice].precio_venta;
        datos[indice].isv15_acumulable += datos[indice].isv_15;
        datos[indice].isv18_acumulable += datos[indice].isv_18;

        let c = fila.querySelector('.pre');
        let s = fila.cells[5];
        let d = fila.cells[4];

        s.textContent = 'L. ' + datos[indice].subtotal.toFixed(2);
        d.textContent = 'L. ' + datos[indice].descuento.toFixed(2);

        c.textContent = datos[indice].cantidad;

        tabla_detalle_total();
    }

    if (e.target.classList.contains('btn_remove')) {
        const fila = e.target.closest('tr');
        let indice = fila.sectionRowIndex;

        datos[indice].cantidad--;
        if (datos[indice].estado === 1) {
            if (datos[indice].lleva > 0) {
                if (datos[indice].cantidad % (datos[indice].lleva) !== 0 && datos[indice].restarlleva === 1) {
                    datos[indice].descuento -= (datos[indice].precio_venta * (datos[indice].lleva - datos[indice].paga));
                    datos[indice].restarlleva = 0;
                }
                else if (datos[indice].cantidad % (datos[indice].lleva) === 0 && datos[indice].restarlleva === 0) {
                    datos[indice].restarlleva = 1;
                }
            }
            else {
                datos[indice].descuento -= datos[indice].valor_descuento;
            }
        }

        datos[indice].subtotal = datos[indice].cantidad * datos[indice].precio_venta;
        datos[indice].isv15_acumulable -= datos[indice].isv_15;
        datos[indice].isv18_acumulable -= datos[indice].isv_18;

        if (datos[indice].cantidad === 0) {
            datos.splice(indice, 1);
            fila.remove();
            tabla_detalle_total();
            return;
        }

        let c = fila.querySelector('.pre');
        let s = fila.cells[5];
        let d = fila.cells[4];

        s.textContent = 'L. ' + datos[indice].subtotal.toFixed(2);

        c.textContent = datos[indice].cantidad;

        d.textContent = 'L. ' + datos[indice].descuento.toFixed(2);

        tabla_detalle_total();
    }

    if (e.target.classList.contains('btn_discunt')) {
        const fila = e.target.closest('tr');
        add_descuento(fila);
    }

});


function descuento_cantidad(indice) {
    if (datos[indice].lleva > 0) {
        if (datos[indice].cantidad % (datos[indice].lleva) === 0) {
            datos[indice].descuento += (datos[indice].precio_venta * (datos[indice].lleva - datos[indice].paga));
            datos[indice].restarlleva = 1;
        }
        else if(datos[indice].cantidad % (datos[indice].lleva) !== 0 && datos[indice].restarlleva === 1){
            datos[indice].restarlleva = 0;
        }
    }
    else {
        datos[indice].descuento += datos[indice].valor_descuento;
    }
}

function add_descuento(fila) {
    fila_descuento = fila;
    let modal = new bootstrap.Modal(document.getElementById('modalDescuento'));
    modal.show();
}

document.getElementById('btndescuento').addEventListener('click', function (e) {
    e.preventDefault();
    let descuento = document.getElementById('Ddescuento');
    let indice = fila_descuento.sectionRowIndex;
    let d = fila_descuento.cells[4]

    fetch(`/manager/cupon_descuento/${descuento.value}/${datos[indice].id}/`, {
        method: 'GET',
        headers: {

        },
    })
        .then(async response => {
            if (!response.ok) {
                const dato = await response.json();
                throw new Error(
                dato.error || dato.mensaje || "Error desconocido"
                );

            }

            return response.json();
        })
        .then(data => {

            if (datos[indice].acumulable) {
                datos[indice].descuento += parseFloat(data.descuento);

            }
            else {
                if (datos[indice].estado === 1) {
                    datos[indice].descuento = parseFloat(data.descuento);
                    datos[indice].estado = 0;
                }
                else {
                    datos[indice].descuento += parseFloat(data.descuento);
                }
            }

            d.textContent = 'L. ' + datos[indice].descuento.toFixed(2);
            fila_descuento = null;
            tabla_detalle_total();

            let modal = document.getElementById('modalDescuento');
            let modalE = bootstrap.Modal.getOrCreateInstance(modal);

            modalE.hide();

        })
        .catch(error => {
            mensaje(error.message,"error",'');
        });

})

function tabla_detalle_total() {
    pagos=[];
    let subtotal = 0;
    let descuento = 0;
    let isv15 = 0;
    let isv18 = 0;

    datos.forEach((item, index) => {
        subtotal += item.subtotal;
        descuento += item.descuento;
        isv15 += item.isv15_acumulable;
        isv18 += item.isv18_acumulable;
    })


    let total = (subtotal + isv15 + isv18) - descuento;

    let tabla = document.getElementById('detalle-total');
    let celda_subtotal = tabla.rows[0].cells[1];
    let celda_descuento = tabla.rows[1].cells[1];
    let celda_isv15 = tabla.rows[2].cells[1];
    let celda_isv18 = tabla.rows[3].cells[1];
    let celda_total = tabla.rows[4].cells[1];

    total_m = total;

    pagos.push({
        rtn:'',
        subtotal:subtotal,
        descuento:descuento,
        isv15:isv15,
        isv18:isv18,
        total:total,
        tipo_pago:''
    })

    celda_subtotal.textContent = 'L. ' + subtotal.toFixed(2);
    celda_descuento.textContent = 'L. ' + descuento.toFixed(2);
    celda_isv15.textContent = 'L. ' + isv15.toFixed(2);
    celda_isv18.textContent = 'L. ' + isv18.toFixed(2);
    celda_total.textContent = 'L. ' + total.toFixed(2);

    
}


//pagos

document.getElementById('postpagar').addEventListener('submit', function (e) {
    e.preventDefault();

        if(datos.length ===0){
            mensaje('Agregue productos a la venta','error','');
            return;
        }

        let tipo_pago = document.getElementById('tipo_pago').value;

        let tarjeta = []

        let canitdad =document.getElementById('Pdinero').value;
        let digitos =document.getElementById('Pdigitos').value;
        let autoriza=document.getElementById('Pautorizacion').value;

        let rtn = document.getElementById('PRTN').value;


        pagos[0].rtn = rtn;


        if(tipo_pago ==="pago_contado"){
            
                if(canitdad.trim() === "" || isNaN(canitdad) || parseFloat(canitdad) < pagos[0].total){
                    mensaje('Ingrese una cantidad valida','error','');
                    return;
                }

            pagos[0].tipo_pago ="contado"
            
            tarjeta.push({
                digitos:'',
                numero_autorizacion:'',
            })


        }
        else if(tipo_pago === "pago_tarjeta"){
            pagos[0].tipo_pago ="tarjeta"

            if(autoriza.trim() === ""){
                mensaje("escriba el nuemro de autorización",'error','')
                return;
            }

            if(digitos.trim() === ""){
                mensaje("Escriba los ultimos cuatro digitos",'error','')
                return;
            }

            tarjeta.push({
                digitos: digitos,
                numero_autorizacion: autoriza,
            })
        }
        else{
            mensaje('Seleccione un tipo de pago',"error",'');
            return;
        }
        
        let data = {
            productos:datos,
            pagos:pagos,
            tarjeta:tarjeta
        }

        fetch('/manager/realizar_venta/',{
            method:'POST',
            headers: {
                "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: JSON.stringify(data)
        })
        .then(async response=>{
            if(!response.ok){
                const dato = await response.json();
                console.log(dato)
                throw new Error(
                dato.error || dato.message || "Error desconocido"
                );
            }
            return response.json();
        })
        .then(data=>{
          
            if(tipo_pago === "pago_contado"){
                let recargar = ()=>location.reload();
                mensaje(`Cambio: L. ${(parseFloat(parseFloat(canitdad)-pagos[0].total)).toFixed(2)}`,"success",recargar)
            }
            console.log(data.id_facutura)
            window.open(`/manager/recibo_pdf/${data.id_facutura}/`,'_blank')

            
        })
        .catch(error=>{
            mensaje(error.message,"error",'');
        })
        
});

document.getElementById('Pagar').addEventListener('click', function (e) {
    let modal = new bootstrap.Modal(document.getElementById('modalPago'));
    modal.show();
});

document.getElementById('tipo_pago').addEventListener('change', function (e) {

    let opcion = e.target.value;
    let dinero = document.getElementById('div_dinero');
    let numero = document.getElementById('div_nuemro');
    let digito = document.getElementById('div_digito');
    let banco = document.getElementById('div_banco');
    let red = document.getElementById('div_red');

    if (opcion === "pago_contado") {
        dinero.style.display = 'block';
        numero.style.display = 'none';
        digito.style.display = 'none';
        banco.style.display = 'none';
        red.style.display = 'none';
    }
    else if (opcion === "pago_tarjeta") {
        dinero.style.display = 'none';
        numero.style.display = 'block';
        digito.style.display = 'block';
        banco.style.display = 'block';
        red.style.display = 'block';
    }
    else {
        dinero.style.display = 'none';
        numero.style.display = 'none';
        digito.style.display = 'none';
        banco.style.display = 'none';
        red.style.display = 'none';
    }
});

function mensaje(mensaje,tipo,funcion){
    Swal.fire({
        title:mensaje,
        icon:tipo,
        confirmButtonText:"Aceptar",
        customClass: { confirmButton: "classbotones" }
    }).then(()=>{
        if(typeof funcion==="function"){
            funcion();
        }
    })
}
document.getElementById("postapertura").addEventListener("submit",function(e){
    e.preventDefault();

    let data = {
        efectio_encaja: parseFloat(document.getElementById("efectivo").value)
    }
    console.log(data)
    fetch("/manager/apertura_caja/",{
        method:"POST",
        headers: {
                "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value
        },
        body: JSON.stringify(data)
    })
    .then(async response=>{
        if (!response.ok){
            const dato = await response.json();
                console.log(dato)
                throw new Error(
                dato.error || dato.message || "Error desconocido"
                );
        }
        return response.json();
    })
    .then(data=>{
        document.getElementById("efectivo").value=""
        location.reload();
    })
    .catch(error=>{
        mensaje(error.message,"error","");
    })
})