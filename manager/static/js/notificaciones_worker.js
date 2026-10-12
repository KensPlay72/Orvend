const clientes = new Set();
let socket;
let ultimoEstado;
let reintento = 0;
let temporizadorReconexion;
let temporizadorInactividad;

const notificarClientes = (mensaje) => {
  for (const cliente of clientes) {
    try {
      cliente.postMessage(mensaje);
    } catch (_) {
      retirarCliente(cliente);
    }
  }
};

const programarReconexion = () => {
  if (!clientes.size || temporizadorReconexion) return;
  const espera = Math.min(1000 * 2 ** reintento, 15000);
  reintento += 1;
  temporizadorReconexion = setTimeout(() => {
    temporizadorReconexion = null;
    conectar();
  }, espera);
};

const programarCierrePorInactividad = () => {
  if (clientes.size || temporizadorInactividad) return;
  temporizadorInactividad = setTimeout(() => {
    temporizadorInactividad = null;
    if (clientes.size) return;
    clearTimeout(temporizadorReconexion);
    temporizadorReconexion = null;
    socket?.close(1000, "Sin páginas activas");
    socket = null;
    ultimoEstado = null;
  }, 30000);
};

const retirarCliente = (cliente) => {
  if (!clientes.delete(cliente)) return;
  programarCierrePorInactividad();
};

const conectar = () => {
  if (!clientes.size || socket?.readyState === WebSocket.OPEN ||
      socket?.readyState === WebSocket.CONNECTING) return;

  const protocolo = self.location.protocol === "https:" ? "wss" : "ws";
  try {
    socket = new WebSocket(`${protocolo}://${self.location.host}/ws/notificaciones/`);
  } catch (_) {
    programarReconexion();
    return;
  }

  socket.addEventListener("open", () => {
    reintento = 0;
  });
  socket.addEventListener("message", (event) => {
    try {
      const mensaje = JSON.parse(event.data);
      if (mensaje.tipo !== "estado_notificaciones") return;
      ultimoEstado = mensaje;
      notificarClientes(mensaje);
    } catch (_) {
      return;
    }
  });
  socket.addEventListener("close", (event) => {
    if (socket?.readyState === WebSocket.CLOSED) socket = null;
    if (event.code !== 4401 && event.code !== 4403) programarReconexion();
  });
};

self.onconnect = (event) => {
  const cliente = event.ports[0];
  clientes.add(cliente);
  clearTimeout(temporizadorInactividad);
  temporizadorInactividad = null;
  cliente.onmessage = (mensaje) => {
    if (ultimoEstado) cliente.postMessage(ultimoEstado);
    conectar();
  };
  cliente.addEventListener("close", () => retirarCliente(cliente), { once: true });
  cliente.start();
};
