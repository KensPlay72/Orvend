import sys

from django.conf import settings
from django.http import FileResponse, Http404
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET

from manager.models import SuscripcionSistema


# Lista explícita: esta ruta no convierte el directorio en un explorador de
# archivos público. Cada nuevo recurso debe añadirse aquí conscientemente.
PUBLIC_ASSETS = {
    "opengraph.webp": "image/webp",
}

def home(request):
    return render(request, 'home.html')


def _documento_legal(titulo, resumen, secciones):
    return {
        "titulo": titulo,
        "resumen": resumen,
        "secciones": secciones,
        "actualizado": timezone.localdate().strftime("%d/%m/%Y"),
    }


def politica_privacidad(request):
    documento = _documento_legal(
        "Política de privacidad",
        "Explica qué información utiliza OrvendMart, con qué finalidad y cómo puedes solicitar asistencia sobre ella.",
        [
            {
                "titulo": "1. Alcance y responsable",
                "parrafos": [
                    "Esta política aplica al sitio web y a la plataforma OrvendMart. El responsable del uso operativo de los datos de cada negocio es el cliente titular de la suscripción; OrvendMart provee la plataforma y procesa la información conforme a las instrucciones de dicho cliente.",
                    "Para consultas sobre esta política o sobre la información de una cuenta, escríbenos a soporte@orvendmart.com. El cliente debe mantener actualizados sus datos comerciales, de contacto y facturación en la propuesta, contrato o factura aplicable.",
                ],
            },
            {
                "titulo": "2. Datos que tratamos",
                "parrafos": [
                    "Recopilamos únicamente los datos necesarios para prestar y proteger el servicio. No solicitamos información sensible salvo que el cliente la ingrese por decisión propia en los módulos del sistema.",
                ],
                "lista": [
                    "Datos de acceso: usuario, contraseña almacenada de forma protegida, rol y registros de inicio de sesión.",
                    "Datos operativos ingresados por el cliente: clientes, proveedores, productos, inventario, ventas, compras, facturas, créditos y movimientos de caja.",
                    "Datos de contacto cuando el cliente los usa: nombre, teléfono, correo, dirección y datos fiscales necesarios para su operación.",
                    "Datos técnicos mínimos: sesión, protección CSRF, registros de seguridad y eventos necesarios para diagnosticar fallos o prevenir abuso.",
                ],
            },
            {
                "titulo": "3. Finalidades",
                "lista": [
                    "Autenticar usuarios, administrar permisos y mantener la seguridad de la cuenta.",
                    "Ejecutar las funciones contratadas de caja, inventario, compras, ventas, créditos, reportes y documentos.",
                    "Atender soporte, prevenir fraude, cumplir obligaciones legales y resolver incidencias técnicas.",
                    "Enviar facturas por WhatsApp únicamente cuando el cliente habilita esa función para un destinatario.",
                ],
            },
            {
                "titulo": "4. Integraciones y encargados",
                "parrafos": [
                    "La plataforma puede utilizar proveedores técnicos para prestar las funciones activadas por el cliente. Cada proveedor recibe solo la información estrictamente necesaria para esa función.",
                ],
                "lista": [
                    "Nextcloud: almacenamiento de archivos e imágenes configurados en la plataforma.",
                    "n8n y WhatsApp: automatización y entrega de facturas por WhatsApp cuando el cliente activa esa opción.",
                    "Redis: coordinación temporal de notificaciones en tiempo real; no es un canal público de analítica.",
                    "Cloudflare, cuando se contrata: seguridad, red y entrega del sitio.",
                    "Google Fonts y AOS desde unpkg en la página pública: pueden recibir la dirección IP y datos técnicos normales de una solicitud web para entregar fuentes o recursos visuales. No se usan para analítica publicitaria dentro de OrvendMart.",
                ],
            },
            {
                "titulo": "5. Conservación, seguridad y derechos",
                "parrafos": [
                    "Conservamos los datos mientras exista una suscripción activa y durante el tiempo adicional requerido para soporte, obligaciones legales, prevención de fraude o resolución de controversias. Aplicamos controles de acceso por usuario, contraseñas protegidas, sesiones seguras y medidas técnicas razonables; ningún sistema es completamente infalible.",
                    "Puedes solicitar acceso, corrección o actualización de tus datos a soporte@orvendmart.com. Las solicitudes sobre datos ingresados por un negocio deben ser realizadas por su administrador autorizado. La eliminación estará sujeta a obligaciones legales, contables y de seguridad aplicables.",
                ],
            },
            {
                "titulo": "6. Cambios",
                "parrafos": [
                    "Podemos actualizar esta política cuando cambien el servicio, las integraciones o los requisitos legales. Publicaremos la versión vigente en esta página.",
                ],
            },
        ],
    )
    return render(request, "legal/documento.html", {"documento": documento})


def politica_cookies(request):
    documento = _documento_legal(
        "Política de cookies",
        "OrvendMart usa cookies técnicas indispensables para que el acceso y la seguridad de la plataforma funcionen correctamente.",
        [
            {
                "titulo": "1. Qué son las cookies",
                "parrafos": [
                    "Las cookies son pequeños archivos que el navegador guarda para recordar información entre solicitudes. No se usan para leer archivos personales del dispositivo.",
                ],
            },
            {
                "titulo": "2. Cookies que utiliza el sistema",
                "lista": [
                    "sessionid: mantiene la sesión autenticada y los permisos del usuario durante el uso de la plataforma.",
                    "csrftoken: protege los formularios y solicitudes contra falsificación de peticiones (CSRF).",
                ],
                "parrafos": [
                    "Estas cookies son estrictamente necesarias. Sin ellas no es posible iniciar sesión ni usar de forma segura las funciones del sistema.",
                ],
            },
            {
                "titulo": "3. Analítica, publicidad y consentimiento",
                "parrafos": [
                    "Actualmente OrvendMart no incorpora Google Analytics, Meta Pixel, Clarity, cookies publicitarias ni perfiles de seguimiento. Por ello no se muestra un banner de consentimiento para cookies no esenciales.",
                    "Si en el futuro se incorporan cookies de analítica, publicidad o seguimiento no esencial, se actualizará esta política y se solicitará el consentimiento previo cuando corresponda antes de activarlas.",
                ],
            },
            {
                "titulo": "4. Control desde el navegador",
                "parrafos": [
                    "Puedes bloquear o eliminar cookies desde la configuración de tu navegador. Si eliminas o bloqueas las cookies técnicas, puede que debas volver a iniciar sesión o que algunas funciones dejen de operar correctamente.",
                ],
            },
        ],
    )
    return render(request, "legal/documento.html", {"documento": documento})


def terminos_condiciones(request):
    documento = _documento_legal(
        "Términos y condiciones",
        "Estas condiciones regulan el uso de OrvendMart como plataforma de gestión para negocios.",
        [
            {
                "titulo": "1. Aceptación y alcance",
                "parrafos": [
                    "Al crear una cuenta, contratar o utilizar OrvendMart, el cliente y sus usuarios autorizados aceptan estos términos. El cliente es responsable de asignar usuarios, permisos y contraseñas a su personal.",
                    "OrvendMart es una herramienta de gestión. El cliente conserva la responsabilidad por la veracidad de sus datos, sus obligaciones fiscales, comerciales, laborales y el cumplimiento de las leyes aplicables a su negocio.",
                ],
            },
            {
                "titulo": "2. Suscripción, vigencia y acceso",
                "parrafos": [
                    "El acceso operativo a la plataforma depende de una suscripción vigente dentro del período contratado. La vigencia se valida con la fecha del servidor, no con la fecha configurada en el equipo del usuario.",
                    "Al vencer o suspenderse la suscripción, los usuarios no administradores no podrán iniciar sesión ni realizar solicitudes dentro del sistema. El sitio público y la pantalla de inicio de sesión permanecen disponibles.",
                    "La información operativa estará accesible mientras el cliente mantenga una suscripción activa. Si no existe una suscripción vigente, OrvendMart no está obligado a brindar acceso, exportaciones, soporte ni disponibilidad de la información, salvo lo que exija la legislación aplicable o un acuerdo escrito distinto.",
                ],
            },
            {
                "titulo": "3. Uso permitido",
                "lista": [
                    "Usar el sistema solo para actividades lícitas y con usuarios autorizados.",
                    "No intentar acceder a cuentas ajenas, vulnerar controles de seguridad, copiar el código, interferir con el servicio ni usar automatizaciones no autorizadas.",
                    "Mantener seguros los equipos, credenciales y los datos de los clientes, proveedores y empleados que se ingresen al sistema.",
                ],
            },
            {
                "titulo": "4. Disponibilidad y soporte",
                "parrafos": [
                    "Buscamos mantener el servicio disponible y seguro, pero pueden existir mantenimientos, fallos de proveedores, actualizaciones o eventos fuera de control razonable. No se garantiza operación ininterrumpida ni libre de errores.",
                    "El soporte se presta por los canales informados al cliente y está sujeto al plan contratado y a la suscripción vigente.",
                ],
            },
            {
                "titulo": "5. Pagos, cancelación y reembolsos",
                "parrafos": [
                    "Los precios, períodos, impuestos y condiciones comerciales se informan en la propuesta, factura o acuerdo aplicable. La política de reembolsos forma parte de estos términos.",
                    "La cancelación puede solicitarse por los canales de soporte. La finalización del acceso no libera al cliente de pagos ya devengados ni de obligaciones legales pendientes.",
                ],
            },
            {
                "titulo": "6. Ley aplicable y contacto",
                "parrafos": [
                    "Estos términos se interpretan conforme a las leyes aplicables de la República de Honduras, sin limitar los derechos irrenunciables de las personas consumidoras. Para consultas o reclamos escribe a soporte@orvendmart.com.",
                ],
            },
        ],
    )
    return render(request, "legal/documento.html", {"documento": documento})


def politica_reembolsos(request):
    documento = _documento_legal(
        "Política de reembolsos",
        "Esta política explica cómo solicitar revisión de un pago de suscripción de OrvendMart.",
        [
            {
                "titulo": "1. Solicitud",
                "parrafos": [
                    "Las solicitudes deben enviarse a soporte@orvendmart.com con el nombre del cliente, comprobante de pago, fecha, monto, motivo y un medio de contacto. Evaluaremos la solicitud y responderemos por el mismo canal o por el que se acuerde con el cliente.",
                ],
            },
            {
                "titulo": "2. Casos que se revisan",
                "lista": [
                    "Cobro duplicado o monto cobrado incorrectamente.",
                    "Pago aplicado a una cuenta equivocada por un error atribuible a la gestión del servicio.",
                    "Servicio contratado a distancia cuya prestación no haya iniciado, conforme a los derechos de revocación aplicables.",
                    "Indisponibilidad atribuible a OrvendMart que haga imposible usar las funciones esenciales durante un período relevante, evaluada según el caso y el acuerdo comercial.",
                ],
            },
            {
                "titulo": "3. Casos no automáticos",
                "parrafos": [
                    "Los períodos ya utilizados, los servicios de implementación, migración, capacitación, personalización o soporte ya prestados no generan reembolso automático. Cada solicitud se revisa sin limitar los derechos que establezca la ley aplicable.",
                ],
            },
            {
                "titulo": "4. Resolución y forma de devolución",
                "parrafos": [
                    "Cuando corresponda un reembolso, se procesará por el medio de pago original o por otro medio acordado y permitido, después de validar el pago. Informaremos el resultado y el plazo estimado; los tiempos bancarios o de terceros pueden variar.",
                ],
            },
            {
                "titulo": "5. Cancelación y datos",
                "parrafos": [
                    "La cancelación no activa por sí sola un reembolso. Antes del vencimiento, el cliente debe solicitar y resguardar las exportaciones que necesite. El acceso y la disponibilidad de datos se rigen por los Términos y condiciones y por las obligaciones legales aplicables.",
                ],
            },
        ],
    )
    return render(request, "legal/documento.html", {"documento": documento})


def suscripcion_vencida(request):
    estado = SuscripcionSistema.estado_actual()
    return render(request, "legal/suscripcion_vencida.html", {"suscripcion": estado})


@require_GET
def public_asset(request, asset_name):
    """Entrega únicamente los recursos institucionales aprobados públicamente."""
    content_type = PUBLIC_ASSETS.get(asset_name)
    if not content_type:
        raise Http404("Recurso público no encontrado.")

    asset_path = settings.PUBLIC_ASSETS_ROOT / asset_name
    if not asset_path.is_file():
        raise Http404("Recurso público no encontrado.")

    response = FileResponse(asset_path.open("rb"), content_type=content_type)
    response["Cache-Control"] = "public, max-age=86400"
    return response


def error_404(request, exception=None):
    """Página pública para rutas que no existen."""
    return render(request, "errors/404.html", status=404)


def error_403(request, exception=None):
    """Página pública para accesos bloqueados por permisos."""
    return render(request, "errors/403.html", status=403)


def error_500(request):
    """Página segura para errores internos.

    El detalle técnico solo se expone durante desarrollo. En producción puede
    contener rutas, datos o nombres internos que no deben mostrarse al cliente.
    """
    exception = sys.exc_info()[1]
    error_detail = str(exception) if settings.DEBUG and exception else None
    return render(
        request,
        "errors/500.html",
        {"error_detail": error_detail},
        status=500,
    )
