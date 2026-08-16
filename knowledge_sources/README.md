# LLMWiki source workspace

This directory is the publication gate for future ChatMaker LLMWiki pages. It
does not change the canonical board, component, recipe, or verification records
under `packs/`.

Use this local sequence:

1. **Collect** a source into `raw/`. This private working copy is ignored by
   Git and must never enter a release archive.
2. **Clean** it into `cleaned/`, recording the cleaning version and its own
   evidence. This is also ignored by Git and releases.
3. **Structure** one checked-in manifest in `manifests/` with the exact board
   scope, source identity, use boundary, and independent gate values.
4. **Review the source** by setting only `source_reviewed` when its evidence is
   complete. A cleaned file does not review itself.
5. **Approve publication** by setting only `publication_approved`, then adding
   an explicit page declaration below `published/boards/<board-id>/`.
6. **Build a pack** only after `scripts/validate_knowledge_publication.py`
   succeeds. The later pack builder consumes approved declarations; it does not
   treat an unreviewed source as a page.

The governed published layout is:

```text
knowledge_sources/
  published/
    boards/
      <board-id>/
        <section-id>.md
```

The current workspace contains eight approved pages for each of the three
boards (24 pages total). A page must carry the exact six-field YAML frontmatter
contract with its stable ID, exact board ID, section ID, and `source_refs`; its
nonempty body alone is limited to 65,536 UTF-8 bytes. The validator rejects
paths outside that layout, unknown sources, malformed frontmatter, duplicate
stable IDs, and any declared page whose source has not separately received
publication approval.

LLMWiki is a file-system method: ordinary YAML manifests and Markdown files
validated and later packed by ChatMaker. It is not a required external product
or service.
