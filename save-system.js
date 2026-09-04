(function () {
  "use strict";

  const SAVE_KEY = "greenBoat.saveData";
  const CORRUPT_BACKUP_PREFIX = "greenBoat.saveData.backup.";
  const CURRENT_SAVE_VERSION = 2;

  function clone(value) {
    if (value === undefined) return undefined;
    return JSON.parse(JSON.stringify(value));
  }

  function isPlainObject(value) {
    return Boolean(value) &&
      typeof value === "object" &&
      !Array.isArray(value);
  }

  function createDefaultSave() {
    return {
      saveVersion: CURRENT_SAVE_VERSION,
      player: {
        biggestFish: 0,
        totalCatch: 0,
        totalTrips: 0
      },
      loadout: {
        selectedLureId: "popper_natural"
      },
      cards: [],
      items: [],
      achievements: [],
      records: {
        areaRecords: {},
        seasonRecords: {}
      }
    };
  }

  /* 既存値と未知の将来項目を残し、足りない項目だけ補う。 */
  function mergeMissing(defaultValue, savedValue) {
    if (Array.isArray(defaultValue)) {
      return Array.isArray(savedValue) ? clone(savedValue) : clone(defaultValue);
    }

    if (isPlainObject(defaultValue)) {
      const result = isPlainObject(savedValue) ? clone(savedValue) : {};

      for (const [key, value] of Object.entries(defaultValue)) {
        result[key] = key in result
          ? mergeMissing(value, result[key])
          : clone(value);
      }

      return result;
    }

    return savedValue === undefined ? defaultValue : savedValue;
  }

  function normalizeIdList(value, fieldName, recovery) {
    if (!Array.isArray(value)) {
      recovery[fieldName] = clone(value);
      return [];
    }

    const ids = [];
    const unsupported = [];

    for (const entry of value) {
      const id = typeof entry === "string"
        ? entry
        : isPlainObject(entry) && typeof entry.id === "string"
          ? entry.id
          : null;

      if (id) {
        if (!ids.includes(id)) ids.push(id);
      } else {
        unsupported.push(clone(entry));
      }
    }

    if (unsupported.length) recovery[fieldName] = unsupported;
    return ids;
  }

  function normalizeNonNegativeNumber(value, fallback, fieldName, recovery) {
    if (typeof value === "number" && Number.isFinite(value) && value >= 0) {
      return value;
    }

    recovery[fieldName] = clone(value);
    return fallback;
  }

  /*
    新しいsaveVersionを追加するときは、次の番号の関数を追加する。
    例: 1(data) { ...; data.saveVersion = 2; return data; }
  */
  const migrations = {
    0(oldSave) {
      const migrated = isPlainObject(oldSave) ? clone(oldSave) : {};
      migrated.player = isPlainObject(migrated.player) ? migrated.player : {};

      for (const field of ["biggestFish", "totalCatch", "totalTrips"]) {
        if (migrated.player[field] === undefined && migrated[field] !== undefined) {
          migrated.player[field] = migrated[field];
        }
      }

      migrated.saveVersion = 1;
      return migrated;
    },
    1(oldSave) {
      const migrated = isPlainObject(oldSave) ? clone(oldSave) : {};
      migrated.loadout = isPlainObject(migrated.loadout)
        ? migrated.loadout
        : {};
      if (typeof migrated.loadout.selectedLureId !== "string") {
        migrated.loadout.selectedLureId = "popper_natural";
      }
      migrated.saveVersion = 2;
      return migrated;
    }
  };

  function migrateSaveData(input) {
    let data = isPlainObject(input) ? clone(input) : {};
    let version = Number.isInteger(data.saveVersion) ? data.saveVersion : 0;

    if (version > CURRENT_SAVE_VERSION) {
      return { data, isFutureVersion: true };
    }

    while (version < CURRENT_SAVE_VERSION) {
      const migrate = migrations[version];
      if (typeof migrate !== "function") {
        throw new Error(`Missing save migration: ${version} -> ${version + 1}`);
      }

      data = migrate(data);
      version = data.saveVersion;
    }

    return { data, isFutureVersion: false };
  }

  function normalizeSaveData(input) {
    const source = isPlainObject(input) ? input : {};
    const recovery = {};

    for (const fieldName of ["cards", "items", "achievements"]) {
      if (source[fieldName] !== undefined && !Array.isArray(source[fieldName])) {
        recovery[fieldName] = clone(source[fieldName]);
      }
    }

    if (source.player !== undefined && !isPlainObject(source.player)) {
      recovery.player = clone(source.player);
    }

    if (source.records !== undefined && !isPlainObject(source.records)) {
      recovery.records = clone(source.records);
    } else if (isPlainObject(source.records)) {
      if (source.records.areaRecords !== undefined &&
          !isPlainObject(source.records.areaRecords)) {
        recovery["records.areaRecords"] = clone(source.records.areaRecords);
      }
      if (source.records.seasonRecords !== undefined &&
          !isPlainObject(source.records.seasonRecords)) {
        recovery["records.seasonRecords"] = clone(source.records.seasonRecords);
      }
    }

    if (source.loadout !== undefined && !isPlainObject(source.loadout)) {
      recovery.loadout = clone(source.loadout);
    }

    const normalized = mergeMissing(createDefaultSave(), source);

    normalized.player.biggestFish = normalizeNonNegativeNumber(
      normalized.player.biggestFish, 0, "player.biggestFish", recovery
    );
    normalized.player.totalCatch = normalizeNonNegativeNumber(
      normalized.player.totalCatch, 0, "player.totalCatch", recovery
    );
    normalized.player.totalTrips = normalizeNonNegativeNumber(
      normalized.player.totalTrips, 0, "player.totalTrips", recovery
    );

    if (typeof normalized.loadout.selectedLureId !== "string") {
      recovery["loadout.selectedLureId"] =
        clone(normalized.loadout.selectedLureId);
      normalized.loadout.selectedLureId = "popper_natural";
    }

    normalized.cards = normalizeIdList(normalized.cards, "cards", recovery);
    normalized.items = normalizeIdList(normalized.items, "items", recovery);
    normalized.achievements = normalizeIdList(
      normalized.achievements, "achievements", recovery
    );

    if (!isPlainObject(normalized.records)) {
      recovery.records = clone(normalized.records);
      normalized.records = createDefaultSave().records;
    }
    if (source.records?.areaRecords === undefined &&
        isPlainObject(source.records?.byArea)) {
      normalized.records.areaRecords = source.records.byArea;
    }
    if (source.records?.seasonRecords === undefined &&
        isPlainObject(source.records?.bySeason)) {
      normalized.records.seasonRecords = source.records.bySeason;
    }

    normalized.records.areaRecords = isPlainObject(normalized.records.areaRecords)
      ? normalized.records.areaRecords
      : {};
    normalized.records.seasonRecords = isPlainObject(normalized.records.seasonRecords)
      ? normalized.records.seasonRecords
      : {};

    if (Object.keys(recovery).length) {
      normalized.recovery = {
        ...(isPlainObject(normalized.recovery) ? normalized.recovery : {}),
        preservedInvalidFields: {
          ...(normalized.recovery?.preservedInvalidFields || {}),
          ...recovery
        }
      };
    }

    normalized.saveVersion = CURRENT_SAVE_VERSION;
    return normalized;
  }

  function createRepository(storage, options = {}) {
    const now = options.now || Date.now;
    let currentData = null;
    let readOnly = false;

    function writeBackup(rawValue, reason) {
      try {
        const key = `${CORRUPT_BACKUP_PREFIX}${now()}`;
        storage.setItem(key, JSON.stringify({ reason, rawValue }));
        return key;
      } catch (error) {
        console.error("Could not back up save data.", error);
        return null;
      }
    }

    function persist(data) {
      try {
        storage.setItem(SAVE_KEY, JSON.stringify(data));
        return true;
      } catch (error) {
        console.error("Could not save game data.", error);
        return false;
      }
    }

    function load() {
      let rawValue = null;

      try {
        rawValue = storage.getItem(SAVE_KEY);
      } catch (error) {
        console.error("Could not read game data.", error);
        currentData = createDefaultSave();
        return clone(currentData);
      }

      if (rawValue === null) {
        currentData = createDefaultSave();
        persist(currentData);
        return clone(currentData);
      }

      try {
        const parsed = JSON.parse(rawValue);
        const migrationResult = migrateSaveData(parsed);

        if (migrationResult.isFutureVersion) {
          readOnly = true;
          currentData = migrationResult.data;
          return clone(currentData);
        }

        currentData = normalizeSaveData(migrationResult.data);
        persist(currentData);
        return clone(currentData);
      } catch (error) {
        writeBackup(rawValue, error.message);
        currentData = createDefaultSave();
        persist(currentData);
        return clone(currentData);
      }
    }

    function get() {
      if (!currentData) return load();
      return clone(currentData);
    }

    function save(data) {
      if (readOnly) return get();
      currentData = normalizeSaveData(data);
      persist(currentData);
      return clone(currentData);
    }

    function update(mutator) {
      if (readOnly) return get();
      const draft = get();
      mutator(draft);
      return save(draft);
    }

    return { load, get, save, update, isReadOnly: () => readOnly };
  }

  function createMemoryStorage(initialEntries = {}) {
    const values = new Map(Object.entries(initialEntries));
    return {
      getItem: key => values.has(key) ? values.get(key) : null,
      setItem: (key, value) => values.set(key, String(value)),
      keys: () => Array.from(values.keys())
    };
  }

  function runFoundationChecks() {
    const firstStorage = createMemoryStorage();
    const firstRepository = createRepository(firstStorage, { now: () => 1 });
    const initial = firstRepository.load();
    firstRepository.update(data => {
      data.player.biggestFish = 51.2;
      data.player.totalCatch = 7;
      data.loadout.selectedLureId = "straight_worm_green_pumpkin";
      data.cards.push("card_001");
      data.futureExtension = { retained: true };
    });
    const reloaded = createRepository(firstStorage).load();

    const legacyStorage = createMemoryStorage({
      [SAVE_KEY]: JSON.stringify({
        biggestFish: 48.6,
        totalCatch: 3,
        cards: ["card_001"],
        items: ["item_001"],
        unknownLegacyValue: "keep"
      })
    });
    const migrated = createRepository(legacyStorage).load();

    const brokenStorage = createMemoryStorage({ [SAVE_KEY]: "{broken" });
    const recovered = createRepository(brokenStorage, { now: () => 2 }).load();

    return {
      initialSaveCreated: initial.saveVersion === CURRENT_SAVE_VERSION,
      reloadRetained: reloaded.player.biggestFish === 51.2 &&
        reloaded.loadout.selectedLureId === "straight_worm_green_pumpkin" &&
        reloaded.cards.includes("card_001") &&
        reloaded.futureExtension.retained === true,
      legacyMigrated: migrated.saveVersion === CURRENT_SAVE_VERSION &&
        migrated.player.biggestFish === 48.6 &&
        migrated.loadout.selectedLureId === "popper_natural" &&
        migrated.cards.includes("card_001") &&
        migrated.items.includes("item_001") &&
        Array.isArray(migrated.achievements) &&
        isPlainObject(migrated.records.areaRecords) &&
        isPlainObject(migrated.records.seasonRecords) &&
        migrated.unknownLegacyValue === "keep",
      corruptDataBackedUp: recovered.saveVersion === CURRENT_SAVE_VERSION &&
        brokenStorage.keys().some(key => key.startsWith(CORRUPT_BACKUP_PREFIX))
    };
  }

  window.GreenBoatSave = Object.freeze({
    SAVE_KEY,
    CURRENT_SAVE_VERSION,
    createDefaultSave,
    migrateSaveData,
    createRepository,
    runFoundationChecks
  });
})();
