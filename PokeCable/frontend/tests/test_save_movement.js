const test = require("node:test");
const assert = require("node:assert/strict");

const { moveWithinContainer, moveAcrossContainers } = require("../save-movement.js");
const { createSaveManagementController } = require("../save-management.js");

function createSaveManagementTestController({ elements = {}, selectedInventoryItem = null, pendingMoveSourceLocation = null } = {}) {
  const pokemon = {
    location: "party:0",
    species_name: "Pikachu",
    display_summary: "Pikachu Lv.5",
    level: 5,
    is_egg: false,
    held_item_id: null
  };
  const save = {
    generation: 2,
    layout: { partyCapacity: 6 },
    party: [pokemon],
    boxes: { current_box: 0, box_names: [], pokemon: [] }
  };
  let selectedLocation = "party:0";
  let selectedItem = selectedInventoryItem;
  let pendingSource = pendingMoveSourceLocation;

  return createSaveManagementController({
    getLoadedSave: () => save,
    getSelectedLocation: () => selectedLocation,
    setSelectedLocation: (value) => { selectedLocation = value; },
    getSelectedInventoryItem: () => selectedItem,
    setSelectedInventoryItem: (value) => { selectedItem = value; },
    getPendingMoveSourceLocation: () => pendingSource,
    setPendingMoveSourceLocation: (value) => { pendingSource = value; },
    getTradeState: () => ({ roundActive: false }),
    parseLocation: (location) => ({ kind: "party", index: Number(String(location).split(":")[1] || 0) }),
    pokemonByLocation: (_save, location) => location === pokemon.location ? pokemon : null,
    locationLabel: () => "Party · slot 1",
    cleanName: (value) => String(value || "").trim(),
    normalizePokemonDisplay: (entry) => entry.display_summary || entry.species_name,
    renderPokemonSummaryHtml: (entry) => entry.display_summary || entry.species_name,
    renderOfferCard: () => {},
    clearTradePreviews: () => {},
    relocatePokemonWithinSave: () => {},
    hasBagSpaceInSave: () => false,
    hasPcSpaceInSave: () => false,
    storeItemInBagForSave: () => null,
    storeItemInPcForSave: () => null,
    clearHeldItemInSave: () => {},
    setHeldItemInSave: () => {},
    removeItemFromPocket: () => {},
    refreshLoadedSaveCollections: () => {},
    nonHoldableCategories: new Set(),
    syncTransientUi: () => {},
    syncAfterSaveMutation: () => {},
    activateTab: () => {},
    elements
  });
}

test("counted container reorders entry into next empty slot", () => {
  const state = {
    kind: "counted",
    capacity: 6,
    entries: ["A", "B", "C"]
  };
  const result = moveWithinContainer(state, 0, 3);
  assert.deepEqual(result.entries, ["B", "C", "A"]);
});

test("fixed container moves entry into empty slot", () => {
  const state = {
    kind: "fixed",
    capacity: 5,
    entries: ["A", null, "B", null, null]
  };
  const result = moveWithinContainer(state, 2, 4);
  assert.deepEqual(result.entries, ["A", null, null, null, "B"]);
});

test("cross-container move from counted party to fixed box preserves source compaction", () => {
  const source = {
    kind: "counted",
    capacity: 6,
    entries: ["A", "B", "C"]
  };
  const target = {
    kind: "fixed",
    capacity: 5,
    entries: [null, null, "X", null, null]
  };
  const result = moveAcrossContainers(source, target, 1, 3);
  assert.deepEqual(result.source.entries, ["A", "C"]);
  assert.deepEqual(result.target.entries, [null, null, "X", "B", null]);
});

test("cross-container move from fixed box to counted party inserts at next free slot", () => {
  const source = {
    kind: "fixed",
    capacity: 5,
    entries: [null, "A", null, null, null]
  };
  const target = {
    kind: "counted",
    capacity: 6,
    entries: ["P1", "P2"]
  };
  const result = moveAcrossContainers(source, target, 1, 2);
  assert.deepEqual(result.source.entries, [null, null, null, null, null]);
  assert.deepEqual(result.target.entries, ["P1", "P2", "A"]);
});

test("fixed container rejects occupied destination", () => {
  const state = {
    kind: "fixed",
    capacity: 4,
    entries: ["A", null, "B", null]
  };
  assert.throws(() => moveWithinContainer(state, 0, 2), /Destino ocupado/);
});

test("counted target rejects invalid insertion past capacity", () => {
  const source = {
    kind: "counted",
    capacity: 6,
    entries: ["A"]
  };
  const target = {
    kind: "counted",
    capacity: 2,
    entries: ["P1", "P2"]
  };
  assert.throws(() => moveAcrossContainers(source, target, 0, 2), /Destino inválido/);
});

test("save management tolerates missing optional held-item buttons", () => {
  const tradeSelectedSummaryEl = { textContent: "" };
  const controller = createSaveManagementTestController({ elements: { tradeSelectedSummaryEl } });

  assert.doesNotThrow(() => controller.updateSelectionUi());
  assert.equal(tradeSelectedSummaryEl.textContent, "Pikachu Lv.5");
});

test("save management updates move buttons when present and held-item buttons are absent", () => {
  const startMovePokemonButton = { disabled: null };
  const cancelMovePokemonButton = { hidden: null };
  const controller = createSaveManagementTestController({
    elements: {
      tradeSelectedSummaryEl: { textContent: "" },
      startMovePokemonButton,
      cancelMovePokemonButton
    }
  });

  controller.updateManagementButtons();

  assert.equal(startMovePokemonButton.disabled, false);
  assert.equal(cancelMovePokemonButton.hidden, true);
});

test("save management preview methods tolerate omitted optional preview targets", () => {
  const controller = createSaveManagementTestController({
    elements: {
      tradeSelectedSummaryEl: { textContent: "" }
    }
  });

  assert.doesNotThrow(() => controller.updateSetupPartyPreview());
  assert.doesNotThrow(() => controller.updateTradePartyPreview());
});
