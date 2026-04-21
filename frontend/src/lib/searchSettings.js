export const DEFAULT_SEARCH_SETTINGS = {
  default_results_per_page: 50,
  similarity_threshold: 0,
  weights: {
    semantic: 0.55,
    design: 0.2,
    color: 0.15,
    texture: 0.1,
  },
  enable_sub_part_localization: true,
  bounding_box_effect: 'scanner',
};

export const SEARCH_PRESETS = {
  balanced: {
    label: 'Balanced',
    description: 'Good general-purpose matching across meaning, layout, color, and texture.',
    settings: {
      similarity_threshold: 0,
      weights: {
        semantic: 0.55,
        design: 0.2,
        color: 0.15,
        texture: 0.1,
      },
    },
  },
  strict: {
    label: 'Strict / High Precision',
    description: 'Reduces noisy matches by favoring semantic agreement and a higher threshold.',
    settings: {
      similarity_threshold: 0.35,
      weights: {
        semantic: 0.7,
        design: 0.15,
        color: 0.1,
        texture: 0.05,
      },
    },
  },
  color: {
    label: 'Color Match',
    description: 'Prioritizes palette and color placement.',
    settings: {
      similarity_threshold: 0.2,
      weights: {
        semantic: 0.3,
        design: 0.1,
        color: 0.5,
        texture: 0.1,
      },
    },
  },
  layout: {
    label: 'Layout Match',
    description: 'Prioritizes composition, edges, and structural similarity.',
    settings: {
      similarity_threshold: 0.2,
      weights: {
        semantic: 0.35,
        design: 0.45,
        color: 0.1,
        texture: 0.1,
      },
    },
  },
  semantic: {
    label: 'Semantic Match',
    description: 'Prioritizes what the image represents over palette or texture.',
    settings: {
      similarity_threshold: 0.25,
      weights: {
        semantic: 0.8,
        design: 0.1,
        color: 0.05,
        texture: 0.05,
      },
    },
  },
};

const EFFECTS = new Set(['scanner', 'simple', 'off']);

function clampNumber(value, min, max, fallback) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.min(max, Math.max(min, parsed));
}

export function normalizeSearchSettings(payload = {}) {
  const defaults = DEFAULT_SEARCH_SETTINGS;
  const rawWeights = payload.weights || {};

  const weights = {
    semantic: Math.max(
      0,
      clampNumber(rawWeights.semantic, 0, Number.MAX_SAFE_INTEGER, defaults.weights.semantic),
    ),
    design: Math.max(
      0,
      clampNumber(rawWeights.design, 0, Number.MAX_SAFE_INTEGER, defaults.weights.design),
    ),
    color: Math.max(
      0,
      clampNumber(rawWeights.color, 0, Number.MAX_SAFE_INTEGER, defaults.weights.color),
    ),
    texture: Math.max(
      0,
      clampNumber(rawWeights.texture, 0, Number.MAX_SAFE_INTEGER, defaults.weights.texture),
    ),
  };

  const totalWeight = Object.values(weights).reduce((sum, value) => sum + value, 0);
  const normalizedWeights =
    totalWeight > 0
      ? Object.fromEntries(
          Object.entries(weights).map(([key, value]) => [key, value / totalWeight]),
        )
      : { ...defaults.weights };

  const effect = EFFECTS.has(payload.bounding_box_effect)
    ? payload.bounding_box_effect
    : defaults.bounding_box_effect;

  return {
    default_results_per_page: Math.round(
      clampNumber(
        payload.default_results_per_page,
        0,
        100,
        defaults.default_results_per_page,
      ),
    ),
    similarity_threshold: clampNumber(
      payload.similarity_threshold,
      0,
      1,
      defaults.similarity_threshold,
    ),
    weights: normalizedWeights,
    enable_sub_part_localization:
      typeof payload.enable_sub_part_localization === 'boolean'
        ? payload.enable_sub_part_localization
        : defaults.enable_sub_part_localization,
    bounding_box_effect: effect,
  };
}

export function applySearchPreset(baseSettings, presetKey) {
  const preset = SEARCH_PRESETS[presetKey];
  if (!preset) {
    return normalizeSearchSettings(baseSettings);
  }

  return normalizeSearchSettings({
    ...baseSettings,
    ...preset.settings,
    weights: {
      ...(baseSettings?.weights || {}),
      ...(preset.settings.weights || {}),
    },
  });
}
