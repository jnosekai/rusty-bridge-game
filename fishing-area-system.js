(function () {
  "use strict";

  const neutralAffinities = Object.freeze({
    seasons: {
      SPRING: 1,
      SUMMER: 1,
      AUTUMN: 1,
      WINTER: 1
    },
    weather: {
      SUNNY: 1,
      CLOUDY: 1,
      RAIN: 1
    }
  });

  const DEFAULT_AREA_SETTINGS = Object.freeze({
    baseHitRate: 0.12,
    bigFishRate: 0.05,
    sizeMin: 20,
    sizeMax: 45,
    depthType: "MID",
    structureType: "NONE",
    seasonAffinity: neutralAffinities.seasons,
    temperaturePreference: {
      min: null,
      max: null,
      outsideMultiplier: 1
    },
    weatherAffinity: neutralAffinities.weather,
    bigFishAffinity: {
      season: neutralAffinities.seasons,
      weather: neutralAffinities.weather,
      temperatureOutsideMultiplier: 1
    }
  });

  function mergeAreaSettings(override = {}) {
    return {
      ...DEFAULT_AREA_SETTINGS,
      ...override,
      seasonAffinity: {
        ...DEFAULT_AREA_SETTINGS.seasonAffinity,
        ...(override.seasonAffinity || {})
      },
      temperaturePreference: {
        ...DEFAULT_AREA_SETTINGS.temperaturePreference,
        ...(override.temperaturePreference || {})
      },
      weatherAffinity: {
        ...DEFAULT_AREA_SETTINGS.weatherAffinity,
        ...(override.weatherAffinity || {})
      },
      bigFishAffinity: {
        ...DEFAULT_AREA_SETTINGS.bigFishAffinity,
        ...(override.bigFishAffinity || {}),
        season: {
          ...DEFAULT_AREA_SETTINGS.bigFishAffinity.season,
          ...(override.bigFishAffinity?.season || {})
        },
        weather: {
          ...DEFAULT_AREA_SETTINGS.bigFishAffinity.weather,
          ...(override.bigFishAffinity?.weather || {})
        }
      }
    };
  }

  function getTemperatureMultiplier(preference, temperature) {
    if (!Number.isFinite(temperature)) return 1;

    const belowMinimum =
      Number.isFinite(preference.min) &&
      temperature < preference.min;
    const aboveMaximum =
      Number.isFinite(preference.max) &&
      temperature > preference.max;

    return belowMinimum || aboveMaximum
      ? preference.outsideMultiplier
      : 1;
  }

  function clampProbability(value) {
    return Math.max(0, Math.min(1, value));
  }

  function getEffectiveHitRate(area, environment, modifiers = {}) {
    const seasonMultiplier =
      area.seasonAffinity[environment.season] ?? 1;
    const temperatureMultiplier =
      getTemperatureMultiplier(
        area.temperaturePreference,
        environment.temperature
      );
    const weatherMultiplier =
      area.weatherAffinity[environment.weather] ?? 1;

    return clampProbability(
      area.baseHitRate *
      seasonMultiplier *
      temperatureMultiplier *
      weatherMultiplier *
      (modifiers.seasonMultiplier ?? 1) *
      (modifiers.otherMultiplier ?? 1)
    );
  }

  function getEffectiveBigFishRate(area, environment, modifiers = {}) {
    const affinity = area.bigFishAffinity;
    const temperatureMultiplier = getTemperatureMultiplier(
      {
        ...area.temperaturePreference,
        outsideMultiplier: affinity.temperatureOutsideMultiplier
      },
      environment.temperature
    );

    return clampProbability(
      area.bigFishRate *
      (affinity.season[environment.season] ?? 1) *
      (affinity.weather[environment.weather] ?? 1) *
      temperatureMultiplier *
      (modifiers.seasonMultiplier ?? 1) *
      (modifiers.otherMultiplier ?? 1)
    );
  }

  function runFoundationChecks() {
    const area = mergeAreaSettings({
      baseHitRate: 0.12,
      depthType: "SHALLOW",
      structureType: "COVE",
      seasonAffinity: { SPRING: 1.1, WINTER: 0.9 },
      temperaturePreference: {
        min: 12,
        max: 20,
        outsideMultiplier: 0.8
      },
      weatherAffinity: { CLOUDY: 1.05 }
    });
    const neutral = getEffectiveHitRate(area, {
      season: "SUMMER",
      weather: "SUNNY",
      temperature: 16
    });
    const spring = getEffectiveHitRate(area, {
      season: "SPRING",
      weather: "SUNNY",
      temperature: 16
    });
    const outsideTemperature = getEffectiveHitRate(area, {
      season: "SUMMER",
      weather: "SUNNY",
      temperature: 25
    });
    const cloudy = getEffectiveHitRate(area, {
      season: "SUMMER",
      weather: "CLOUDY",
      temperature: 16
    });

    return {
      nestedDefaultsMerged:
        area.seasonAffinity.AUTUMN === 1 &&
        area.weatherAffinity.RAIN === 1,
      areaTraitsRetained:
        area.depthType === "SHALLOW" &&
        area.structureType === "COVE",
      seasonChangesRate: spring > neutral,
      temperatureChangesRate: outsideTemperature < neutral,
      weatherChangesRate: cloudy > neutral,
      neutralBalanceRetained:
        Math.abs(neutral - area.baseHitRate) < 0.000001
    };
  }

  window.GreenBoatFishingAreas = Object.freeze({
    DEFAULT_AREA_SETTINGS,
    mergeAreaSettings,
    getEffectiveHitRate,
    getEffectiveBigFishRate,
    runFoundationChecks
  });
})();
