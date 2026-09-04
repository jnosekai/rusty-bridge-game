(function () {
  "use strict";

  const neutralSeasonAffinity = {
    SPRING: 1,
    SUMMER: 1,
    AUTUMN: 1,
    WINTER: 1
  };

  const neutralWeatherAffinity = {
    SUNNY: 1,
    CLOUDY: 1,
    RAIN: 1
  };

  const lureDefinitions = [
    {
      id: "popper_natural",
      name: "POPPER",
      family: "POPPER",
      image: "assets/lures/popper_natural.png",
      color: "NATURAL",
      unlocked: true,
      depthType: "SURFACE",
      seasonAffinity: { ...neutralSeasonAffinity },
      weatherAffinity: { ...neutralWeatherAffinity },
      temperatureAffinity: {
        min: null,
        max: null,
        outsideMultiplier: 1
      },
      structureAffinity: {},
      hitRateMultiplier: 1,
      bigFishMultiplier: 1
    },
    {
      id: "shallow_crank_natural",
      name: "SHALLOW CRANK",
      family: "SHALLOW_CRANK",
      image: "assets/lures/shallow_crank_natural.png",
      color: "NATURAL",
      unlocked: true,
      depthType: "SHALLOW",
      seasonAffinity: { ...neutralSeasonAffinity },
      weatherAffinity: { ...neutralWeatherAffinity },
      temperatureAffinity: {
        min: null,
        max: null,
        outsideMultiplier: 1
      },
      structureAffinity: {},
      hitRateMultiplier: 1,
      bigFishMultiplier: 1
    },
    {
      id: "straight_worm_green_pumpkin",
      name: "STRAIGHT WORM",
      family: "STRAIGHT_WORM",
      image: "assets/lures/straight_worm_green_pumpkin.png",
      color: "GREEN_PUMPKIN",
      unlocked: true,
      depthType: "VARIABLE",
      seasonAffinity: { ...neutralSeasonAffinity },
      weatherAffinity: { ...neutralWeatherAffinity },
      temperatureAffinity: {
        min: null,
        max: null,
        outsideMultiplier: 1
      },
      structureAffinity: {},
      hitRateMultiplier: 1,
      bigFishMultiplier: 1
    }
  ];

  const lureById = new Map(
    lureDefinitions.map((lure) => [lure.id, lure])
  );

  function getLureById(id) {
    return lureById.get(id) || null;
  }

  function getUnlockedLures() {
    return lureDefinitions.filter((lure) => lure.unlocked);
  }

  function getSafeSelectedLure(id) {
    const selected = getLureById(id);
    return selected?.unlocked
      ? selected
      : lureDefinitions[0];
  }

  window.GreenBoatLures = Object.freeze({
    DEFAULT_LURE_ID: lureDefinitions[0].id,
    lureDefinitions,
    getLureById,
    getUnlockedLures,
    getSafeSelectedLure
  });
})();
