const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const [,, input, output, w, h, transparent] = process.argv;
  const svg = fs.readFileSync(input, 'utf8');
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: +w, height: +h }, deviceScaleFactor: 1 });
  await p.setContent(`<html><body style="margin:0;background:transparent">${svg}</body></html>`);
  await p.evaluate(() => document.fonts.ready);
  await p.screenshot({ path: output, omitBackground: transparent === '1', clip: { x: 0, y: 0, width: +w, height: +h } });
  await b.close();
})();
