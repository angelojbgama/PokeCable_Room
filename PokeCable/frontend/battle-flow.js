window.POKECABLE_BATTLE_FLOW = {
  createBattleFlowController({
    state,
    getLoadedSave,
    getRoomCredentials,
    send,
    setStatus,
    setBattleStatus,
    log,
    battleLog,
    elements
  }) {
    const {
      battleLogEl,
      battleActionsEl,
      battleFormatEl,
      battleTeamCountEl,
      confirmBattleButton,
      sendBattleTeamButton,
      forfeitBattleButton
    } = elements;

    function setBattleActionsEnabled(enabled) {
      for (const button of battleActionsEl.querySelectorAll("[data-battle-action]")) button.disabled = !enabled;
    }

    function renderBattleActions(request = null) {
      battleActionsEl.innerHTML = "";
      const actions = [];
      if (request && Array.isArray(request.active) && request.active[0] && Array.isArray(request.active[0].moves)) {
        request.active[0].moves.forEach((move, index) => {
          if (move.disabled) return;
          actions.push({
            action: `move ${index + 1}`,
            label: `${move.move} (${move.pp}/${move.maxpp})`,
            secondary: false
          });
        });
      }
      if (request && request.forceSwitch && request.side && Array.isArray(request.side.pokemon)) {
        request.side.pokemon.forEach((pokemon, index) => {
          if (pokemon.active) return;
          if (String(pokemon.condition || "").includes("fnt")) return;
          actions.push({
            action: `switch ${index + 1}`,
            label: `Trocar ${pokemon.details || pokemon.ident || `Pokémon ${index + 1}`}`,
            secondary: true
          });
        });
      }
      if (!actions.length) {
        actions.push({ action: "move 1", label: "Golpe 1", secondary: false });
        actions.push({ action: "pass", label: "Passar", secondary: true });
      }
      for (const item of actions) {
        const button = document.createElement("button");
        button.type = "button";
        button.dataset.battleAction = item.action;
        button.textContent = item.label;
        if (item.secondary) button.classList.add("secondary");
        button.disabled = true;
        battleActionsEl.append(button);
      }
    }

    function battleFormatLabel(room) {
      const formatId = room?.format_id || "automatico";
      if (formatId === "gen1customgame") return "Gen 1 Custom Game";
      if (formatId === "gen2customgame") return "Gen 2 Custom Game";
      if (formatId === "gen3customgame") return "Gen 3 Custom Game";
      return formatId;
    }

    function updateBattleRoomDisplay(room) {
      if (!room) return;
      battleFormatEl.textContent = battleFormatLabel(room);
      const players = room.players || {};
      const teamSizes = Object.values(players).map((player) => `${player.team_size || 0}`);
      if (teamSizes.length) battleTeamCountEl.textContent = teamSizes.join(" x ");
    }

    function syncButtons() {
      const loadedSave = getLoadedSave();
      const hasTeam = Boolean(loadedSave && loadedSave.party && loadedSave.party.some((pokemon) => !pokemon.is_egg));
      sendBattleTeamButton.disabled = !state.hasJoinedBattleRoom || !state.roomReady || !hasTeam || Boolean(state.currentBattleId);
      confirmBattleButton.disabled = !state.readyToConfirm;
      forfeitBattleButton.disabled = !state.hasJoinedBattleRoom || (!state.currentBattleId && !state.roomReady);
    }

    function battleTeam() {
      const loadedSave = getLoadedSave();
      if (!loadedSave) throw new Error("Escolha um save local.");
      const team = loadedSave.party
        .filter((pokemon) => !pokemon.is_egg)
        .slice(0, 6)
        .map((pokemon) => {
          const payload = loadedSave.exportPayload(pokemon.location);
          const canonical = payload.canonical;
          if (canonical && canonical.original_data) {
            canonical.original_data = { ...canonical.original_data, raw_data_base64: null };
          }
          return canonical;
        });
      if (!team.length) throw new Error("A party nao possui Pokemon validos para batalha.");
      return team;
    }

    function joinBattleRoom(action) {
      const { roomName, password } = getRoomCredentials();
      const loadedSave = getLoadedSave();
      if (!roomName || !password) {
        setStatus("Informe nome da sala e senha.");
        return;
      }
      if (!loadedSave || !loadedSave.party.length) {
        setStatus("Carregue um save com party antes da batalha.");
        return;
      }
      state.hasJoinedBattleRoom = false;
      state.roomReady = false;
      state.readyToConfirm = false;
      state.currentBattleId = null;
      state.currentBattleRequest = null;
      battleLogEl.textContent = "";
      renderBattleActions(null);
      setBattleActionsEnabled(false);
      syncButtons();
      send({
        type: action === "create" ? "create_battle_room" : "join_battle_room",
        room_name: roomName,
        password,
        generation: loadedSave.generation,
        game: loadedSave.game
      });
    }

    function sendBattleTeam() {
      if (!state.hasJoinedBattleRoom || !state.roomReady) {
        setBattleStatus("A sala ainda nao esta pronta para batalha.");
        return;
      }
      const team = battleTeam();
      battleTeamCountEl.textContent = `${team.length} Pokémon enviados`;
      state.readyToConfirm = false;
      syncButtons();
      send({ type: "offer_battle_team", team });
      setBattleStatus("Time enviado. Aguardando o outro jogador.");
      log("Time de batalha enviado.");
    }

    function handleBattleMessage(message) {
      switch (message.type) {
        case "battle_error":
          setBattleStatus(message.message || "Erro na batalha.");
          state.currentBattleRequest = null;
          state.readyToConfirm = false;
          renderBattleActions(null);
          setBattleActionsEnabled(false);
          syncButtons();
          log(`Erro de batalha: ${message.message || message.code}`);
          return true;
        case "battle_waiting":
          state.roomReady = false;
          setBattleStatus(message.message || "Aguardando segundo usuário para batalha.");
          syncButtons();
          return true;
        case "battle_room_created":
          state.hasJoinedBattleRoom = true;
          state.roomReady = false;
          updateBattleRoomDisplay(message.room);
          setBattleStatus("Sala de batalha criada. Aguardando segundo usuário.");
          log("Sala de batalha criada.");
          syncButtons();
          return true;
        case "battle_room_joined":
          state.hasJoinedBattleRoom = true;
          state.roomReady = false;
          updateBattleRoomDisplay(message.room);
          setBattleStatus("Entrou na sala de batalha. Envie seu time quando quiser.");
          log("Entrou na sala de batalha.");
          syncButtons();
          return true;
        case "battle_room_ready":
          state.hasJoinedBattleRoom = true;
          state.roomReady = true;
          updateBattleRoomDisplay(message.room);
          setBattleStatus("Sala de batalha pronta. Envie seu time.");
          log("Sala de batalha pronta.");
          syncButtons();
          return true;
        case "battle_room_updated":
          state.hasJoinedBattleRoom = true;
          state.roomReady = Boolean(message.room && message.room.players && Object.keys(message.room.players).length === 2);
          state.readyToConfirm = false;
          state.currentBattleId = null;
          state.currentBattleRequest = null;
          updateBattleRoomDisplay(message.room);
          renderBattleActions(null);
          setBattleActionsEnabled(false);
          setBattleStatus("Sala de batalha atualizada após mudança de save. Envie um novo time.");
          log("Sala de batalha atualizada após mudança de save.");
          syncButtons();
          return true;
        case "battle_team_received":
          updateBattleRoomDisplay(message.room);
          setBattleStatus(`Servidor recebeu seu time (${message.team_size || 0} Pokémon).`);
          log("Servidor recebeu seu time de batalha.");
          return true;
        case "battle_ready":
          state.readyToConfirm = true;
          updateBattleRoomDisplay(message.room);
          setBattleStatus("Times prontos. Confirme para iniciar.");
          syncButtons();
          log("Batalha pronta para confirmação.");
          return true;
        case "battle_confirmed":
          state.readyToConfirm = false;
          syncButtons();
          setBattleStatus("Confirmação enviada. Aguardando o outro jogador.");
          log("Confirmação de batalha enviada.");
          return true;
        case "battle_started":
          state.currentBattleId = message.battle_id;
          state.currentBattleRequest = null;
          state.readyToConfirm = false;
          updateBattleRoomDisplay(message.room);
          setBattleStatus("Batalha iniciada. Aguarde sua ação.");
          renderBattleActions(null);
          setBattleActionsEnabled(false);
          for (const line of message.logs || []) battleLog(line);
          syncButtons();
          log("Batalha iniciada.");
          return true;
        case "battle_log":
          for (const line of message.logs || []) battleLog(line);
          return true;
        case "battle_request_action":
          state.currentBattleId = message.battle_id || state.currentBattleId;
          state.currentBattleRequest = message.request || null;
          setBattleStatus("Escolha uma ação de batalha.");
          renderBattleActions(state.currentBattleRequest);
          setBattleActionsEnabled(true);
          battleLog(state.currentBattleRequest ? "|request|ação disponível para este jogador" : "|request|escolha um golpe ou passe o turno");
          syncButtons();
          return true;
        case "battle_finished":
          state.currentBattleId = null;
          state.currentBattleRequest = null;
          state.readyToConfirm = false;
          if (message.reason === "peer_disconnected") {
            state.roomReady = false;
            setBattleStatus("O outro jogador saiu. A sala continua aguardando novo oponente.");
          } else {
            setBattleStatus("Batalha finalizada. A sala continua pronta para nova batalha.");
          }
          for (const line of message.logs || []) battleLog(line);
          renderBattleActions(null);
          setBattleActionsEnabled(false);
          syncButtons();
          log("Batalha finalizada.");
          return true;
        default:
          return false;
      }
    }

    function handleBattleServerError(message) {
      setBattleStatus(message.message || "Erro no servidor.");
      state.currentBattleRequest = null;
      state.readyToConfirm = false;
      renderBattleActions(null);
      setBattleActionsEnabled(false);
      syncButtons();
    }

    function handleBattleSocketClosed() {
      state.currentBattleId = null;
      state.currentBattleRequest = null;
      state.readyToConfirm = false;
      state.hasJoinedBattleRoom = false;
      state.roomReady = false;
      renderBattleActions(null);
      setBattleActionsEnabled(false);
      syncButtons();
      if (battleLogEl) battleLogEl.textContent += "";
      setBattleStatus("Conexão de batalha encerrada.");
    }

    function resetBattleUiForContextChange() {
      state.currentBattleId = null;
      state.currentBattleRequest = null;
      state.readyToConfirm = false;
      renderBattleActions(null);
      setBattleActionsEnabled(false);
      syncButtons();
    }

    return {
      joinBattleRoom,
      sendBattleTeam,
      resetBattleUiForContextChange,
      handleBattleMessage,
      handleBattleServerError,
      handleBattleSocketClosed,
      handleBattleActionClick(event) {
        const button = event.target.closest("[data-battle-action]");
        if (!button) return false;
        const action = button.dataset.battleAction || "pass";
        setBattleActionsEnabled(false);
        setBattleStatus(`Ação enviada: ${action}.`);
        send({ type: "battle_action", battle_id: state.currentBattleId, action });
        return true;
      },
      handleBattleConfirm() {
        state.readyToConfirm = false;
        syncButtons();
        setBattleStatus("Confirmação enviada. Aguardando início da batalha.");
        send({ type: "confirm_battle" });
      },
      handleBattleForfeit() {
        setBattleActionsEnabled(false);
        setBattleStatus("Desistência enviada.");
        send({ type: "battle_forfeit" });
      },
      renderBattleActions,
      updateBattleRoomDisplay,
      syncButtons,
      isBattleJoined: () => state.hasJoinedBattleRoom
    };
  }
};
