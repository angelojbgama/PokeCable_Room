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
      const byIndex = new Map((loadedSave.party || []).filter((item) => !item.is_egg).map((pokemon) => [parseLocation(pokemon.location).index, pokemon]));

      // Limpar instâncias antigas se houver
      if (target._sortable) {
        target._sortable.destroy();
        delete target._sortable;
      }

      for (let index = 0; index < count; index += 1) {
        const location = `party:${index}`;
        const pokemon = byIndex.get(index) || null;

        const item = document.createElement("button");
        item.type = "button";
        item.className = `team-preview-item team-preview-item-selectable${location === selectedLocation ? " is-selected" : ""}${pendingMoveSourceLocation === location ? " is-source" : ""}${!pokemon ? " is-empty" : ""}`;
        item.setAttribute("aria-pressed", location === selectedLocation ? "true" : "false");
        item.dataset.pokemonLocation = location;
        item.dataset.index = index;

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
        } else if (pendingMoveSourceLocation) {
          meta.textContent = "Clique para mover aqui";
        } else if (pokemon) {
          meta.textContent = "Arraste para organizar ou clique para selecionar";
        } else {
          meta.textContent = "Slot vazio";
        }
        item.append(name, meta);
        target.append(item);
      }

      // Initialize SortableJS
      if (typeof Sortable !== "undefined" && !pendingMoveSourceLocation) {
        let originalLocations = [];
        target._sortable = new Sortable(target, {
          animation: 150,
          ghostClass: "sortable-ghost",
          dragClass: "sortable-drag",
          filter: ".is-source", // Don't allow dragging the source of a manual move
          onStart: () => {
            const tradeState = getTradeState();
            if (tradeState?.roundActive) {
              saveManagementStatusEl.textContent = "Não é possível organizar a party enquanto uma oferta de troca está ativa.";
              return false;
            }
            // Capture locations before DOM reordering
            originalLocations = Array.from(target.children).map(el => el.dataset.pokemonLocation);
          },
          onMove: () => {
            const tradeState = getTradeState();
            if (tradeState?.roundActive) return false;
          },
          onEnd: (evt) => {
            const { oldIndex, newIndex } = evt;
            if (oldIndex === newIndex) return;

            const sourceLocation = originalLocations[oldIndex];
            const targetLocation = originalLocations[newIndex];

            if (!sourceLocation || !targetLocation || sourceLocation === targetLocation) {
              updateSetupPartyPreview();
              updateTradePartyPreview();
              return;
            }

            try {
              const currentSelected = getSelectedLocation();
              let newSelectedLocation = currentSelected;

              // Logic to track the selected pokemon
              if (currentSelected === sourceLocation) {
                newSelectedLocation = targetLocation;
              } else if (currentSelected === targetLocation) {
                newSelectedLocation = sourceLocation;
              }

              relocatePokemonWithinSave(loadedSave, sourceLocation, targetLocation);
              saveManagementStatusEl.textContent = `Party organizada: ${locationLabel(sourceLocation, loadedSave?.boxes)} ↔ ${locationLabel(targetLocation, loadedSave?.boxes)}.`;

              syncAfterSaveMutation?.();

              if (newSelectedLocation && (newSelectedLocation === sourceLocation || newSelectedLocation === targetLocation)) {
                setSelectedTradePokemon(newSelectedLocation);
              } else {
                updateSelectionUi();
                updateSetupPartyPreview();
                updateTradePartyPreview();
              }
            } catch (error) {
              saveManagementStatusEl.textContent = error.message || String(error);
              updateSetupPartyPreview();
              updateTradePartyPreview();
            }
          }
        });
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
      clearTradePreviews(); // Limpar ANTES de renderizar o novo card
      renderOfferCard(localOfferEl, localOfferDetailsEl, selected, "", { emptyMessage: "Escolha um Pokémon da party ou do PC." });
      updateSetupPartyPreview();
      updateTradePartyPreview();
      syncTransientUi?.();
    }

    function handlePokemonSelectionClick(location, tab = null) {
      const loadedSave = getLoadedSave();
      const pendingMoveSourceLocation = getPendingMoveSourceLocation();
      const tradeState = getTradeState();
      if (pendingMoveSourceLocation && pendingMoveSourceLocation !== location) {
        if (tradeState?.roundActive) {
          saveManagementStatusEl.textContent = "Não é possível mover Pokémon enquanto uma oferta de troca está ativa.";
          setPendingMoveSourceLocation(null);
          updateSelectionUi();
          updateSetupPartyPreview();
          updateTradePartyPreview();
          syncTransientUi?.();
          return;
        }
        try {
          const currentSelected = getSelectedLocation();
          let newSelectedLocation = location;
          if (currentSelected === pendingMoveSourceLocation) {
            newSelectedLocation = location;
          } else if (currentSelected === location) {
            const targetPokemon = pokemonByLocation(loadedSave, location);
            if (targetPokemon) {
              newSelectedLocation = pendingMoveSourceLocation;
            }
          } else {
            newSelectedLocation = currentSelected;
          }

          relocatePokemonWithinSave(loadedSave, pendingMoveSourceLocation, location);
          saveManagementStatusEl.textContent = `Pokémon movido: ${locationLabel(pendingMoveSourceLocation, loadedSave?.boxes)} → ${locationLabel(location, loadedSave?.boxes)}.`;
          setPendingMoveSourceLocation(null);

          syncAfterSaveMutation?.();

          if (newSelectedLocation) {
            setSelectedTradePokemon(newSelectedLocation);
          } else {
            setSelectedLocation(location);
            updateSelectionUi();
            updateSetupPartyPreview();
            updateTradePartyPreview();
          }

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
      setSelectedTradePokemon
    };
  }
};
