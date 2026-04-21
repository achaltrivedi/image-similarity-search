# Search Accuracy Workflow

Use this workflow when tuning ranking rules or preset weights.

## 1. Backfill Metadata

Existing rows only had `file_size` in `minio_metadata`. Run the metadata backfill so precision ranking can use dimensions, aspect ratio, dominant colors, visual complexity, and perceptual hashes.

```bash
python tools/backfill_metadata.py --dry-run --limit 10
python tools/backfill_metadata.py
```

The command is resumable in practice: rerunning it recomputes and overwrites metadata for each indexed asset.

## 2. Build a Small Evaluation Set

Create 10-20 representative query images and manually record expected strong matches and obvious bad matches. Focus on business-critical asset types first, such as PDFs, AI thumbnails, repeating product layouts, or color-sensitive designs.

Recommended metrics:

- Precision at 3: how many of the first 3 results are useful.
- Precision at 10: how many of the first 10 results are useful.
- Bad match in top 3: whether any clearly irrelevant result appears too high.

## 3. Tune Safely

Compare the same queries before and after ranking changes. Accept changes only when top-result precision improves without hiding known good matches.

For noisy results, start with the `Strict / High Precision` profile in the UI. For broader discovery, use `Balanced`.
