# LLMWiki knowledge-source pipeline

This is the local, reviewable route from a useful board source to a future
LLMWiki pack. It deliberately keeps source handling, publishing approval, and
hardware evidence separate.

## Before writing a page

1. Put a working copy in `knowledge_sources/raw/`. It is intentionally ignored
   by Git and release archives.
2. Make any readable, reduced working copy in `knowledge_sources/cleaned/`.
   Record the cleaner/version and evidence in the source manifest. Cleaning is
   not source review.
3. Add or update one `knowledge_sources/manifests/<board-id>.yaml` manifest.
   It names the source, exact board, source type, canonical URL (or an
   owned-local description and SHA-256), license/use boundary, cleaning version
   and review date.
4. Record `cleaning_verified`, `source_reviewed`, and
   `publication_approved` independently. Each has its own status, date, and
   evidence. Never copy a verified status from one gate to another.
5. When a maintainer approves a specific page, set that source manifest's
   `publication_approved` gate to `verified` and add a page declaration. Use a
   stable page ID and exactly this path shape:

   ```text
   published/boards/<board-id>/<section-id>.md
   ```

6. Add the Markdown page only after that declaration. Its YAML frontmatter must
   include `schema_version: "1.0"`, `kind: llmwiki-page`, `stable_id`,
   `board_id`, `section_id`, and `source_refs`. `source_refs` must name the
   checked-in manifest IDs used by the page.

## Validate before a later pack build

Run this check-only command from the repository root:

```powershell
python scripts/validate_knowledge_publication.py --root .
```

It prints structured JSON and returns a nonzero exit code for a missing board
manifest, an unapproved declaration, an escaping path, malformed frontmatter,
unsupported schema version, duplicate stable ID, missing source reference, or a
page body over 65,536 UTF-8 bytes. It writes nothing and is suitable for CI.

LLMWiki here means a file-system method: YAML records and Markdown pages that
can later be built into a passive pack. No external LLMWiki product is required.
The current task creates the gate only; it does not publish pages or assert that
source, compile, upload, serial, or physical hardware evidence has changed.
