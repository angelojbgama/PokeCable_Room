window.POKECABLE_GROWTH_RATES = {
  speciesGrowthRate: [
    0, 4, 4, 4, 4, 4, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2, 4, 4, 4, 2, 2, 2, 2, 2,
    2, 2, 2, 2, 2, 4, 4, 4, 4, 4, 4, 3, 3, 2, 2, 3, 3, 2, 2, 4, 4, 4, 2, 2,
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
    1, 1, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1, 4, 4, 4, 2,
    2, 2, 2, 2, 2, 2, 1, 1, 2, 2, 2, 2, 2, 2, 2, 1, 1, 3, 2, 2, 2, 2, 2, 2,
    1, 1, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 2, 2, 2, 2, 3, 3, 3,
    3, 2, 1, 1, 2, 3, 3, 3, 3, 2, 2, 4, 4, 4, 4, 3, 3, 2, 4, 4, 4, 4, 3, 4,
    4, 2, 2, 2, 2, 2, 4, 2, 3, 2, 2, 2, 2, 2, 2, 4, 2, 3, 3, 2, 2, 4, 1, 4,
    2, 2, 2, 2, 1, 1, 3, 2, 2, 3, 1, 1, 1, 1, 2, 2, 2, 2, 1, 3, 2, 2, 2, 2,
    2, 1, 3, 1, 1, 1, 1, 1, 1, 1, 1, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 2, 2, 2,
    2, 2, 2, 2, 2, 2, 4, 4, 4, 4, 4, 4, 4, 4, 2, 2, 1, 1, 1, 2, 2, 6, 6, 1,
    1, 1, 5, 5, 5, 4, 4, 4, 6, 6, 3, 2, 3, 3, 4, 3, 1, 1, 1, 2, 2, 1, 1, 2,
    2, 5, 6, 4, 6, 6, 1, 1, 6, 6, 2, 2, 2, 3, 3, 3, 4, 4, 4, 4, 4, 5, 5, 5,
    6, 3, 3, 2, 2, 6, 6, 2, 2, 5, 5, 5, 5, 5, 5, 2, 4, 3, 3, 3, 3, 1, 3, 4,
    2, 2, 2, 4, 4, 4, 5, 5, 5, 1, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1,
  ],
  experienceForLevel(growthRateId, level) {
    const clampedLevel = Math.max(1, Math.min(100, Number(level || 1)));
    const cube = clampedLevel * clampedLevel * clampedLevel;
    if (growthRateId === 1) return Math.floor((5 * cube) / 4);
    if (growthRateId === 2) return cube;
    if (growthRateId === 3) return Math.floor((4 * cube) / 5);
    if (growthRateId === 4) return Math.floor((6 * cube) / 5) - 15 * clampedLevel * clampedLevel + 100 * clampedLevel - 140;
    if (growthRateId === 5) {
      if (clampedLevel <= 50) return Math.floor((cube * (100 - clampedLevel)) / 50);
      if (clampedLevel <= 68) return Math.floor((cube * (150 - clampedLevel)) / 100);
      if (clampedLevel <= 98) {
        const mod = clampedLevel % 3;
        const factor = 1274 + mod * mod - 9 * mod - 20 * Math.floor(clampedLevel / 3);
        return Math.floor((cube * factor) / 1000);
      }
      return Math.floor((cube * (160 - clampedLevel)) / 100);
    }
    if (growthRateId === 6) {
      if (clampedLevel <= 15) return Math.floor((cube * (Math.floor((clampedLevel + 1) / 3) + 24)) / 50);
      if (clampedLevel <= 35) return Math.floor((cube * (clampedLevel + 14)) / 50);
      return Math.floor((cube * (Math.floor(clampedLevel / 2) + 32)) / 50);
    }
    throw new Error(`Growth rate desconhecido: ${growthRateId}`);
  },
  levelFromExperience(growthRateId, experience) {
    const currentExperience = Math.max(0, Number(experience || 0));
    let currentLevel = 1;
    for (let level = 1; level <= 100; level += 1) {
      if (currentExperience < this.experienceForLevel(growthRateId, level)) return currentLevel;
      currentLevel = level;
    }
    return 100;
  },
  levelFromSpeciesExperience(nationalDexId, experience) {
    const growthRateId = this.speciesGrowthRate[Number(nationalDexId || 0)] || 0;
    if (!growthRateId) throw new Error(`Growth rate nao encontrado para National Dex #${nationalDexId}.`);
    return this.levelFromExperience(growthRateId, experience);
  }
};
