// Drive the preview build in a real browser and assert the behaviour that only
// shows up at runtime: no console errors, the language switch, the quiz, the
// flashcard deck, and the archive's client-side badge.
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

  // What the build says it produced. Counts are read from here rather than
  // written down, so adding a daf does not turn these checks red.
  const manifest = await (await fetch(`${BASE}/dapim.json`)).json();
  const pages = Object.fromEntries(await Promise.all(manifest.map(async e =>
    [e.file, await (await fetch(`${BASE}/${e.file}`)).text()])));
  const today = new Date().toISOString().slice(0, 10);

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

    // ---------- flashcards ----------
    // The button under the glossary table is the entry point the reader meets
    // first, so open the deck through it rather than through the tab.
    await page.evaluate(() => [...document.querySelectorAll('.deck-cta button')]
      .find(b => b.offsetParent !== null).click());
    await page.waitForSelector('.flashcard');
    check('cards: the glossary button opens the deck',
      await page.evaluate(() => document.getElementById('cards').classList.contains('active')));
    check('cards: the tab followed',
      await page.evaluate(() =>
        document.querySelector('.tab[data-v="cards"]').getAttribute('aria-selected') === 'true'));

    const nCards = await page.evaluate(() => +document.querySelector('.dnum').innerText.split('/')[1]);
    const nTerms = await page.evaluate(() => {
      const t = [...document.querySelectorAll('.sheet[data-lang~="en"] table')]
        .find(x => /^term$/i.test(x.rows[0].cells[0].textContent.trim()));
      return t ? t.tBodies[0].rows.length : -1;
    });
    check('cards: deck has one card per glossary row', nCards === nTerms, `${nCards} vs ${nTerms}`);

    // A face centres with flex, so bare text beside an <em> would become its
    // own flex item and the sentence would lay out as columns. One element
    // child per face is what keeps the text a single running paragraph.
    const wrapped = await page.evaluate(() =>
      [...document.querySelectorAll('.flashcard .face')].every(f =>
        f.childNodes.length === 1 && f.firstChild.nodeType === 1));
    check('cards: each face wraps its content in one element', wrapped);

    // the back is hidden until the card is turned
    const hidden = await page.evaluate(() => {
      const b = document.querySelector('.face.back');
      return getComputedStyle(b).backfaceVisibility === 'hidden' &&
             !document.querySelector('.flashcard').classList.contains('flipped');
    });
    check('cards: the meaning starts hidden', hidden);

    await page.click('#show');
    check('cards: clicking flips the card',
      await page.evaluate(() => document.querySelector('.flashcard.flipped') !== null));
    check('cards: rating buttons appear once flipped',
      await page.evaluate(() => !!document.getElementById('knew') && !!document.getElementById('again')));

    await page.click('#knew');
    check('cards: rating advances and scores',
      await page.evaluate(() => document.querySelector('.dnum').innerText.includes('2 /') &&
                                document.querySelector('.dbar .pill').textContent === '1'));
    check('cards: the next card starts face down',
      await page.evaluate(() => document.querySelector('.flashcard.flipped') === null));

    // space flips, then rates — the documented keyboard path
    await page.evaluate(() => document.activeElement.blur());
    await page.keyboard.press('Space');
    check('cards: space flips',
      await page.evaluate(() => document.querySelector('.flashcard.flipped') !== null));
    await page.keyboard.press('1');
    check('cards: 1 flags for review and moves on',
      await page.evaluate(() => document.querySelector('.dnum').innerText.includes('3 /')));
    await page.keyboard.press('ArrowLeft');
    check('cards: back un-rates the card it returns to',
      await page.evaluate(() => document.querySelector('.dnum').innerText.includes('2 /') &&
                                document.querySelector('.dbar .pill').textContent === '1'));

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
    // hidden view, so textContent — innerText of a display:none element is ''
    const cEs = await page.evaluate(() => document.querySelector('.dnum').textContent);
    check('daf: deck restarted in Spanish', /^Tarjeta 1 \//.test(cEs), cEs);
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
  // Which daf that is changes as translations land, so find one rather than
  // naming one: a hardcoded page quietly stops testing anything the day it is
  // translated.
  {
    const untranslated = manifest.find(e => pages[e.file].includes('class="untranslated"'));
    if (!untranslated) {
      console.log('  skip  untranslated: every daf is translated');
    } else {
      const { page, errors } = await open(browser, `${BASE}/${untranslated.file}?lang=es`);
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
  }

  // ---------- archive ----------
  // Start from a known language: the daf page above left "es" in localStorage,
  // which is the site-wide-preference feature working, not a clean slate.
  {
    const { page, errors } = await open(browser, `${BASE}/archive.html?lang=en`);
    check('archive: no console errors', errors.length === 0, errors.join(' | ') || 'none');
    const rows = await page.evaluate(() => document.querySelectorAll('#list li').length);
    check('archive: lists every daf', rows === manifest.length, `${rows} of ${manifest.length}`);
    const badge = await page.evaluate(() => {
      const b = document.querySelector('li.today .badge');
      return b ? b.textContent : null;
    });
    check('archive: today badge painted', badge === 'Today' || badge === 'Most recent', badge);
    const future = await page.evaluate(() => document.querySelectorAll('li.future').length);
    const ahead = manifest.filter(e => e.iso > today).length;
    check('archive: future dapim dimmed', future === ahead, `${future} of ${ahead}`);
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
