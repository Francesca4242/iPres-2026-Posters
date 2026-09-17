# pdf.js 3.11.174

Mozilla's PDF renderer, vendored so that the poster viewer keeps working on
conference wifi with no CDN reachable. Copyright 2023 Mozilla Foundation,
Apache License 2.0 — see https://github.com/mozilla/pdf.js.

Files were taken verbatim from
`https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/`.

`assets/js/site.js` loads these first and only falls back to the CDN if they
are missing. To upgrade, drop in a newer `pdf.min.js` + `pdf.worker.min.js`
pair and bump `PDFJS_VERSION` in `assets/js/site.js`.
