window.POKECABLE_POKEMON_UI = {
  createPokemonUiRenderer({
    canonicalFromPayload,
    itemName,
    moveName,
    abilityName,
    cleanName,
    escapeHtml,
    normalizePokemonDisplay,
    payloadNationalDexId,
    renderPokemonSummaryHtml,
    getLoadedSaveGeneration,
    getLoadedSaveGame
  }) {
    function pokemonFacts(pokemonLike) {
      if (!pokemonLike) return null;
      const canonical = canonicalFromPayload(pokemonLike);
      const sourceGeneration = Number(canonical?.source_generation || pokemonLike.generation || pokemonLike.source_generation || getLoadedSaveGeneration() || 0);
      const speciesName = canonical?.species?.name || pokemonLike.species_name || "Pokemon";
      const heldItemName = cleanName(
        canonical?.held_item?.name
        || pokemonLike.held_item_name
        || itemName(canonical?.held_item?.item_id || pokemonLike.held_item_id, sourceGeneration)
      ) || null;
      const moves = canonical?.moves
        ? canonical.moves.map((move) => move.name || moveName(move.move_id || move) || `Move #${move.move_id || move}`).filter(Boolean)
        : (pokemonLike.moves || []).map((move) => moveName(move) || `Move #${move}`).filter(Boolean);
      const gender = cleanName(
        canonical?.metadata?.gender
        || pokemonLike.gender
        || pokemonLike.metadata?.gender
      ) || null;
      const unownForm = cleanName(
        canonical?.metadata?.unown_form
        || pokemonLike.unown_form
        || pokemonLike.metadata?.unown_form
      ) || null;
      return {
        species_name: speciesName,
        nickname: cleanName(canonical?.nickname || pokemonLike.nickname || speciesName) || speciesName,
        held_item_name: heldItemName,
        moves,
        source_generation: sourceGeneration,
        source_game: cleanName(canonical?.source_game || pokemonLike.game || pokemonLike.source_game || getLoadedSaveGame?.() || ""),
        ot_name: cleanName(canonical?.ot_name || pokemonLike.ot_name || ""),
        trainer_id: Number(canonical?.trainer_id || pokemonLike.trainer_id || 0),
        ability: abilityName(canonical?.ability ?? pokemonLike.ability ?? pokemonLike.ability_id) || (Number.isFinite(pokemonLike.ability_index) ? `Index ${pokemonLike.ability_index}` : null),
        nature: cleanName(canonical?.nature?.name || canonical?.nature || pokemonLike.nature || ""),
        gender,
        unown_form: unownForm
      };
    }

    function detailBlockHtml(title, bodyHtml) {
      return `
        <div class="pokemon-detail-block">
          <strong>${escapeHtml(title)}</strong>
          ${bodyHtml}
        </div>
      `;
    }

    function renderPokemonDetailsHtml(pokemonLike, emptyMessage = "Item, golpes e características aparecem aqui.") {
      const facts = pokemonFacts(pokemonLike);
      if (!facts) {
        return [
          detailBlockHtml("Item", "<span>-</span>"),
          detailBlockHtml("Golpes", "<span>-</span>"),
          detailBlockHtml("Características", `<span>${escapeHtml(emptyMessage)}</span>`)
        ].join("");
      }
      const itemText = facts.held_item_name ? escapeHtml(facts.held_item_name) : "Sem item";
      const moveItems = facts.moves.length
        ? `<ul class="pokemon-detail-list">${facts.moves.map((move) => `<li>${escapeHtml(move)}</li>`).join("")}</ul>`
        : "<span>Sem golpes exportados.</span>";
      const characteristics = [
        facts.gender ? `Sexo: ${facts.gender}` : null,
        facts.unown_form ? `Forma: ${facts.unown_form}` : null,
        facts.ability ? `Ability: ${facts.ability}` : null,
        facts.nature ? `Nature: ${facts.nature}` : null,
        facts.ot_name ? `OT: ${facts.ot_name}` : null,
        facts.trainer_id ? `Trainer ID: ${facts.trainer_id}` : null,
        facts.source_generation ? `Geração de origem: Gen ${facts.source_generation}` : null,
        facts.source_game ? `Jogo de origem: ${facts.source_game}` : null
      ].filter(Boolean);
      const characteristicsHtml = characteristics.length
        ? `<ul class="pokemon-detail-list">${characteristics.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
        : "<span>Sem características extras.</span>";
      return [
        detailBlockHtml("Item", `<span>${itemText}</span>`),
        detailBlockHtml("Golpes", moveItems),
        detailBlockHtml("Características", characteristicsHtml)
      ].join("");
    }

    function renderOfferCard(summaryEl, detailsEl, pokemonLike, textOverride = "", options = {}) {
      if (!pokemonLike) {
        summaryEl.innerHTML = "-";
        detailsEl.className = "pokemon-card-details pokemon-card-details-empty";
        detailsEl.innerHTML = renderPokemonDetailsHtml(null, options.emptyMessage || "Aguardando oferta...");
        return;
      }
      }
      summaryEl.innerHTML = renderPokemonSummaryHtml(pokemonLike, textOverride, { variant: "trade" });
      detailsEl.className = "pokemon-card-details";
      detailsEl.innerHTML = renderPokemonDetailsHtml(pokemonLike);
    }

    return {
      pokemonFacts,
      renderPokemonDetailsHtml,
      renderOfferCard,
      payloadNationalDexId,
      normalizePokemonDisplay
    };
  }
};
