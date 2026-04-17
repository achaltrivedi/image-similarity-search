import { useEffect, useMemo, useState } from 'react';
import {
  SlidersHorizontal,
  ScanSearch,
  Sparkles,
  SquareDashedMousePointer,
  Save,
  RotateCcw,
  Loader2,
} from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { useSearchSettings } from '@/context/SearchSettingsContext';
import {
  DEFAULT_SEARCH_SETTINGS,
  normalizeSearchSettings,
} from '@/lib/searchSettings';

const WEIGHT_FIELDS = [
  { key: 'semantic', label: 'Semantic', accent: 'bg-emerald-500' },
  { key: 'design', label: 'Design', accent: 'bg-sky-500' },
  { key: 'color', label: 'Color', accent: 'bg-amber-500' },
  { key: 'texture', label: 'Texture', accent: 'bg-fuchsia-500' },
];

const BOUNDING_BOX_OPTIONS = [
  {
    value: 'scanner',
    label: 'Scanner',
    description: 'Animated trace, sweep line, and spotlight overlay.',
    icon: ScanSearch,
  },
  {
    value: 'simple',
    label: 'Simple Highlight',
    description: 'Static polygon outline for a calmer result card.',
    icon: SquareDashedMousePointer,
  },
  {
    value: 'off',
    label: 'Off',
    description: 'Hide match overlays in result cards entirely.',
    icon: Sparkles,
  },
];

function formatPercent(value) {
  return `${Math.round(value * 100)}%`;
}

export default function Settings() {
  const { settings, loading, saving, saveSettings } = useSearchSettings();
  const [draft, setDraft] = useState(DEFAULT_SEARCH_SETTINGS);

  useEffect(() => {
    setDraft(settings);
  }, [settings]);

  const normalizedDraft = useMemo(() => normalizeSearchSettings(draft), [draft]);
  const isDirty =
    JSON.stringify(normalizedDraft) !== JSON.stringify(normalizeSearchSettings(settings));

  const handleWeightChange = (key, value) => {
    setDraft((current) => ({
      ...current,
      weights: {
        ...current.weights,
        [key]: Number(value),
      },
    }));
  };

  const handleSave = async () => {
    try {
      await saveSettings(normalizedDraft);
      toast.success('Search settings saved');
    } catch (err) {
      toast.error(err.message || 'Failed to save settings');
    }
  };

  const handleReset = () => {
    setDraft(settings);
  };

  return (
    <div className='container mx-auto px-4 py-16'>
      <div className='mb-8 flex items-start justify-between gap-6'>
        <div>
          <div className='mb-3 inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1 text-xs font-medium text-muted-foreground'>
            <SlidersHorizontal className='h-3.5 w-3.5' />
            Search Controls
          </div>
          <h1 className='text-3xl font-bold tracking-tight'>Settings</h1>
          <p className='mt-2 max-w-2xl text-sm text-muted-foreground'>
            Tune the default search experience, rebalance similarity ranking, and
            control how localized matches are visualized in the results grid.
          </p>
        </div>
        <div className='flex items-center gap-2'>
          <Button variant='outline' onClick={handleReset} disabled={!isDirty || saving}>
            <RotateCcw className='h-4 w-4' />
            Reset
          </Button>
          <Button onClick={handleSave} disabled={!isDirty || saving || loading}>
            {saving ? (
              <Loader2 className='h-4 w-4 animate-spin' />
            ) : (
              <Save className='h-4 w-4' />
            )}
            Save Changes
          </Button>
        </div>
      </div>

      <div className='grid gap-6 xl:grid-cols-[1.15fr_0.85fr]'>
        <Card>
          <CardHeader>
            <CardTitle className='text-xl'>Search Defaults</CardTitle>
            <CardDescription>
              These values are applied automatically whenever a new search starts.
            </CardDescription>
          </CardHeader>
          <CardContent className='space-y-8'>
            <div className='grid gap-6 md:grid-cols-2'>
              <div className='space-y-2'>
                <label className='text-sm font-medium text-foreground'>
                  Default Results Per Page
                </label>
                <Input
                  type='number'
                  min='1'
                  max='100'
                  value={draft.default_results_per_page}
                  onChange={(event) =>
                    setDraft((current) => ({
                      ...current,
                      default_results_per_page: Number(event.target.value),
                    }))
                  }
                />
                <p className='text-xs text-muted-foreground'>
                  Controls how many matches load in the first search page.
                </p>
              </div>

              <div className='space-y-2'>
                <div className='flex items-center justify-between gap-3'>
                  <label className='text-sm font-medium text-foreground'>
                    Similarity Threshold
                  </label>
                  <Badge variant='outline'>
                    {formatPercent(draft.similarity_threshold)}
                  </Badge>
                </div>
                <input
                  type='range'
                  min='0'
                  max='1'
                  step='0.01'
                  value={draft.similarity_threshold}
                  onChange={(event) =>
                    setDraft((current) => ({
                      ...current,
                      similarity_threshold: Number(event.target.value),
                    }))
                  }
                  className='h-2 w-full cursor-pointer accent-primary'
                />
                <p className='text-xs text-muted-foreground'>
                  Higher values hide weaker matches sooner.
                </p>
              </div>
            </div>

            <div className='rounded-xl border border-border/70 bg-muted/20 p-4'>
              <div className='flex items-start justify-between gap-4'>
                <div>
                  <h3 className='text-sm font-semibold text-foreground'>
                    Sub-part Localization
                  </h3>
                  <p className='mt-1 text-xs text-muted-foreground'>
                    When enabled, the backend attempts to find the matching region
                    inside each result image.
                  </p>
                </div>
                <label className='inline-flex cursor-pointer items-center gap-2 rounded-full border border-border bg-background px-3 py-2 text-sm font-medium'>
                  <input
                    type='checkbox'
                    className='h-4 w-4 accent-primary'
                    checked={draft.enable_sub_part_localization}
                    onChange={(event) =>
                      setDraft((current) => ({
                        ...current,
                        enable_sub_part_localization: event.target.checked,
                      }))
                    }
                  />
                  Enabled
                </label>
              </div>
            </div>

            <div className='space-y-4'>
              <div>
                <h3 className='text-sm font-semibold text-foreground'>
                  Search Mode Weights
                </h3>
                <p className='mt-1 text-xs text-muted-foreground'>
                  These weights are normalized automatically, so you can focus on
                  relative importance instead of perfect totals.
                </p>
              </div>

              <div className='space-y-4'>
                {WEIGHT_FIELDS.map(({ key, label, accent }) => (
                  <div key={key} className='space-y-2'>
                    <div className='flex items-center justify-between gap-3'>
                      <div className='flex items-center gap-2'>
                        <span className={cn('h-2.5 w-2.5 rounded-full', accent)} />
                        <span className='text-sm font-medium text-foreground'>
                          {label}
                        </span>
                      </div>
                      <Badge variant='outline'>
                        {formatPercent(normalizedDraft.weights[key])}
                      </Badge>
                    </div>
                    <input
                      type='range'
                      min='0'
                      max='1'
                      step='0.01'
                      value={draft.weights[key]}
                      onChange={(event) => handleWeightChange(key, event.target.value)}
                      className='h-2 w-full cursor-pointer accent-primary'
                    />
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className='text-xl'>Bounding Box Effect</CardTitle>
            <CardDescription>
              Choose how localized matches should appear when a result includes a
              detected region.
            </CardDescription>
          </CardHeader>
          <CardContent className='space-y-4'>
            {BOUNDING_BOX_OPTIONS.map(({ value, label, description, icon: Icon }) => {
              const selected = draft.bounding_box_effect === value;
              return (
                <button
                  key={value}
                  type='button'
                  onClick={() =>
                    setDraft((current) => ({
                      ...current,
                      bounding_box_effect: value,
                    }))
                  }
                  className={cn(
                    'w-full rounded-2xl border p-4 text-left transition-all',
                    selected
                      ? 'border-primary bg-primary/8 shadow-sm'
                      : 'border-border bg-card hover:border-primary/40 hover:bg-accent/30',
                  )}
                >
                  <div className='flex items-start gap-3'>
                    <div
                      className={cn(
                        'mt-0.5 rounded-xl p-2',
                        selected ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground',
                      )}
                    >
                      <Icon className='h-4 w-4' />
                    </div>
                    <div>
                      <div className='flex items-center gap-2'>
                        <span className='text-sm font-semibold text-foreground'>
                          {label}
                        </span>
                        {selected && <Badge>Active</Badge>}
                      </div>
                      <p className='mt-1 text-xs leading-5 text-muted-foreground'>
                        {description}
                      </p>
                    </div>
                  </div>
                </button>
              );
            })}

            <div className='rounded-xl border border-dashed border-border p-4 text-xs leading-5 text-muted-foreground'>
              The effect choice changes the frontend only. The localization toggle
              above controls whether the backend computes match regions at all.
            </div>

            {loading && (
              <div className='flex items-center gap-2 text-sm text-muted-foreground'>
                <Loader2 className='h-4 w-4 animate-spin' />
                Loading saved settings...
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
