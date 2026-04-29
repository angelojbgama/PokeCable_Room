window.POKECABLE_TRADE_FLOW = {
  createTradeFlowController({
    state,
    getLoadedSave,
    getSelectedLocation,
    getSelectedPokemon,
    getRoomCredentials,
    getSessionAction,
    selectedPayload,
    supportedTradeModes,
    supportedProtocols,
    renderOfferCard,
    buildWebCompatibilityReport,
    renderTradeCompatibilityPreview,
    renderTradeEvolutionPreview,
    clearTradePreviews,
    send,
    setStatus,
    log,
    sha256Hex,
    downloadBlob,
    elements
  }) {
    const {
      confirmButton,
      cancelButton,
      sendOfferButton,
      downloadArea,
      peerOfferEl,
      peerOfferDetailsEl,
      localOfferEl,
      localOfferDetailsEl
    } = elements;

    function resetTradeRoundUi(options = {}) {
      const selected = getSelectedPokemon();
      state.localPayload = null;
      state.peerPayload = null;
      state.preparedTradeBackup = null;
      state.pendingTradePayload = null;
      state.roundActive = false;
      peerOfferEl.innerHTML = "-";
      peerOfferDetailsEl.className = "pokemon-card-details pokemon-card-details-empty";
      peerOfferDetailsEl.textContent = options.peerMessage || "Aguardando o Pokémon do outro jogador.";
      clearTradePreviews();
      renderOfferCard(localOfferEl, localOfferDetailsEl, selected || null, "", { emptyMessage: "Escolha um Pokémon da party." });
      confirmButton.disabled = true;
      cancelButton.disabled = !state.hasJoinedRoom || !state.roomReady;
      sendOfferButton.disabled = !state.hasJoinedRoom || !state.roomReady || !selected;
    }

    function syncButtons() {
      const selected = getSelectedPokemon();
      sendOfferButton.disabled = !state.hasJoinedRoom || !state.roomReady || !selected || Boolean(state.roundActive);
      cancelButton.disabled = !state.hasJoinedRoom || !state.roomReady;
    }

    function joinTradeRoom(action) {
      const { roomName, password } = getRoomCredentials();
      const loadedSave = getLoadedSave();
      if (!roomName || !password) {
        setStatus("Informe nome da sala e senha.");
        return;
      }
      if (!loadedSave) {
        setStatus("Carregue um save antes de entrar na sala.");
        return;
      }
      state.hasJoinedRoom = false;
      state.roomReady = false;
      resetTradeRoundUi();
      send({
        type: action === "create" ? "create_room" : "join_room",
        room_name: roomName,
        password,
        generation: loadedSave.generation,
        game: loadedSave.game,
        supported_trade_modes: supportedTradeModes(loadedSave.generation),
        supported_protocols: supportedProtocols()
      });
    }

    function sendOffer() {
      if (!state.hasJoinedRoom || !state.roomReady) {
        setStatus("A sala ainda nao esta pronta para troca.");
        return;
      }
      state.localPayload = selectedPayload();
      state.roundActive = true;
      renderOfferCard(localOfferEl, localOfferDetailsEl, state.localPayload, state.localPayload.display_summary);
      confirmButton.disabled = true;
      cancelButton.disabled = false;
      sendOfferButton.disabled = true;
      send({ type: "offer_pokemon", payload: state.localPayload });
      setStatus("Oferta enviada. Aguardando o outro jogador.");
      log("Oferta de troca enviada.");
    }

    async function handlePrepareWrite(message) {
      try {
        const loadedSave = getLoadedSave();
        if (!loadedSave) throw new Error("Nenhum save carregado no navegador.");
        const currentHash = await sha256Hex(loadedSave.bytes);
        const expected = loadedSave.signature || { size: loadedSave.bytes.length, sha256: currentHash };
        if (expected.size !== loadedSave.bytes.length || expected.sha256 !== currentHash) {
          send({
            type: "write_ready",
            ready: false,
            error: "save_changed_during_room",
            metadata: {
              error_code: "save_changed_during_room",
              message: "O save local carregado no navegador mudou antes da escrita.",
              expected_signature: expected,
              current_signature: { size: loadedSave.bytes.length, sha256: currentHash }
            }
          });
          setStatus("O save local mudou antes da escrita. Recarregue o arquivo e tente novamente.");
          return;
        }
        state.preparedTradeBackup = new Uint8Array(loadedSave.bytes);
        state.pendingTradePayload = message.received_payload;
        send({
          type: "write_ready",
          ready: true,
          metadata: {
            save_name: loadedSave.name,
            size: loadedSave.bytes.length,
            sha256: currentHash
          }
        });
        setStatus("Backup local preparado. Aguardando o outro jogador preparar também.");
        log("Preparação local concluída. Backup em memória pronto.");
      } catch (error) {
        send({ type: "write_ready", ready: false, error: error.message || String(error) });
        setStatus(error.message || String(error));
        log(`Falha na preparação de escrita: ${error.message || error}`);
      }
    }

    async function handleTradeCommitWrite(message) {
      try {
        const loadedSave = getLoadedSave();
        if (!loadedSave) throw new Error("Nenhum save carregado no navegador.");
        state.pendingTradePayload = message.received_payload;
        renderOfferCard(
          peerOfferEl,
          peerOfferDetailsEl,
          state.pendingTradePayload,
          state.pendingTradePayload.display_summary || (state.pendingTradePayload.summary && state.pendingTradePayload.summary.display_summary) || "-"
        );
        loadedSave.applyPayload(getSelectedLocation(), state.pendingTradePayload);
        send({ type: "write_done", success: true });
        setStatus("Commit autorizado. Save gravado. Aguardando confirmação remota.");
        log("Save aplicado localmente no navegador.");
      } catch (error) {
        send({ type: "write_failed", stage: "commit_write", error: error.message || String(error) });
        setStatus(error.message || String(error));
        log(`Erro ao aplicar save local: ${error.message || error}`);
      }
    }

    function handlePreflightRequired(message) {
      const payload = message.received_payload;
      state.peerPayload = payload;
      renderOfferCard(
        peerOfferEl,
        peerOfferDetailsEl,
        payload,
        payload.display_summary || (payload.summary && payload.summary.display_summary) || "-"
      );
      const report = buildWebCompatibilityReport(payload, message);
      const loadedSave = getLoadedSave();
      if (!loadedSave) {
        report.compatible = false;
        report.blocking_reasons.push("Nenhum save carregado.");
      } else if (!(payload.raw_data_base64 || (payload.raw && payload.raw.data_base64))) {
        if (payload.generation === loadedSave.generation) {
          report.compatible = false;
          report.blocking_reasons.push("Payload same-generation sem raw data.");
        }
      }
      renderTradeCompatibilityPreview(payload, report);
      renderTradeEvolutionPreview(payload, report);
      send({
        type: "preflight_result",
        compatible: report.compatible,
        requires_user_confirmation: false,
        report,
        error: report.blocking_reasons.join("; ")
      });
      if (report.compatible) {
        setStatus("Preflight local aprovado. Aguardando o outro usuário.");
        log("Preflight local aprovado.");
      } else {
        setStatus(report.blocking_reasons.join(" "));
        confirmButton.disabled = true;
        log(`Preflight local bloqueado: ${report.blocking_reasons.join("; ")}`);
      }
    }

    function handleTradeMessage(message) {
      switch (message.type) {
        case "room_created":
          state.hasJoinedRoom = true;
          state.roomReady = false;
          setStatus("Sala de troca criada. Aguardando o segundo usuário.");
          log("Sala de troca criada.");
          syncButtons();
          return true;
        case "room_waiting":
          state.roomReady = false;
          if (state.hasJoinedRoom) setStatus(message.message || "Aguardando outro usuario.");
          log("Sala de troca aguardando segundo usuário.");
          syncButtons();
          return true;
        case "room_joined":
          state.hasJoinedRoom = true;
          state.roomReady = false;
          setStatus("Entrou na sala de troca. Aguardando sincronização com o outro jogador.");
          log("Entrou na sala de troca.");
          syncButtons();
          return true;
        case "room_ready":
          state.hasJoinedRoom = true;
          state.roomReady = true;
          setStatus("Sala de troca pronta. Escolha um Pokémon e envie a oferta.");
          log("Sala de troca pronta com dois usuários.");
          syncButtons();
          return true;
        case "room_context_updated":
          state.hasJoinedRoom = true;
          state.roomReady = Boolean(message.room && message.room.players && Object.keys(message.room.players).length === 2);
          resetTradeRoundUi({ peerMessage: "Contexto da sala atualizado. Aguardando nova oferta." });
          setStatus("Contexto da sala de troca atualizado. Escolha um Pokémon e envie nova oferta.");
          log("Sala de troca atualizada após mudança de save.");
          return true;
        case "offer_received":
          log("Servidor recebeu sua oferta.");
          return true;
        case "peer_offer_received":
          state.peerPayload = message.offer;
          renderOfferCard(
            peerOfferEl,
            peerOfferDetailsEl,
            state.peerPayload,
            state.peerPayload.display_summary || (state.peerPayload.summary && state.peerPayload.summary.display_summary) || "-"
          );
          setStatus("Oferta do outro usuário recebida. Validando compatibilidade.");
          confirmButton.disabled = true;
          log(`Outro usuário oferece: ${state.peerPayload.display_summary || (state.peerPayload.summary && state.peerPayload.summary.display_summary) || "-"}`);
          return true;
        case "offers_ready":
          log("As duas ofertas de troca estão prontas.");
          return true;
        case "preflight_required":
          handlePreflightRequired(message);
          return true;
        case "preflight_received":
          log("Preflight enviado ao servidor.");
          return true;
        case "preflight_ready":
          setStatus("Compatibilidade validada nos dois lados. Confirme para concluir.");
          confirmButton.disabled = false;
          log("Preflight aprovado pelos dois usuários.");
          return true;
        case "trade_blocked":
          state.roundActive = false;
          setStatus(message.message || "Troca bloqueada no preflight.");
          confirmButton.disabled = true;
          syncButtons();
          log(`Troca bloqueada: ${message.message || "preflight"}`);
          return true;
        case "trade_confirmed":
          setStatus("Sua confirmação foi enviada. Aguardando o outro usuário.");
          log("Confirmação de troca enviada.");
          return true;
        case "prepare_write":
          void handlePrepareWrite(message);
          return true;
        case "write_ready_received":
          log("Servidor recebeu sua preparação de escrita.");
          return true;
        case "trade_commit_write":
          void handleTradeCommitWrite(message);
          return true;
        case "write_done_received":
          log("Servidor recebeu a confirmação de gravação local.");
          return true;
        case "peer_confirmed":
          log("O outro usuário confirmou a troca.");
          return true;
        case "trade_completed": {
          const loadedSave = getLoadedSave();
          const receivedSummary = state.pendingTradePayload?.display_summary || state.peerPayload?.display_summary || "-";
          if (state.preparedTradeBackup && loadedSave) {
            downloadArea.textContent = "";
            downloadBlob(`${loadedSave.name}.bak`, state.preparedTradeBackup, "Baixar backup original");
            downloadBlob(loadedSave.name, loadedSave.bytes, "Baixar save modificado");
          }
          if (loadedSave) {
            void sha256Hex(loadedSave.bytes).then((hash) => {
              loadedSave.signature = { size: loadedSave.bytes.length, sha256: hash };
            });
          }
          resetTradeRoundUi({ peerMessage: "A sala continua pronta para uma nova troca." });
          setStatus(`Troca concluída. Recebido: ${receivedSummary}. A sala continua pronta para nova rodada.`);
          log("Troca concluída. A sala continua aberta.");
          return true;
        }
        case "trade_write_failed":
          resetTradeRoundUi({ peerMessage: "A rodada falhou. A sala continua pronta para tentar novamente." });
          setStatus(message.message || "Falha durante a preparação/gravação da troca.");
          log(`Falha de escrita da troca: ${message.message || message.stage}`);
          return true;
        case "trade_round_cancelled":
          resetTradeRoundUi({ peerMessage: "Rodada cancelada. A sala continua pronta." });
          setStatus("Rodada de troca cancelada. A sala continua pronta para nova oferta.");
          log(`Rodada de troca cancelada: ${message.reason || "cancelled"}`);
          return true;
        case "trade_cancelled":
          if (message.reason === "peer_disconnected") {
            state.roomReady = false;
            resetTradeRoundUi({ peerMessage: "Aguardando o Pokémon do outro jogador." });
            setStatus("Outro usuário desconectou. A sala continua aberta aguardando novo usuário.");
          } else {
            state.hasJoinedRoom = false;
            state.roomReady = false;
            resetTradeRoundUi({ peerMessage: "Aguardando o Pokémon do outro jogador." });
            setStatus(`Sala de troca encerrada: ${message.reason}`);
          }
          log(`Troca cancelada: ${message.reason}`);
          return true;
        default:
          return false;
      }
    }

    return {
      joinTradeRoom,
      sendOffer,
      resetTradeRoundUi,
      handleTradeMessage,
      syncButtons,
      isRoomJoined: () => state.hasJoinedRoom
    };
  }
};
