window.POKECABLE_INVENTORY_UI = {
  createInventoryUiController({
    getLoadedSave,
    getSelectedLocation,
    getSelectedInventoryItem,
    getPendingMoveSourceLocation,
    getBoxCapacity,
    cleanName,
    escapeHtml,
    escapeAttribute,
    renderPokemonSummaryHtml,
    elements
  }) {
    const genderRates = window.POKECABLE_GENDER_RATES || [];
    const {
      setupBagPreviewEl,
      setupPcPreviewEl,
      setupPokemonPcPreviewEl,
      tradeBoxPreviewEl,
      setupTogglePokemonPcButton,
      tradeTogglePokemonPcButton,
      pokemonDetailDrawerEl,
      pokemonDetailDrawerBackdropEl,
      pokemonDetailDrawerTitleEl,
      pokemonDetailDrawerBodyEl
    } = elements;

    const activeBoxByView = {
      setup: null,
      trade: null
    };
    const pcVisibleByView = {
      setup: false,
      trade: false
    };
    let detailDrawerPokemon = null;

    function itemSpriteSlug(entry) {
      const source = String(entry.item_name || "")
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/['.]/g, "")
        .replace(/[^a-zA-Z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "")
        .toLowerCase();
      return source || "poke-ball";
    }

    function itemSpriteHtml(entry) {
      const category = cleanName(entry.category || "item").toLowerCase() || "item";
      const label = escapeAttribute(entry.item_name || "Item");
      const spriteUrl = `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/${escapeAttribute(itemSpriteSlug(entry))}.png`;
      return `
        <span class="item-sprite-wrap" title="${label}">
          <img class="item-sprite-image" src="${spriteUrl}" alt="${label}" loading="lazy" onerror="this.style.display='none';this.nextElementSibling.style.display='inline-block';" />
          <span class="item-sprite item-sprite-fallback item-sprite-${escapeAttribute(category)}" aria-hidden="true" style="display:none;"></span>
        </span>
      `;
    }

    function renderInventoryPocketPreview(title, entries, { selectable = false } = {}) {
      const selectedInventoryItem = getSelectedInventoryItem();
      if (!entries.length) return "";
      const rows = entries
        .sort((left, right) => cleanName(left.item_name).localeCompare(cleanName(right.item_name)))
        .map((entry) => `
          <button type="button" class="inventory-item inventory-item-selectable${selectedInventoryItem && selectedInventoryItem.item_id === entry.item_id && selectedInventoryItem.pocket_name === entry.pocket_name ? " is-selected" : ""}" ${selectable ? `data-item-id="${Number(entry.item_id)}" data-pocket-name="${escapeAttribute(entry.pocket_name)}" data-storage="${escapeAttribute(entry.storage)}"` : "disabled"}>
            <span class="inventory-item-label">${itemSpriteHtml(entry)}${escapeHtml(entry.item_name)} x${Number(entry.quantity || 0)}</span>
            <span class="inventory-item-meta">${escapeHtml(`${entry.category || "item"} · ${entry.pocket_name}`)}</span>
          </button>
        `)
        .join("");
      return `
        <div class="inventory-pocket">
          <strong>${escapeHtml(title)}</strong>
          <div class="inventory-list">${rows}</div>
        </div>
      `;
    }

    function updateInventoryPreview() {
      const loadedSave = getLoadedSave();
      if (!loadedSave || !loadedSave.inventory?.length) {
        setupBagPreviewEl.className = "inventory-preview-body inventory-preview-empty";
        setupBagPreviewEl.textContent = loadedSave ? "Este save não possui itens visíveis na mochila." : "Carregue um save para visualizar os pockets da mochila.";
        setupPcPreviewEl.className = "inventory-preview-body inventory-preview-empty";
        setupPcPreviewEl.textContent = loadedSave ? "Este save não possui itens guardados no PC." : "Carregue um save para visualizar os itens guardados no PC.";
        return;
      }
      const bagEntries = loadedSave.inventory.filter((entry) => entry.storage === "bag");
      const pcEntries = loadedSave.inventory.filter((entry) => entry.storage === "pc");
      const bagHtml = [
        renderInventoryPocketPreview("Itens", bagEntries.filter((entry) => entry.pocket_name === "bag_items" || entry.pocket_name === "items"), { selectable: true }),
        renderInventoryPocketPreview("Poké Bolas", bagEntries.filter((entry) => entry.pocket_name === "balls"), { selectable: true }),
        renderInventoryPocketPreview("Itens-chave", bagEntries.filter((entry) => entry.pocket_name === "key_items"), { selectable: true }),
        renderInventoryPocketPreview("TM / HM", bagEntries.filter((entry) => entry.pocket_name === "tm_hm"), { selectable: true }),
        renderInventoryPocketPreview("Berries", bagEntries.filter((entry) => entry.pocket_name === "berries"), { selectable: true })
      ].filter(Boolean).join("");
      const pcHtml = renderInventoryPocketPreview("Itens armazenados", pcEntries.filter((entry) => entry.pocket_name === "pc_items"), { selectable: true });
      setupBagPreviewEl.className = "inventory-preview-body";
      setupBagPreviewEl.innerHTML = bagHtml || '<div class="inventory-preview-empty">A mochila deste save está vazia.</div>';
      setupPcPreviewEl.className = "inventory-preview-body";
      setupPcPreviewEl.innerHTML = pcHtml || '<div class="inventory-preview-empty">O PC de itens deste save está vazio.</div>';
    }

    function pokemonInfoHtml(pokemon) {
      const locationText = (() => {
        if (String(pokemon.location || "").startsWith("party:")) {
          const index = Number(String(pokemon.location).split(":")[1] || 0);
          return `Party · Slot ${index + 1}`;
        }
        if (String(pokemon.location || "").startsWith("box:")) {
          const boxName = getLoadedSave()?.boxes?.box_names?.[Number(pokemon.box_index || 0)] || `Box ${Number(pokemon.box_index || 0) + 1}`;
          return `${boxName} · Box ${Number(pokemon.box_index || 0) + 1} · Slot ${Number(pokemon.slot_index || 0) + 1}`;
        }
        return cleanName(pokemon.location || "Local desconhecido");
      })();
      const moves = (pokemon.moves || [])
        .map((move) => cleanName(move.name || move.move_name || `Move #${move.move_id || "?"}`))
        .filter(Boolean)
        .join(" · ");
      const facts = [
        pokemon.display_summary ? `Resumo: ${escapeHtml(pokemon.display_summary)}` : "",
        `Localização: ${escapeHtml(locationText)}`,
        `Nível: ${Number(pokemon.level || 1)}`,
        Number.isFinite(Number(pokemon.experience)) ? `Experiência: ${Number(pokemon.experience)}` : "",
        pokemon.nickname ? `Apelido: ${escapeHtml(pokemon.nickname)}` : "",
        `Sexo: ${escapeHtml(
          cleanName(pokemon.gender || pokemon.metadata?.gender || "")
          || (
            Number(pokemon.generation || 0) === 1
              ? "Não disponível na Gen 1"
              : (Number(pokemon.national_dex_id || 0) > 0 && Number(genderRates[Number(pokemon.national_dex_id || 0)] ?? 0) < 0)
                ? "Sem sexo"
                : "Não lido neste save"
          )
        )}`,
        cleanName(pokemon.unown_form || pokemon.metadata?.unown_form || "") ? `Forma: ${escapeHtml(cleanName(pokemon.unown_form || pokemon.metadata?.unown_form || ""))}` : "",
        pokemon.held_item_name ? `Item: ${escapeHtml(pokemon.held_item_name)}` : "Item: Sem item",
        pokemon.ability ? `Habilidade: ${escapeHtml(cleanName(pokemon.ability.name || pokemon.ability.ability_name || pokemon.ability) || "Desconhecida")}` : "",
        pokemon.nature ? `Nature: ${escapeHtml(cleanName(pokemon.nature.name || pokemon.nature) || "Desconhecida")}` : "",
        pokemon.ot_name ? `OT: ${escapeHtml(pokemon.ot_name)}` : "",
        Number.isFinite(Number(pokemon.trainer_id)) ? `Trainer ID: ${Number(pokemon.trainer_id)}` : "",
        pokemon.source_generation ? `Geração de origem: Gen ${Number(pokemon.source_generation)}` : "",
        pokemon.source_game ? `Jogo de origem: ${escapeHtml(pokemon.source_game)}` : "",
        moves ? `Golpes: ${escapeHtml(moves)}` : ""
      ].filter(Boolean);
      const spriteHtml = renderPokemonSummaryHtml(pokemon, "", { variant: "trade" });
      return `
        <div class="pokemon-detail-drawer-summary">${spriteHtml}</div>
        <div class="pokemon-inline-details">${facts.map((fact) => `<span>${fact}</span>`).join("")}</div>
      `;
    }

    function savePlayerName(save) {
      return cleanName(save?.player_name || "Player");
    }

    function updatePcToggleLabels() {
      const loadedSave = getLoadedSave();
      const playerName = loadedSave ? savePlayerName(loadedSave) : "Player";
      if (setupTogglePokemonPcButton) {
        setupTogglePokemonPcButton.textContent = pcVisibleByView.setup ? `Fechar computador de ${playerName}` : `Computador de ${playerName}`;
      }
      if (tradeTogglePokemonPcButton) {
        tradeTogglePokemonPcButton.textContent = pcVisibleByView.trade ? `Fechar computador de ${playerName}` : `Computador de ${playerName}`;
      }
    }

    function syncActiveBoxWithSelection(view) {
      const loadedSave = getLoadedSave();
      const selectedLocation = getSelectedLocation();
      if (!loadedSave?.boxes) return;
      if (!selectedLocation?.startsWith("box:")) {
        if (!Number.isFinite(activeBoxByView[view])) {
          activeBoxByView[view] = Number(loadedSave.boxes.current_box || 0);
        }
        return;
      }
      const parts = String(selectedLocation).split(":");
      activeBoxByView[view] = Number(parts[1] || loadedSave.boxes.current_box || 0);
    }

    function renderBoxPreviewHtml({ target, selectable, view }) {
      const loadedSave = getLoadedSave();
      const selectedLocation = getSelectedLocation();
      const pendingMoveSourceLocation = getPendingMoveSourceLocation();
      const boxState = loadedSave?.boxes || { current_box: 0, box_names: [], pokemon: [] };
      if (!boxState.pokemon.length && !pendingMoveSourceLocation) {
        target.className = "inventory-preview-body inventory-preview-empty";
        target.textContent = "Nenhum Pokémon armazenado nas boxes deste save.";
        return;
      }
      const grouped = new Map();
      const totalBoxes = Math.max(boxState.box_names?.length || 0, ...(boxState.pokemon || []).map((pokemon) => Number(pokemon.box_index || 0) + 1), 0);
      for (let boxIndex = 0; boxIndex < totalBoxes; boxIndex += 1) grouped.set(boxIndex, []);
      for (const pokemon of boxState.pokemon) {
        const boxIndex = Number(pokemon.box_index || 0);
        if (!grouped.has(boxIndex)) grouped.set(boxIndex, []);
        grouped.get(boxIndex).push(pokemon);
      }
      const totalBoxesOrdered = Array.from(grouped.keys()).sort((left, right) => left - right);
      const defaultBoxIndex = Number(boxState.current_box || 0);
      const maxBoxIndex = totalBoxesOrdered.length ? totalBoxesOrdered[totalBoxesOrdered.length - 1] : 0;
      let activeBoxIndex = Number.isFinite(activeBoxByView[view]) ? activeBoxByView[view] : defaultBoxIndex;
      if (!grouped.has(activeBoxIndex)) activeBoxIndex = defaultBoxIndex <= maxBoxIndex ? defaultBoxIndex : 0;
      activeBoxByView[view] = activeBoxIndex;

      const tabs = totalBoxesOrdered
        .map((boxIndex) => {
          const boxName = boxState.box_names?.[boxIndex] || `Box ${boxIndex + 1}`;
          const entries = grouped.get(boxIndex) || [];
          return `
            <button type="button" class="pc-box-tab${boxIndex === activeBoxIndex ? " is-active" : ""}" data-box-tab="${boxIndex}" data-box-view="${escapeAttribute(view)}">
              <span>${escapeHtml(boxName)}</span>
              <strong>${entries.length}</strong>
            </button>
          `;
        })
        .join("");

      const activeEntries = (grouped.get(activeBoxIndex) || []).sort((left, right) => Number(left.slot_index || 0) - Number(right.slot_index || 0));
      const activeBoxName = boxState.box_names?.[activeBoxIndex] || `Box ${activeBoxIndex + 1}`;
      const rows = activeEntries
        .map((pokemon) => {
          const selectedClass = pokemon.location === selectedLocation ? " is-selected" : "";
          const moveClass = pendingMoveSourceLocation === pokemon.location ? " is-source" : "";
          const metaText = pendingMoveSourceLocation === pokemon.location
            ? "Origem da movimentação"
            : pokemon.location === selectedLocation
              ? "Selecionado"
              : `Slot ${Number(pokemon.slot_index || 0) + 1}${pokemon.held_item_name ? ` · Item: ${escapeHtml(pokemon.held_item_name)}` : ""}`;
          if (!selectable) {
            return `<div class="inventory-item inventory-item-box"><span class="inventory-item-label">${renderPokemonSummaryHtml(pokemon)}</span><span class="inventory-item-meta">${metaText}</span></div>`;
          }
          return `
            <div class="inventory-item-shell${selectedClass}${moveClass}">
              <button type="button" draggable="true" class="inventory-item inventory-item-box inventory-item-selectable${selectedClass}${moveClass}" data-pokemon-location="${escapeAttribute(pokemon.location)}">
                <span class="inventory-item-label">${renderPokemonSummaryHtml(pokemon)}</span>
                <span class="inventory-item-meta">${metaText}</span>
              </button>
              <button type="button" class="inventory-item-info-button${detailDrawerPokemon?.location === pokemon.location ? " is-open" : ""}" data-pokemon-info="${escapeAttribute(pokemon.location)}" data-box-view="${escapeAttribute(view)}" aria-label="Mostrar detalhes do Pokémon">i</button>
            </div>
          `;
        })
        .join("") + (() => {
          if (!selectable || !pendingMoveSourceLocation) return "";
          const capacity = Number(getBoxCapacity?.() || activeEntries.length);
          if (loadedSave?.generation === 3) {
            const occupiedSlots = new Set(activeEntries.map((pokemon) => Number(pokemon.slot_index || 0)));
            const emptySlots = Array.from({ length: capacity }, (_, slotIndex) => slotIndex)
              .filter((slotIndex) => !occupiedSlots.has(slotIndex));
            if (!emptySlots.length) return "";
            const firstEmptySlot = emptySlots[0];
            const extraEmptyCount = emptySlots.length - 1;
            return `
              <button type="button" class="inventory-item inventory-item-box inventory-item-selectable inventory-item-empty" data-pokemon-location="box:${activeBoxIndex}:${firstEmptySlot}">
                <span class="inventory-item-label">Próximo slot vazio</span>
                <span class="inventory-item-meta">Slot ${firstEmptySlot + 1}${extraEmptyCount > 0 ? ` · +${extraEmptyCount} vazios neste box` : ""}</span>
              </button>
            `;
          }
          if (activeEntries.length >= capacity) return "";
          const nextSlotIndex = activeEntries.length;
          return `
            <button type="button" class="inventory-item inventory-item-box inventory-item-selectable inventory-item-empty" data-pokemon-location="box:${activeBoxIndex}:${nextSlotIndex}">
              <span class="inventory-item-label">Slot vazio</span>
              <span class="inventory-item-meta">Próximo slot disponível · clique para mover aqui</span>
            </button>
          `;
        })();

      const header = `
        <div class="pc-box-header">
          <button type="button" class="pc-box-nav ghost" data-box-prev="${activeBoxIndex}" data-box-view="${escapeAttribute(view)}" ${activeBoxIndex <= 0 ? "disabled" : ""}>←</button>
          <div class="pc-box-tabs" role="tablist" aria-label="Boxes do PC Pokémon">${tabs}</div>
          <button type="button" class="pc-box-nav ghost" data-box-next="${activeBoxIndex}" data-box-view="${escapeAttribute(view)}" ${activeBoxIndex >= maxBoxIndex ? "disabled" : ""}>→</button>
        </div>
      `;
      target.className = "inventory-preview-body";
      target.innerHTML = `
        ${header}
        <div class="inventory-pocket inventory-pocket-box">
          <strong>${escapeHtml(activeBoxName)}${activeBoxIndex === boxState.current_box ? " · atual" : ""}</strong>
          <div class="inventory-list inventory-list-pokemon-grid">${rows}</div>
        </div>
      `;
    }

    function updatePokemonPcPreview() {
      const loadedSave = getLoadedSave();
      updatePcToggleLabels();
      if (!loadedSave) {
        setupPokemonPcPreviewEl.className = "inventory-preview-body inventory-preview-empty";
        setupPokemonPcPreviewEl.textContent = "Carregue um save para liberar o computador deste jogador.";
        tradeBoxPreviewEl.className = "inventory-preview-body inventory-preview-empty";
        tradeBoxPreviewEl.textContent = "Carregue um save para liberar o computador deste jogador.";
        return;
      }
      if (!pcVisibleByView.setup) {
        setupPokemonPcPreviewEl.className = "inventory-preview-body inventory-preview-empty";
        setupPokemonPcPreviewEl.textContent = `Clique em "${setupTogglePokemonPcButton?.textContent || "Computador do Player"}" para abrir as boxes.`;
      } else {
        syncActiveBoxWithSelection("setup");
        renderBoxPreviewHtml({ target: setupPokemonPcPreviewEl, selectable: true, view: "setup" });
      }
      if (!pcVisibleByView.trade) {
        tradeBoxPreviewEl.className = "inventory-preview-body inventory-preview-empty";
        tradeBoxPreviewEl.textContent = `Clique em "${tradeTogglePokemonPcButton?.textContent || "Computador do Player"}" para abrir as boxes.`;
      } else {
        syncActiveBoxWithSelection("trade");
        renderBoxPreviewHtml({ target: tradeBoxPreviewEl, selectable: true, view: "trade" });
      }
    }

    function handlePokemonPcAction(event, view) {
      const targetEl = event.target.closest("[data-box-tab],[data-box-prev],[data-box-next],[data-pokemon-info]");
      if (!targetEl) return false;
      if (targetEl.hasAttribute("data-box-tab")) {
        activeBoxByView[view] = Number(targetEl.getAttribute("data-box-tab") || 0);
        updatePokemonPcPreview();
        return true;
      }
      if (targetEl.hasAttribute("data-box-prev")) {
        activeBoxByView[view] = Math.max(0, Number(activeBoxByView[view] || 0) - 1);
        updatePokemonPcPreview();
        return true;
      }
      if (targetEl.hasAttribute("data-box-next")) {
        activeBoxByView[view] = Number(activeBoxByView[view] || 0) + 1;
        updatePokemonPcPreview();
        return true;
      }
      if (targetEl.hasAttribute("data-pokemon-info")) {
        const location = targetEl.getAttribute("data-pokemon-info");
        const loadedSave = getLoadedSave();
        detailDrawerPokemon = location ? (loadedSave?.boxes?.pokemon || []).find((pokemon) => pokemon.location === location) || null : null;
        if (!detailDrawerPokemon) return true;
        if (pokemonDetailDrawerTitleEl) {
          pokemonDetailDrawerTitleEl.textContent = detailDrawerPokemon.display_summary || cleanName(detailDrawerPokemon.species_name || "Pokémon");
        }
        if (pokemonDetailDrawerBodyEl) {
          pokemonDetailDrawerBodyEl.innerHTML = pokemonInfoHtml(detailDrawerPokemon);
        }
        if (pokemonDetailDrawerBackdropEl) pokemonDetailDrawerBackdropEl.hidden = false;
        if (pokemonDetailDrawerEl) {
          pokemonDetailDrawerEl.classList.add("is-open");
          pokemonDetailDrawerEl.setAttribute("aria-hidden", "false");
        }
        updatePokemonPcPreview();
        return true;
      }
      return false;
    }

    function togglePokemonPcVisibility(view) {
      pcVisibleByView[view] = !pcVisibleByView[view];
      updatePokemonPcPreview();
    }

    function closePokemonDetailDrawer() {
      detailDrawerPokemon = null;
      if (pokemonDetailDrawerBackdropEl) pokemonDetailDrawerBackdropEl.hidden = true;
      if (pokemonDetailDrawerEl) {
        pokemonDetailDrawerEl.classList.remove("is-open");
        pokemonDetailDrawerEl.setAttribute("aria-hidden", "true");
      }
      updatePokemonPcPreview();
    }

    return {
      updateInventoryPreview,
      updatePokemonPcPreview,
      handlePokemonPcAction,
      togglePokemonPcVisibility,
      closePokemonDetailDrawer
    };
  }
};
