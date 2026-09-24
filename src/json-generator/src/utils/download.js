import { saveAs } from 'file-saver';

/** Save text as a file. CSVs are plain UTF-8 without a BOM, as v4 asks. */
export function downloadText(fileName, text, type = 'text/csv;charset=utf-8') {
  saveAs(new Blob([text], { type }), fileName);
}

/** Read a File as text. */
export function readText(file) {
  return file.text();
}
