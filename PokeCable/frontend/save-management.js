window.POKECABLE_SAVE_MANAGEMENT = {
  createSaveManagementController({
    getLoadedSave,
    getSelectedLocation,
    setSelectedLocation,
    getSelectedInventoryItem,
    setSelectedInventoryItem,
    getPendingMoveSourceLocation,
    setPendingMoveSourceLocation,
    getTradeState,
    parseLocation,
    pokemonByLocation,
    locationLabel,
    cleanName,
    normalizePokemonDisplay,
    renderPokemonSummaryHtml,
    renderOfferCard,
    clearTradePreviews,
    relocatePokemonWithinSave,
    hasBagSpaceInSave,
    hasPcSpaceInSave,
    storeItemInBagForSave,
    storeItemInPcForSave,
    clearHeldItemInSave,
    setHeldItemInSave,
    removeItemFromPocket,
    refreshLoadedSaveCollections,
    nonHoldableCategories,
    syncTransientUi,
    syncAfterSaveMutation,
    activateTab,
    elements
  }) {
    let dragSourceLocation = null;

    const {
      tradeSelectedSummaryEl,
      setupSelectedSummaryEl,
      setupSelectionDetailEl,
      selectedInventoryItemStatusEl,
      saveManagementStatusEl,
      startMovePokemonButton,
      cancelMovePokemonButton,
      removeHeldItemButton,
      applyHeldItemButton,
      setupPartyPreviewEl,
      tradePartyPreviewEl,
      localOfferEl,
      localOfferDetailsEl
    } = elements;

    function partyCapacity(save) {
      return save?.generation === 3 ? 6 : Number(save?.layout?.partyCapacity || 6);
    }

    function updateManagementButtons() {
      const loadedSave = getLoadedSave();
      const selected = pokemonByLocation(loadedSave, getSelectedLocation());
      const canManage = Boolean(loadedSave && selected && !selected.is_egg);
      startMovePokemonButton.disabled = !canManage || Boolean(getPendingMoveSourceLocation());
      cancelMovePokemonButton.disabled = !getPendingMoveSourceLocation();
      removeHeldItemButton.disabled = !canManage || loadedSave?.generation === 1 || !selected?.held_item_id;
      applyHeldItemButton.disabled = !canManage || loadedSave?.generation === 1 || !getSelectedInventoryItem();
    }

    function updateSelectionUi() {
      const loadedSave = getLoadedSave();
      const selected = pokemonByLocation(loadedSave, getSelectedLocation());
      const label = selected ? selected.display_summary || normalizePokemonDisplay(selected) : "Nenhum Pokémon selecionado.";
      const locationText = selected ? locationLabel(selected.location, loadedSave?.boxes) : "Sem localização";
      tradeSelectedSummaryEl.textContent = label;
      if (setupSelectedSummaryEl) setupSelectedSummaryEl.textContent = label;
      if (setupSelectionDetailEl) {
        setupSelectionDetailEl.textContent = selected
          ? `${locationText}${getPendingMoveSourceLocation() ? ` · origem da movimentação: ${locationLabel(getPendingMoveSourceLocation(), loadedSave?.boxes)}` : ""}`
          : "Selecione um Pokémon da party ou do PC para trocar, mover ou editar item.";
      }
      if (selectedInventoryItemStatusEl) {
        const selectedInventoryItem = getSelectedInventoryItem();
        selectedInventoryItemStatusEl.textContent = selectedInventoryItem
          ? `Item selecionado: ${selectedInventoryItem.item_name} x${selectedInventoryItem.quantity} · ${selectedInventoryItem.pocket_name}`
          : "Nenhum item selecionado na mochila/PC.";
      }
      updateManagementButtons();
    }

    function renderPartyPreview(target, mode) {
      const loadedSave = getLoadedSave();
      const selectedLocation = getSelectedLocation();
      const pendingMoveSourceLocation = getPendingMoveSourceLocation();
      target.textContent = "";
      if (!loadedSave) return;
      const count = partyCapacity(loadedSave);
      const occupiedCount = Number((loadedSave.party || []).length);
      const byIndex = new Map((loadedSave.party || []).filter((item) => !item.is_egg).map((pokemon) => [parseLocation(pokemon.location).index, pokemon]));
      const showEmpty = mode === "setup" && Boolean(pendingMoveSourceLocation);
      for (let index = 0; index < count; index += 1) {
        const location = `party:${index}`;
        const pokemon = byIndex.get(index) || null;
        if (!pokemon && (!showEmpty || index !== occupiedCount)) continue;
        const item = document.createElement("button");
        item.type = "button";
        item.className = `team-preview-item team-preview-item-selectable${location === selectedLocation ? " is-selected" : ""}${pendingMoveSourceLocation === location ? " is-source" : ""}`;
        item.setAttribute("aria-pressed", location === selectedLocation ? "true" : "false");
        item.dataset.pokemonLocation = location;
        item.draggable = Boolean(pokemon);
        item.addEventListener("click", () => handlePokemonSelectionClick(location, mode));
        const name = document.createElement("div");
        name.className = "team-preview-name";
        if (pokemon) {
          name.innerHTML = renderPokemonSummaryHtml(pokemon);
        } else {
          name.innerHTML = `<span class="pokemon-summary"><span class="pokemon-summary-text">Slot vazio</span></span>`;
        }
        const meta = document.createElement("span");
        if (pendingMoveSourceLocation === location) {
          meta.textContent = "Origem da movimentação";
        } else if (location === selectedLocation && pokemon) {
          meta.textContent = mode === "trade" ? "Selecionado para a rodada" : "Selecionado";
        } else if (!pokemon) {
          meta.textContent = "Clique para mover aqui";
        } else {
          meta.textContent = mode === "trade" ? "Clique para selecionar" : "Clique para selecionar";
        }
        item.append(name, meta);
        target.append(item);
      }
    }

    function updateSetupPartyPreview() {
      renderPartyPreview(setupPartyPreviewEl, "setup");
    }

    function updateTradePartyPreview() {
      renderPartyPreview(tradePartyPreviewEl, "trade");
    }

    function setSelectedTradePokemon(location) {
      const loadedSave = getLoadedSave();
      if (getTradeState()?.roundActive) return;
      if (!loadedSave || !location) return;
      const selected = pokemonByLocation(loadedSave, location);
      if (!selected || selected.is_egg) return;
      setSelectedLocation(location);
      updateSelectionUi();
      renderOfferCard(localOfferEl, localOfferDetailsEl, selected, "", { emptyMessage: "Escolha um Pokémon da party ou do PC." });
      clearTradePreviews();
      updateSetupPartyPreview();
      updateTradePartyPreview();
      syncTransientUi?.();
    }

    function handlePokemonSelectionClick(location, tab = null) {
      const loadedSave = getLoadedSave();
      const pendingMoveSourceLocation = getPendingMoveSourceLocation();
      if (pendingMoveSourceLocation && pendingMoveSourceLocation !== location) {
        try {
          relocatePokemonWithinSave(loadedSave, pendingMoveSourceLocation, location);
          saveManagementStatusEl.textContent = `Pokémon movido: ${locationLabel(pendingMoveSourceLocation, loadedSave?.boxes)} → ${locationLabel(location, loadedSave?.boxes)}.`;
          setPendingMoveSourceLocation(null);
          setSelectedLocation(location);
          syncAfterSaveMutation?.();
          if (tab) activateTab(tab);
          return;
        } catch (error) {
          saveManagementStatusEl.textContent = error.message || String(error);
          setPendingMoveSourceLocation(null);
          updateSelectionUi();
          updateSetupPartyPreview();
          updateTradePartyPreview();
          syncTransientUi?.();
          return;
        }
      }
      setSelectedTradePokemon(location);
      if (tab) activateTab(tab);
    }

    function handlePokemonDragStart(location) {
      const loadedSave = getLoadedSave();
      const selected = pokemonByLocation(loadedSave, location);
      if (!selected || selected.is_egg) return;
      dragSourceLocation = location;
      setPendingMoveSourceLocation(location);
      saveManagementStatusEl.textContent = `Arrastando ${locationLabel(location, loadedSave?.boxes)}. Solte no destino para mover ou trocar.`;
      updateSelectionUi();
      updateSetupPartyPreview();
      updateTradePartyPreview();
      syncTransientUi?.();
    }

    function handlePokemonDrop(location, tab = null) {
      if (!dragSourceLocation) {
        handlePokemonSelectionClick(location, tab);
        return;
      }
      const sourceLocation = dragSourceLocation;
      dragSourceLocation = null;
      handlePokemonSelectionClick(location, tab);
      if (getPendingMoveSourceLocation() === sourceLocation) {
        setPendingMoveSourceLocation(null);
        syncTransientUi?.();
      }
    }

    function handlePokemonDragEnd() {
      if (!dragSourceLocation) return;
      dragSourceLocation = null;
      if (getPendingMoveSourceLocation()) {
        setPendingMoveSourceLocation(null);
        saveManagementStatusEl.textContent = "Movimentação por arrastar foi cancelada.";
        updateSelectionUi();
        updateSetupPartyPreview();
        updateTradePartyPreview();
        syncTransientUi?.();
      }
    }

    function startMovePokemon() {
      const loadedSave = getLoadedSave();
      const selected = pokemonByLocation(loadedSave, getSelectedLocation());
      if (!selected) return;
      setPendingMoveSourceLocation(selected.location);
      saveManagementStatusEl.textContent = `Movimentação armada a partir de ${locationLabel(selected.location, loadedSave?.boxes)}. Clique no destino para mover ou trocar.`;
      updateSelectionUi();
      updateSetupPartyPreview();
      updateTradePartyPreview();
      syncTransientUi?.();
    }

    function cancelMovePokemon() {
      setPendingMoveSourceLocation(null);
      saveManagementStatusEl.textContent = "Movimentação cancelada.";
      updateSelectionUi();
      updateSetupPartyPreview();
      updateTradePartyPreview();
      syncTransientUi?.();
    }

    function selectInventoryItem(itemId, pocketName, storage) {
      const loadedSave = getLoadedSave();
      if (!loadedSave) return;
      const selectedInventoryItem = (loadedSave.inventory || []).find(
        (entry) => Number(entry.item_id) === Number(itemId) && entry.pocket_name === pocketName && entry.storage === storage
      ) || null;
      setSelectedInventoryItem(selectedInventoryItem);
      if (selectedInventoryItem) {
        saveManagementStatusEl.textContent = `Item selecionado: ${selectedInventoryItem.item_name}. Selecione um Pokémon para equipar.`;
      }
      syncTransientUi?.();
      updateSelectionUi();
    }

    function removeHeldItemFromSelectedPokemon() {
      const loadedSave = getLoadedSave();
      const selected = pokemonByLocation(loadedSave, getSelectedLocation());
      if (!loadedSave || !selected) return;
      if (loadedSave.generation === 1) throw new Error("Gen 1 não suporta held item.");
      if (!selected.held_item_id) throw new Error("O Pokémon selecionado não está segurando item.");
      const itemId = Number(selected.held_item_id);
      const stored = hasBagSpaceInSave(loadedSave, itemId, 1)
        ? storeItemInBagForSave(loadedSave, itemId, 1)
        : hasPcSpaceInSave(loadedSave, itemId, 1)
          ? storeItemInPcForSave(loadedSave, itemId, 1)
          : null;
      if (!stored) throw new Error("Sem espaço na mochila nem no PC para remover o item.");
      clearHeldItemInSave(loadedSave, selected.location);
      refreshLoadedSaveCollections(loadedSave);
      saveManagementStatusEl.textContent = `Item removido de ${locationLabel(selected.location, loadedSave?.boxes)} e enviado para ${stored.storage === "pc" ? "PC" : "mochila"} (${stored.pocket_name}).`;
      syncAfterSaveMutation?.();
    }

    function applySelectedItemToPokemon() {
      const loadedSave = getLoadedSave();
      const selected = pokemonByLocation(loadedSave, getSelectedLocation());
      const selectedInventoryItem = getSelectedInventoryItem();
      if (!loadedSave || !selected) return;
      if (loadedSave.generation === 1) throw new Error("Gen 1 não suporta held item.");
      if (!selectedInventoryItem) throw new Error("Selecione um item da mochila ou do PC.");
      if (nonHoldableCategories.has(cleanName(selectedInventoryItem.category || "").toLowerCase())) {
        throw new Error("Esse item não pode ser segurado por um Pokémon.");
      }
      const previousItemId = selected.held_item_id ? Number(selected.held_item_id) : null;
      if (previousItemId) {
        const stored = hasBagSpaceInSave(loadedSave, previousItemId, 1)
          ? storeItemInBagForSave(loadedSave, previousItemId, 1)
          : hasPcSpaceInSave(loadedSave, previousItemId, 1)
            ? storeItemInPcForSave(loadedSave, previousItemId, 1)
            : null;
        if (!stored) throw new Error("Sem espaço para guardar o item que o Pokémon já segurava.");
      }
      removeItemFromPocket(loadedSave, selectedInventoryItem.pocket_name, Number(selectedInventoryItem.item_id), 1);
      setHeldItemInSave(loadedSave, selected.location, Number(selectedInventoryItem.item_id));
      const appliedName = selectedInventoryItem.item_name;
      setSelectedInventoryItem(null);
      refreshLoadedSaveCollections(loadedSave);
      saveManagementStatusEl.textContent = `${appliedName} equipado em ${locationLabel(selected.location, loadedSave?.boxes)}.`;
      syncAfterSaveMutation?.();
    }

    return {
      updateSelectionUi,
      updateManagementButtons,
      handlePokemonSelectionClick,
      startMovePokemon,
      cancelMovePokemon,
      selectInventoryItem,
      removeHeldItemFromSelectedPokemon,
      applySelectedItemToPokemon,
      updateSetupPartyPreview,
      updateTradePartyPreview,
      setSelectedTradePokemon,
      handlePokemonDragStart,
      handlePokemonDrop,
      handlePokemonDragEnd
    };
  }
};
