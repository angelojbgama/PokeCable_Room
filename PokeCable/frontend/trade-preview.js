window.POKECABLE_TRADE_PREVIEW = {
  createTradePreviewRenderer({
    elements,
    canonicalFromPayload,
    payloadNationalDexId,
    itemName,
    sameName,
    cleanName,
    escapeHtml,
    normalizePokemonDisplay,
    renderPokemonSummaryHtml,
    speciesNames,
    simpleTradeEvolutionByNational,
    itemTradeEvolutionRules,
    getLoadedSaveGeneration
  }) {
    const {
      tradeCompatibilityPreviewEl,
      tradeEvolutionPreviewEl,
      localOfferDetailsEl,
      peerOfferDetailsEl
    } = elements;

    function clearTradePreviews() {
      tradeCompatibilityPreviewEl.textContent = "Aguardando o Pokémon do outro jogador.";
      tradeCompatibilityPreviewEl.className = "trade-preview-body trade-preview-empty";
      tradeEvolutionPreviewEl.textContent = "Sem evolução prevista.";
      tradeEvolutionPreviewEl.className = "trade-preview-body trade-preview-empty";
      localOfferDetailsEl.className = "pokemon-card-details pokemon-card-details-empty";
      localOfferDetailsEl.textContent = "Item, golpes e características aparecem aqui.";
      peerOfferDetailsEl.className = "pokemon-card-details pokemon-card-details-empty";
      peerOfferDetailsEl.textContent = "Aguardando o Pokémon do outro jogador.";
    }

    function listSectionHtml(title, items) {
      if (!items.length) return "";
      const lines = items.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
      return `
        <div class="trade-report-section">
          <strong>${escapeHtml(title)}</strong>
          <ul class="trade-report-list">${lines}</ul>
        </div>
      `;
    }

    function itemTransferSectionHtml(itemTransfer) {
      if (!itemTransfer) return "";
      let destination = "Item será removido.";
      if (itemTransfer.disposition === "keep_held") {
        destination = `Item continua segurado: ${itemTransfer.resolved_item_name || `Item #${itemTransfer.resolved_item_id}`}.`;
      } else if (itemTransfer.disposition === "move_to_bag") {
        destination = `Item vai para a mochila (${itemTransfer.stored_in?.pocket_name || "pocket principal"}): ${itemTransfer.resolved_item_name || `Item #${itemTransfer.resolved_item_id}`}.`;
      } else if (itemTransfer.disposition === "move_to_pc") {
        destination = `Item vai para o PC: ${itemTransfer.resolved_item_name || `Item #${itemTransfer.resolved_item_id}`}.`;
      }
      const detail = itemTransfer.reason ? `Motivo: ${itemTransfer.reason}.` : "";
      return `
        <div class="trade-report-section">
          <strong>Destino do item recebido</strong>
          <ul class="trade-report-list">
            <li>${escapeHtml(destination)}</li>
            ${detail ? `<li>${escapeHtml(detail)}</li>` : ""}
          </ul>
        </div>
      `;
    }

    function predictedHeldItemName(canonical, report, targetGeneration) {
      if (!canonical?.held_item?.item_id && !canonical?.held_item?.name) return null;
      if (targetGeneration === 1) return null;
      const removedItems = report?.removed_items || [];
      const currentName = cleanName(canonical.held_item?.name || itemName(canonical.held_item?.item_id, canonical.source_generation));
      const removed = removedItems.some((item) => sameName(item.name || "", currentName) || Number(item.item_id || 0) === Number(canonical.held_item?.item_id || 0));
      if (removed) return null;
      return currentName || null;
    }

    function previewTradeEvolutionForPayload(payload, report, targetGeneration) {
      if (!payload || !report?.compatible) return null;
      const canonical = canonicalFromPayload(payload);
      if (!canonical) return null;
      const beforeNationalId = Number(report.normalized_species?.national_dex_id || canonical.species?.national_dex_id || payloadNationalDexId(payload) || 0);
      if (!beforeNationalId) return null;
      const heldItemName = predictedHeldItemName(canonical, report, targetGeneration);
      const simpleTarget = simpleTradeEvolutionByNational[beforeNationalId];
      if (simpleTarget) {
        return {
          source_national_dex_id: beforeNationalId,
          source_name: speciesNames[beforeNationalId] || canonical.species?.name || payload.species_name || "Pokemon",
          target_national_dex_id: simpleTarget,
          target_name: speciesNames[simpleTarget] || `Species #${simpleTarget}`,
          level: Number(canonical.level || payload.level || 1),
          nickname: canonical.nickname || payload.nickname || canonical.species?.name || payload.species_name,
          held_item_name: heldItemName,
          consumed_item_name: null,
          reason: "simple_trade_evolution"
        };
      }
      const itemRule = itemTradeEvolutionRules.find((rule) => (
        targetGeneration >= rule.minGeneration
        && rule.national === beforeNationalId
        && heldItemName
        && sameName(heldItemName, rule.item)
      ));
      if (!itemRule) return null;
      return {
        source_national_dex_id: beforeNationalId,
        source_name: speciesNames[beforeNationalId] || canonical.species?.name || payload.species_name || "Pokemon",
        target_national_dex_id: itemRule.target,
        target_name: speciesNames[itemRule.target] || `Species #${itemRule.target}`,
        level: Number(canonical.level || payload.level || 1),
        nickname: canonical.nickname || payload.nickname || canonical.species?.name || payload.species_name,
        held_item_name: heldItemName,
        consumed_item_name: itemRule.item,
        reason: "item_trade_evolution"
      };
    }

    function renderTradeCompatibilityPreview(payload, report, explicitTargetGeneration) {
      if (!payload) {
        clearTradePreviews();
        return;
      }
      const targetGeneration = explicitTargetGeneration || report?.target_generation || getLoadedSaveGeneration() || payload.generation;
      const summary = payload.display_summary || (payload.summary && payload.summary.display_summary) || normalizePokemonDisplay(payload);
      const blockedReasons = (report?.blocking_reasons || []).slice();
      const warnings = (report?.warnings || []).slice();
      const dataLoss = (report?.data_loss || []).map((entry) => {
        if (entry === "held_item") return "Held item será removido.";
        if (entry === "moves") return "Golpes incompatíveis serão removidos.";
        if (entry === "ability") return "Ability será removida.";
        if (entry === "nature") return "Nature será removida.";
        return String(entry);
      });
      const removedMoves = (report?.removed_moves || []).map((move) => `Golpe removido: ${move.name || `Move #${move.move_id}`}`);
      const removedItems = (report?.removed_items || []).map((item) => `Item removido: ${item.name || `Item #${item.item_id}`}`);
      const removedFields = (report?.removed_fields || []).map((field) => `${field === "ability" ? "Ability" : field === "nature" ? "Nature" : field} será removido.`);
      const transformations = (report?.transformations || []).slice();
      const normalized = report?.normalized_species || {};
      const statusClass = report?.compatible ? "compatible" : "blocked";
      const statusLabel = report?.compatible ? "Compatível" : "Bloqueado";
      const metaLines = payload.generation === targetGeneration
        ? [
            `Origem Gen ${report?.source_generation || payload.generation} -> Destino Gen ${targetGeneration}.`,
            "Troca same-generation: o save local receberá o payload raw."
          ]
        : [
            `Origem Gen ${report?.source_generation || payload.generation} -> Destino Gen ${targetGeneration}.`,
            normalized.target_species_id
              ? `Species destino: ${normalized.target_species_id} (${normalized.target_species_id_space || "nativo"}).`
              : "Species destino ainda não normalizada."
          ];

      tradeCompatibilityPreviewEl.className = "trade-preview-body";
      tradeCompatibilityPreviewEl.innerHTML = `
        <div class="trade-report-status ${statusClass}">${statusLabel}</div>
        <div class="trade-report-meta">
          ${renderPokemonSummaryHtml(payload, summary, { variant: "trade" })}
          <p>${escapeHtml(metaLines.join(" "))}</p>
          <p>${escapeHtml(`Modo derivado: ${report?.mode || "same_generation"}`)}</p>
        </div>
        <div class="trade-report-sections">
          ${listSectionHtml("Bloqueios", blockedReasons)}
          ${listSectionHtml("Perdas detectadas", dataLoss)}
          ${listSectionHtml("Golpes removidos", removedMoves)}
          ${listSectionHtml("Itens removidos", removedItems)}
          ${listSectionHtml("Campos removidos", removedFields)}
          ${itemTransferSectionHtml(report?.item_transfer)}
          ${listSectionHtml("Transformações", transformations)}
          ${listSectionHtml("Avisos", warnings)}
        </div>
      `;
    }

    function renderTradeEvolutionPreview(payload, report, explicitTargetGeneration) {
      if (!payload) {
        clearTradePreviews();
        return;
      }
      const targetGeneration = explicitTargetGeneration || report?.target_generation || getLoadedSaveGeneration() || payload.generation;
      const summary = payload.display_summary || (payload.summary && payload.summary.display_summary) || normalizePokemonDisplay(payload);
      const preview = previewTradeEvolutionForPayload(payload, report, targetGeneration);
      if (!preview) {
        const message = report?.compatible
          ? "Sem evolução prevista para esta troca."
          : "Sem evolução prevista porque a troca será bloqueada.";
        tradeEvolutionPreviewEl.className = "trade-preview-body";
        tradeEvolutionPreviewEl.innerHTML = `
          <div class="trade-report-meta">
            ${renderPokemonSummaryHtml(payload, summary, { variant: "trade" })}
            <p>${escapeHtml(message)}</p>
          </div>
        `;
        return;
      }
      const beforePokemon = {
        national_dex_id: preview.source_national_dex_id,
        species_name: preview.source_name,
        level: preview.level,
        nickname: preview.nickname,
        held_item_name: preview.held_item_name
      };
      const afterPokemon = {
        national_dex_id: preview.target_national_dex_id,
        species_name: preview.target_name,
        level: preview.level,
        nickname: preview.nickname,
        held_item_name: preview.reason === "item_trade_evolution" ? null : preview.held_item_name
      };
      const caption = preview.reason === "item_trade_evolution"
        ? `${preview.source_name} deve evoluir ao chegar no save local. ${preview.consumed_item_name} será consumido.`
        : `${preview.source_name} deve evoluir ao chegar no save local.`;
      tradeEvolutionPreviewEl.className = "trade-preview-body";
      tradeEvolutionPreviewEl.innerHTML = `
        <div class="trade-evolution-caption">${escapeHtml(caption)}</div>
        <div class="trade-evolution-flow">
          <div class="trade-report-meta">
            ${renderPokemonSummaryHtml(beforePokemon, "", { variant: "trade" })}
          </div>
          <div class="trade-evolution-arrow">→</div>
          <div class="trade-report-meta">
            ${renderPokemonSummaryHtml(afterPokemon, "", { variant: "trade" })}
          </div>
        </div>
      `;
    }

    return {
      clearTradePreviews,
      renderTradeCompatibilityPreview,
      renderTradeEvolutionPreview
    };
  }
};
