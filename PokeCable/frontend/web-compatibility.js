window.POKECABLE_WEB_COMPATIBILITY = {
  createCompatibilityBuilder({
    canonicalFromPayload,
    payloadNationalDexId,
    nationalToNative,
    speciesExistsInGeneration,
    itemName,
    itemCategory,
    moveName,
    getLoadedSaveGeneration,
    getLoadedSave,
    resolveItemTransferDecisionForSave
  }) {
    return function buildWebCompatibilityReport(payload, message) {
      const targetGeneration = getLoadedSaveGeneration() || message.target_generation;
      const report = {
        compatible: true,
        mode: message.derived_mode || "same_generation",
        source_generation: message.source_generation,
        target_generation: targetGeneration,
        blocking_reasons: [],
        warnings: [],
        data_loss: [],
        suggested_actions: [],
        transformations: [],
        removed_moves: [],
        removed_items: [],
        removed_fields: [],
        normalized_species: {},
        item_transfer: null,
        requires_user_confirmation: false
      };
      if (!getLoadedSaveGeneration()) return report;
      if (payload.generation === targetGeneration) {
        const nationalId = payloadNationalDexId(payload);
        report.normalized_species = {
          national_dex_id: nationalId,
          source_species_id: payload.species_id,
          source_species_id_space: targetGeneration === 1 ? "gen1_internal" : targetGeneration === 2 ? "national_dex" : "gen3_internal",
          target_species_id: payload.species_id,
          target_species_id_space: targetGeneration === 1 ? "gen1_internal" : targetGeneration === 2 ? "national_dex" : "gen3_internal"
        };
        return report;
      }
      const canonical = canonicalFromPayload(payload);
      if (!canonical) {
        report.compatible = false;
        report.blocking_reasons.push("Payload cross-generation sem canonical.");
        return report;
      }
      const nationalId = Number(canonical.species.national_dex_id);
      const targetSpeciesId = nationalToNative(targetGeneration, nationalId);
      report.normalized_species = {
        national_dex_id: nationalId,
        source_species_id: canonical.species.source_species_id,
        source_species_id_space: canonical.species.source_species_id_space,
        target_species_id: targetSpeciesId,
        target_species_id_space: targetGeneration === 1 ? "gen1_internal" : targetGeneration === 2 ? "national_dex" : "gen3_internal"
      };
      if (!speciesExistsInGeneration(nationalId, targetGeneration)) {
        report.compatible = false;
        report.blocking_reasons.push(`${canonical.species.name} National Dex #${nationalId} nao existe na Gen ${targetGeneration}.`);
        return report;
      }
      const maxMove = targetGeneration === 1 ? 165 : targetGeneration === 2 ? 251 : 354;
      const learnableIds = window.POKECABLE_LEARNSETS ? (window.POKECABLE_LEARNSETS[`${targetGeneration}-${nationalId}`] || []) : [];
      const validReplacements = learnableIds.map(id => ({ move_id: id, name: moveName(id) || `Move #${id}` }));

      for (const move of canonical.moves || []) {
        const moveId = Number(move.move_id || move);
        if (moveId > maxMove) {
          report.removed_moves.push({ 
            move_id: moveId, 
            name: move.name || moveName(moveId) || `Move #${moveId}`,
            valid_replacements: validReplacements
          });
          if (!report.data_loss.includes("moves")) report.data_loss.push("moves");
          report.requires_user_confirmation = true;
        }
      }      if (canonical.held_item && canonical.held_item.item_id) {
        const localSave = getLoadedSave();
        if (localSave) {
          report.item_transfer = resolveItemTransferDecisionForSave(payload, localSave);
        }
      }
      if (canonical.held_item && canonical.held_item.item_id && targetGeneration === 1) {
        report.removed_items.push({
          item_id: canonical.held_item.item_id,
          name: canonical.held_item.name || itemName(canonical.held_item.item_id, canonical.source_generation) || `Item #${canonical.held_item.item_id}`
        });
        if (!report.data_loss.includes("held_item")) report.data_loss.push("held_item");
      }
      if (report.item_transfer && report.item_transfer.disposition === "remove" && report.item_transfer.reason !== "item_absent_in_target_generation") {
        report.warnings.push("O item recebido não ficará segurado no save local.");
      }
      if (report.item_transfer && report.item_transfer.reason === "item_absent_in_target_generation") {
        report.warnings.push("O item recebido não existe na geração de destino e será removido.");
      }
      if (targetGeneration < 3) {
        if (canonical.ability) {
          report.removed_fields.push("ability");
          if (!report.data_loss.includes("ability")) report.data_loss.push("ability");
        }
        if (canonical.nature) {
          report.removed_fields.push("nature");
          if (!report.data_loss.includes("nature")) report.data_loss.push("nature");
        }
      }
      return report;
    };
  }
};
