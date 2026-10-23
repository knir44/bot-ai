# 02 - Chunking

An embedding squeezes a whole text into **one** vector. Feed it a 20-page PDF and you get a blurry average of everything in it. So we cut documents into **chunks**, and each chunk gets its own sharp vector and its own entry in the keyword index.

## The trade-off

| Chunks too **small** (e.g. 100 chars) | Chunks too **large** (e.g. 5000 chars) |
|---|---|
| Lose context: "He landed it manually" - who? | Vector is a blur of many topics |
| Answers split across chunks | Prompt is stuffed with irrelevant text (cost, distraction) |
| More chunks -> more storage | BM25 length normalisation penalises it |

There is no universally right size. 500-1000 characters (roughly 100-250 words) is a good default for prose; this project uses `CHUNK_SIZE=800`. The only honest way to choose is to measure with [your own questions](07-evaluation.md).

## Recursive splitting

`chunking.py` tries the most natural boundary first and only falls back when a piece is still too big:

```
paragraph break "\n\n"  ->  line break "\n"  ->  sentence ". "  ->  word " "  ->  raw characters
```

A chunk that ends mid-sentence hurts both retrieval signals, so we avoid hard cuts unless a single "word" is longer than the whole chunk (e.g. a base64 blob).

## Overlap

Consider these two neighbouring chunks of `apollo_11.txt`:

```
... Eagle touched down in the Sea of Tranquility on July 20, 1969. | During the descent the onboard computer ...
```

If the question is "when did Eagle land?" and the cut falls exactly at `|`, each half only has part of the story. **Overlap** repeats the last ~100 characters of a chunk at the start of the next, so a fact near a boundary lives intact in at least one chunk.

Cost: ~10-15% more storage. Setting `CHUNK_OVERLAP=0` turns it off.

## What chunking does *not* solve

- **Tables and figures** in PDFs come out as jumbled text (`pypdf` extracts text only).
- **Scanned PDFs** contain no text at all - you would need OCR. The uploader reports this instead of silently indexing nothing.
- **Headings**: a chunk from the middle of a section loses its title. Production systems often prepend the heading/filename to each chunk. Try it: in `ingestion.py`, prefix each chunk with the document title before embedding, then re-run the [evaluation](07-evaluation.md).

## Experiments

1. Set `CHUNK_SIZE=300` in `.env`, restart the backend, press **Clear all** in the 📎 panel of the chat widget, click **Load sample corpus** again, and compare `scripts.evaluate` output.
2. Same with `CHUNK_SIZE=3000`. Look at the **Embedding map**: do the dots for one file still form a tight group?
