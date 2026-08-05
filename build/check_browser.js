// Drive the preview build in a real browser and assert the behaviour that only
// shows up at runtime: no console errors, the language switch, the quiz, and
// the archive's client-side badge.
const puppeteer = require('puppeteer-core');

const BASE = 'http://localhost:8891';
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

let failures = 0;
function check(name, cond, detail) {
  const ok = !!cond;
  if (!ok) failures++;
  console.log(`${ok ? '  ok  ' : ' FAIL '} ${name}${detail !== undefined ? '  → ' + detail : ''}`);
}

async function open(browser, url) {
  const page = await browser.newPage();
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push(String(e)));
  await page.goto(url, { waitUntil: 'networkidle0' });
  return { page, errors };
}

(async () => {
  const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new' });

  // ---------- a bilingual daf ----------
  {
    const { page, errors } = await open(browser, `${BASE}/Chullin_98.html`);
    check('daf: no console errors', errors.length === 0, errors.join(' | ') || 'none');
    check('daf: html lang defaults to en', await page.evaluate(() => document.documentElement.lang) === 'en');

    const visible = () => page.evaluate(() =>
      [...document.querySelectorAll('.sheet')]
        .filter(e => getComputedStyle(e).display !== 'none')
        .map(e => e.getAttribute('data-lang')));
    check('daf: only the English sheet is visible', JSON.stringify(await visible()) === '["en"]', JSON.stringify(await visible()));

    const h1 = await page.evaluate(() => document.querySelector('h1').innerText.trim());
    check('daf: English title shown', h1.includes('Chullin 98'), h1);
    check('daf: Hebrew is marked rtl',
      await page.evaluate(() => {
        const s = document.querySelector('h1 span[lang="he"]');
        return s && getComputedStyle(s).direction === 'rtl';
      }));

    // quiz
    await page.click('.tab[data-v="quiz"]');
    await page.waitForSelector('.opt');
    const nOpts = await page.evaluate(() => document.querySelectorAll('.opt').length);
    check('daf: quiz renders 4 options', nOpts === 4, nOpts);
    // .qnum is text-transform:uppercase, so compare case-insensitively
    const qEn = await page.evaluate(() => document.querySelector('.qnum').innerText);
    check('daf: quiz chrome in English', /^question/i.test(qEn), qEn);

    // answering marks exactly one correct
    await page.evaluate(() => document.querySelectorAll('.opt')[0].click());
    const marked = await page.evaluate(() => document.querySelectorAll('.opt.correct').length);
    check('daf: answering marks the correct option', marked === 1, marked);
    check('daf: explanation shown', await page.evaluate(() => document.querySelector('.why.show') !== null));

    // ---------- switch to Spanish ----------
    await page.click('#lang-btn');
    await new Promise(r => setTimeout(r, 250));
    check('daf: html lang is es', await page.evaluate(() => document.documentElement.lang) === 'es');
    check('daf: only the Spanish sheet is visible', JSON.stringify(await visible()) === '["es"]', JSON.stringify(await visible()));
    const h1es = await page.evaluate(() => document.querySelector('h1').innerText.trim());
    check('daf: Spanish title shown', h1es.includes('Julín 98'), h1es);
    const qEs = await page.evaluate(() => document.querySelector('.qnum').innerText);
    check('daf: quiz restarted in Spanish', /^pregunta 1 /i.test(qEs), qEs);
    check('daf: toggle now offers English',
      await page.evaluate(() => {
        const s = [...document.querySelectorAll('#lang-btn span')].find(e => getComputedStyle(e).display !== 'none');
        return s && s.textContent.includes('English');
      }));

    // preference persists to another page
    const { page: p2 } = await open(browser, `${BASE}/Chullin_99.html`);
    check('daf: language persists across pages',
      await p2.evaluate(() => document.documentElement.lang) === 'es');
    await p2.close();
    await page.close();
  }

  // ---------- an untranslated daf ----------
  {
    const { page, errors } = await open(browser, `${BASE}/Chullin_100.html?lang=es`);
    check('untranslated: no console errors', errors.length === 0, errors.join(' | ') || 'none');
    check('untranslated: ?lang=es honoured', await page.evaluate(() => document.documentElement.lang) === 'es');
    const shown = await page.evaluate(() =>
      [...document.querySelectorAll('.sheet, .untranslated')]
        .filter(e => getComputedStyle(e).display !== 'none')
        .map(e => e.className.trim()));
    check('untranslated: note + English body shown once',
      shown.filter(c => c === 'sheet').length === 1 && shown.includes('untranslated'),
      JSON.stringify(shown));
    const note = await page.evaluate(() => document.querySelector('.untranslated').innerText);
    check('untranslated: note is in Spanish', note.includes('todavía no está traducida'), note.slice(0, 40) + '…');
    await page.close();
  }

  // ---------- archive ----------
  // Start from a known language: the daf page above left "es" in localStorage,
  // which is the site-wide-preference feature working, not a clean slate.
  {
    const { page, errors } = await open(browser, `${BASE}/archive.html?lang=en`);
    check('archive: no console errors', errors.length === 0, errors.join(' | ') || 'none');
    const rows = await page.evaluate(() => document.querySelectorAll('#list li').length);
    check('archive: lists every daf', rows === 5, rows);
    const badge = await page.evaluate(() => {
      const b = document.querySelector('li.today .badge');
      return b ? b.textContent : null;
    });
    check('archive: today badge painted', badge === 'Today' || badge === 'Most recent', badge);
    const future = await page.evaluate(() => document.querySelectorAll('li.future').length);
    check('archive: future dapim dimmed', future === 3, future);
    const zman = await page.evaluate(() => document.getElementById('zman').textContent);
    check('archive: sunset line rendered', /sunset is \d/.test(zman), zman);

    await page.click('#lang-btn');
    await new Promise(r => setTimeout(r, 250));
    const zmanEs = await page.evaluate(() => document.getElementById('zman').textContent);
    check('archive: sunset line switches to Spanish', zmanEs.includes('atardecer'), zmanEs);
    const badgeEs = await page.evaluate(() => document.querySelector('li.today .badge').textContent);
    check('archive: badge switches to Spanish', badgeEs === 'Hoy' || badgeEs === 'Más reciente', badgeEs);
    await page.screenshot({ path: 'shot-archive-es.png', fullPage: true });
    await page.close();
  }

  // ---------- index router ----------
  {
    const { page, errors } = await open(browser, `${BASE}/index.html`);
    check('index: no console errors', errors.length === 0, errors.join(' | ') || 'none');
    check('index: stays on the current daf (no redirect loop)',
      page.url().endsWith('/index.html') || page.url().includes('Chullin_'), page.url());
    await page.screenshot({ path: 'shot-index-en.png', fullPage: false });
    await page.close();
  }

  // ---------- dark mode ----------
  {
    const page = await browser.newPage();
    await page.emulateMediaFeatures([{ name: 'prefers-color-scheme', value: 'dark' }]);
    await page.goto(`${BASE}/Chullin_98.html`, { waitUntil: 'networkidle0' });
    const bg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
    check('dark mode: dark background applied', /rgb\((\d+), (\d+), (\d+)\)/.test(bg) &&
      bg.match(/\d+/g).slice(0, 3).every(v => +v < 60), bg);
    await page.screenshot({ path: 'shot-daf-dark.png', fullPage: false });
    await page.close();
  }

  await browser.close();
  console.log(failures === 0 ? '\nALL CHECKS PASSED' : `\n${failures} CHECK(S) FAILED`);
  process.exit(failures === 0 ? 0 : 1);
})().catch(e => { console.error(e); process.exit(2); });
