# ChatCAD verification

Use four separate states:

1. `source_reviewed`: the mechanical value has a traceable source.
2. `model_generated`: DXF, SVG, SCAD or STL was written successfully.
3. `file_opened`: the target CAD, slicer or browser opened the artifact.
4. `physical_fit`: the real board, fastener and connector were tested.

Do not promote an earlier state into a later one. For a first print, recommend a small hole or connector coupon before the full enclosure.
