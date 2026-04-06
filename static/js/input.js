// Address input helpers: parse a textarea/CSV blob into a list of addresses.

const SmartInput = {
  parseBulk(text) {
    if (!text) return [];
    const lines = text.split(/\r?\n/);
    const addresses = [];
    for (const raw of lines) {
      const line = raw.trim();
      if (!line) continue;
      // CSV: take a column named "address" or fallback to the first column.
      if (line.includes(',') && /address/i.test(lines[0] || '') && line === lines[0]) continue;
      if (line.includes(',') && /address/i.test(lines[0] || '')) {
        const headers = lines[0].split(',').map((h) => h.trim().toLowerCase());
        const idx = headers.indexOf('address');
        const cells = line.split(',').map((c) => c.trim());
        addresses.push(cells[idx] || cells[0]);
      } else {
        addresses.push(line);
      }
    }
    return addresses;
  },
};

window.SmartInput = SmartInput;
