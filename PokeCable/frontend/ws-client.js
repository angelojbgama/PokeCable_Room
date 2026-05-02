window.POKECABLE_WS_CLIENT = {
  createWsClient({
    wsUrl,
    statusEl,
    onMessage,
    onClosed
  }) {
    let socket = null;
    let heartbeatTimer = null;

    function setDisconnected() {
      statusEl.textContent = "Desconectado";
      statusEl.classList.remove("online");
    }

    function setConnecting() {
      statusEl.textContent = "Conectando";
      statusEl.classList.remove("online");
    }

    function setOnline() {
      statusEl.textContent = "Online";
      statusEl.classList.add("online");
    }

    function clearHeartbeat() {
      if (heartbeatTimer) window.clearInterval(heartbeatTimer);
      heartbeatTimer = null;
    }

    function startHeartbeat() {
      clearHeartbeat();
      heartbeatTimer = window.setInterval(() => {
        if (socket && socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({ type: "heartbeat" }));
        }
      }, 20000);
    }

    function send(payload) {
      if (!socket || socket.readyState !== WebSocket.OPEN) throw new Error("WebSocket nao conectado.");
      socket.send(JSON.stringify(payload));
    }

    function close() {
      if (socket) socket.close();
    }

    let connectionPromise = null;

    function connect() {
      if (socket && socket.readyState === WebSocket.OPEN) {
        return Promise.resolve();
      }
      if (connectionPromise) {
        return connectionPromise;
      }

      connectionPromise = new Promise((resolve, reject) => {
        setConnecting();
        socket = new WebSocket(wsUrl());
        
        socket.addEventListener("open", () => {
          // Aguarda a mensagem 'connected' do servidor para resolver
        });

        socket.addEventListener("message", (event) => {
          const message = JSON.parse(event.data);
          if (message.type === "connected") {
            setOnline();
            startHeartbeat();
            onMessage?.(message);
            connectionPromise = null;
            resolve();
            return;
          }
          onMessage?.(message);
        });

        socket.addEventListener("close", () => {
          setDisconnected();
          clearHeartbeat();
          connectionPromise = null;
          onClosed?.();
        });

        socket.addEventListener("error", () => {
          connectionPromise = null;
          reject(new Error("Falha ao conectar no WebSocket."));
        });
      });

      return connectionPromise;
    }

    return {
      connect,
      send,
      close
    };
  }
};
