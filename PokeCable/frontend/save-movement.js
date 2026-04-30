(function initSaveMovement(root) {
  function cloneEntries(entries) {
    return entries.slice();
  }

  function moveWithinContainer(state, sourceIndex, targetIndex) {
    const entries = cloneEntries(state.entries);
    if (state.kind === "counted") {
      if (sourceIndex < 0 || sourceIndex >= entries.length) throw new Error("Origem inválida para container contíguo.");
      if (targetIndex < 0 || targetIndex > entries.length) throw new Error("Destino inválido para container contíguo.");
      if (targetIndex === sourceIndex) return { ...state, entries };
      const [entry] = entries.splice(sourceIndex, 1);
      const insertAt = Math.min(targetIndex, entries.length);
      entries.splice(insertAt, 0, entry);
      return { ...state, entries };
    }
    if (sourceIndex < 0 || sourceIndex >= state.capacity) throw new Error("Origem inválida para container fixo.");
    if (targetIndex < 0 || targetIndex >= state.capacity) throw new Error("Destino inválido para container fixo.");
    if (!entries[sourceIndex]) throw new Error("Origem vazia para container fixo.");
    if (entries[targetIndex]) throw new Error("Destino ocupado para container fixo.");
    entries[targetIndex] = entries[sourceIndex];
    entries[sourceIndex] = null;
    return { ...state, entries };
  }

  function moveAcrossContainers(sourceState, targetState, sourceIndex, targetIndex) {
    const nextSourceEntries = cloneEntries(sourceState.entries);
    const nextTargetEntries = cloneEntries(targetState.entries);
    let movedEntry;

    if (sourceState.kind === "counted") {
      if (sourceIndex < 0 || sourceIndex >= nextSourceEntries.length) throw new Error("Origem inválida.");
      movedEntry = nextSourceEntries.splice(sourceIndex, 1)[0];
    } else {
      if (sourceIndex < 0 || sourceIndex >= sourceState.capacity) throw new Error("Origem inválida.");
      movedEntry = nextSourceEntries[sourceIndex];
      if (!movedEntry) throw new Error("Origem vazia.");
      nextSourceEntries[sourceIndex] = null;
    }

    if (targetState.kind === "counted") {
      if (targetIndex < 0 || targetIndex > nextTargetEntries.length || targetIndex >= targetState.capacity) {
        throw new Error("Destino inválido.");
      }
      nextTargetEntries.splice(targetIndex, 0, movedEntry);
    } else {
      if (targetIndex < 0 || targetIndex >= targetState.capacity) throw new Error("Destino inválido.");
      if (nextTargetEntries[targetIndex]) throw new Error("Destino ocupado.");
      nextTargetEntries[targetIndex] = movedEntry;
    }

    return {
      source: { ...sourceState, entries: nextSourceEntries },
      target: { ...targetState, entries: nextTargetEntries }
    };
  }

  const api = {
    moveWithinContainer,
    moveAcrossContainers
  };

  root.POKECABLE_SAVE_MOVEMENT = api;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
})(typeof window !== "undefined" ? window : globalThis);
