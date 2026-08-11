/**
 * Turn a byte count into something a human can read.
 *
 * formatFileSize(0)       -> "0 B"
 * formatFileSize(2048)    -> "2 KB"
 * formatFileSize(1500000) -> "1.4 MB"
 *
 * @param {number} bytes
 * @returns {string}
 */
export function formatFileSize(bytes) {
  if (!Number.isFinite(bytes) || bytes < 0) return "unknown size";
  if (bytes < 1024) return `${bytes} B`;

  const units = ["KB", "MB", "GB"];
  let size = bytes;
  let unitIndex = -1;

  // Divide by 1024 until the number is small enough to read comfortably.
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }

  // One decimal place, but drop a trailing ".0" so "2 KB" beats "2.0 KB".
  return `${parseFloat(size.toFixed(1))} ${units[unitIndex]}`;
}
