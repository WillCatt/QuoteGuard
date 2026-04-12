# Corpus Notes

This file captures corpus inspection notes before a parser choice is locked in.

## Scope

- Product vertical: `home_contents`
- Target corpus size: 5 to 8 Australian insurer PDS documents
- PDFs should not be committed to the repository

## Inspection Checklist

- Heading hierarchy quality
- Multi-column layout issues
- Table extraction quality
- Footnotes and cross-references
- Page-number consistency
- OCR/scanned-page quality
- Copyright and usage notices

## Expected Risks

- Insurance tables will likely break naive reading order
- Nested exclusions are easy to flatten incorrectly
- Section path fidelity matters more than paragraph beauty
- A few problematic PDFs should be dropped instead of forcing the parser to accommodate everything

## Pending Manual Notes

Use this document to record concrete findings per insurer once the corpus is fetched.
