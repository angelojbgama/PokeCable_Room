const test = require("node:test");
const assert = require("node:assert/strict");

const { moveWithinContainer, moveAcrossContainers } = require("../save-movement.js");

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
