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
    // One sheet on screen, and it is the one that covers this language — a
    // group may stand in for several ("en he" on a daf with no Hebrew sheet),
    // so the attribute is not the language, it is the set the block serves.
    const onlyFor = async l => {
      const v = await visible();
      return v.length === 1 && v[0].split(' ').includes(l);
    };
    check('daf: only the English sheet is visible', await onlyFor('en'), JSON.stringify(await visible()));

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

    // and back again — a card you can only turn once cannot be re-tested
    await page.click('#flip');
    check('cards: clicking the card again turns it back to the term',
      await page.evaluate(() => document.querySelector('.flashcard.flipped') === null &&
                                !!document.getElementById('show')));
    check('cards: the hidden face is hidden from screen readers too',
      await page.evaluate(() => {
        const f = document.querySelector('.face.front'), b = document.querySelector('.face.back');
        return f.getAttribute('aria-hidden') === 'false' && b.getAttribute('aria-hidden') === 'true';
      }));
    await page.click('#flip');

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
    check('daf: only the Spanish sheet is visible', await onlyFor('es'), JSON.stringify(await visible()));
    const h1es = await page.evaluate(() => document.querySelector('h1').innerText.trim());
    check('daf: Spanish title shown', h1es.includes('Julín 98'), h1es);
    const qEs = await page.evaluate(() => document.querySelector('.qnum').innerText);
    check('daf: quiz restarted in Spanish', /^pregunta 1 /i.test(qEs), qEs);
    // hidden view, so textContent — innerText of a display:none element is ''
    const cEs = await page.evaluate(() => document.querySelector('.dnum').textContent);
    check('daf: deck restarted in Spanish', /^Tarjeta 1 \//.test(cEs), cEs);
    // The toggle is a cycle through every language, not a pair: from Spanish
    // the next one offered is Hebrew, and from Hebrew it comes back to English.
    const offered = () => page.evaluate(() => {
      const s = [...document.querySelectorAll('#lang-btn span')].find(e => getComputedStyle(e).display !== 'none');
      return s ? s.textContent : null;
    });
    check('daf: toggle now offers Hebrew', (await offered() || '').includes('עברית'), await offered());

    // ---------- and on to Hebrew ----------
    await page.click('#lang-btn');
    await new Promise(r => setTimeout(r, 250));
    check('daf: html lang is he', await page.evaluate(() => document.documentElement.lang) === 'he');
    check('daf: the page turns right to left with it',
      await page.evaluate(() => document.documentElement.dir === 'rtl' &&
                                getComputedStyle(document.body).direction === 'rtl'));
    check('daf: the tabs are labelled in Hebrew',
      await page.evaluate(() => document.querySelector('.tab[data-v="learn"]').innerText.includes('לימוד')));
    check('daf: toggle comes back round to English', (await offered() || '').includes('English'), await offered());
    // Chullin 98 has no Hebrew sheet, so the English one stands in — and it has
    // to keep reading left to right inside a page that runs the other way.
    check('daf: the stand-in English sheet is still shown once', await onlyFor('he'), JSON.stringify(await visible()));
    check('daf: and it stays left to right', await page.evaluate(() => {
      const s = [...document.querySelectorAll('.sheet')].find(e => getComputedStyle(e).display !== 'none');
      return getComputedStyle(s).direction === 'ltr';
    }));
    // There is no Hebrew quiz or deck either, so both stand in whole — the
    // English ones, still reading left to right inside the right-to-left page.
    // Half of each translated would mean Hebrew buttons around English text.
    const fallback = await page.evaluate(() => ({
      q: document.querySelector('.qnum').innerText,
      qdir: getComputedStyle(document.getElementById('quizCard')).direction,
      c: document.querySelector('.dnum').textContent,
      cdir: getComputedStyle(document.getElementById('deckCard')).direction,
    }));
    check('daf: the stand-in quiz stays English and left to right',
      /^question 1 /i.test(fallback.q) && fallback.qdir === 'ltr', JSON.stringify(fallback));
    check('daf: the stand-in deck does too',
      /^Card 1 \//.test(fallback.c) && fallback.cdir === 'ltr', JSON.stringify(fallback));

    await page.click('#lang-btn');
    await new Promise(r => setTimeout(r, 250));
    check('daf: back to English restores left to right',
      await page.evaluate(() => document.documentElement.lang === 'en' &&
                                document.documentElement.dir === 'ltr'));

    // preference persists to another page
    await page.click('#lang-btn');
    await new Promise(r => setTimeout(r, 250));
    const { page: p2 } = await open(browser, `${BASE}/Chullin_99.html`);
    check('daf: language persists across pages',
      await p2.evaluate(() => document.documentElement.lang) === 'es');
    await p2.close();
    await page.close();
  }

  // ---------- an untranslated daf ----------
  // Which daf is missing which language changes as sheets land, so find one per
  // language rather than naming one: a hardcoded page quietly stops testing
  // anything the day it is translated.
  {
    const NOTE = { es: 'todavía no está traducida', he: 'עדיין לא תורגם' };
    for (const lang of ['es', 'he']) {
      const gap = manifest.find(e =>
        pages[e.file].includes(`<div class="untranslated" data-lang="${lang}">`));
      if (!gap) {
        console.log(`  skip  untranslated: every daf has a '${lang}' sheet`);
        continue;
      }
      const { page, errors } = await open(browser, `${BASE}/${gap.file}?lang=${lang}`);
      check(`untranslated ${lang}: no console errors`, errors.length === 0, errors.join(' | ') || 'none');
      check(`untranslated ${lang}: ?lang=${lang} honoured`,
        await page.evaluate(() => document.documentElement.lang) === lang);
      const shown = await page.evaluate(() =>
        [...document.querySelectorAll('.sheet, .untranslated')]
          .filter(e => getComputedStyle(e).display !== 'none')
          .map(e => e.className.trim()));
      check(`untranslated ${lang}: note + English body shown once`,
        shown.filter(c => c === 'sheet').length === 1 && shown.includes('untranslated'),
        JSON.stringify(shown));
      // A daf can be short of more than one language, so take the note that is
      // actually on screen rather than the first one in the markup.
      const note = await page.evaluate(() => [...document.querySelectorAll('.untranslated')]
        .find(e => getComputedStyle(e).display !== 'none').innerText);
      check(`untranslated ${lang}: the note is in that language`, note.includes(NOTE[lang]),
        note.slice(0, 40) + '…');
      await page.close();
    }
  }

  // ---------- the daf ----------
  // The tzurat hadaf layout is the whole point of this tab, and it is layout:
  // which column lands where can only be checked by measuring it. The margins
  // swap between the amudim, because Rashi belongs on the inner side and that
  // side changes with the leaf.
  {
    const withDaf = manifest.find(e => pages[e.file] && pages[e.file].includes('id="daf"'));
    if (!withDaf) {
      console.log('  skip  daf tab: no page has cached daf text');
    } else {
      const { page, errors } = await open(browser, `${BASE}/${withDaf.file}?lang=en`);
      await page.setViewport({ width: 1280, height: 900 });

      // The scans are a third party's bandwidth: nothing may be requested from
      // shas.org until the reader actually opens the tab.
      const scans = [];
      page.on('request', r => { if (/shas\.org/.test(r.url())) scans.push(r.url()); });
      check('daf tab: no scan is fetched on page load', scans.length === 0, `${scans.length}`);

      await page.evaluate(() => document.querySelector('.tab[data-v="daf"]').click());
      check('daf tab: no console errors', errors.length === 0, errors.join(' | ') || 'none');
      check('daf tab: opens', await page.evaluate(() =>
        document.getElementById('daf').classList.contains('active')));

      // ---------- the printed page ----------
      check('daf tab: the printed page is what opens', await page.evaluate(() =>
        document.getElementById('daf').classList.contains('mode-scan')));
      const frames = await page.evaluate(() =>
        document.querySelectorAll('.daf-scan figure.scan iframe').length);
      check('daf tab: one framed scan per amud', frames === 2, frames);
      // Chrome fetches an embedded PDF twice — once to navigate the frame, once
      // from the viewer plugin — so wait for both amudim rather than a count.
      for (let i = 0; i < 50 && new Set(scans).size < 2; i++) {
        await new Promise(r => setTimeout(r, 100));
      }
      const amudim = new Set(scans.map(u => (u.match(/amud=([ab])/) || [])[1]));
      check('daf tab: opening the tab is what loads them',
        amudim.has('a') && amudim.has('b') &&
        scans.every(u => /masechta=chullin&daf=\d+&amud=[ab]/.test(u)),
        [...new Set(scans)].map(u => u.split('?')[1]).join(' | ') || 'none requested');
      check('daf tab: every frame got its src', await page.evaluate(() =>
        [...document.querySelectorAll('.daf-scan iframe')]
          .every(f => f.src && !f.dataset.src)));
      check('daf tab: the text layout is put away with it', await page.evaluate(() =>
        getComputedStyle(document.querySelector('.daf-text')).display === 'none'));
      const credits = () => page.evaluate(() => [...document.querySelectorAll('.daf-credit')]
        .filter(e => getComputedStyle(e).display !== 'none')
        .map(e => e.innerText));
      const shown = await credits();
      check('daf tab: the scan carries its own credit, alone',
        shown.length === 1 && shown[0].includes('shas.org'),
        JSON.stringify(shown.map(c => c.slice(0, 30))));
      const pdfLink = await page.evaluate(() =>
        document.querySelector('figure.scan figcaption a').href);
      check('daf tab: a full-size link that does not need the frame',
        /shas\.org.*amud=a$/.test(pdfLink), pdfLink);

      // The page cannot answer a tap, so the passages under it do. One row per
      // Sefaria segment, in printed order, each opening onto its English.
      const rows = await page.evaluate(() =>
        document.querySelectorAll('.daf-scan .daf-lines .line').length);
      const segs = await page.evaluate(() =>
        document.querySelectorAll('.daf-text .seg').length);
      check('daf tab: a line under the page for every passage of it',
        rows === segs && rows > 0, `${rows} lines vs ${segs} passages`);
      check('daf tab: every line starts shut', await page.evaluate(() =>
        [...document.querySelectorAll('.daf-lines .line')]
          .every(l => l.classList.contains('collapsed'))));
      const enOf = () => page.evaluate(() => {
        const b = document.querySelector('.daf-lines .line .line-body');
        return { shown: getComputedStyle(b).display !== 'none', text: b.innerText.trim() };
      });
      check('daf tab: its English is not shown until asked', (await enOf()).shown === false);
      await page.evaluate(() =>
        document.querySelector('.daf-lines .line button.line-head').click());
      const opened = await enOf();
      check('daf tab: tapping a line opens its English',
        opened.shown && /[A-Za-z]{4,}/.test(opened.text), opened.text.slice(0, 48) + '…');
      // The Hebrew is written once: the head holds it, clamped when shut.
      check('daf tab: the Hebrew is not duplicated to do it', await page.evaluate(() => {
        const l = document.querySelector('.daf-lines .line');
        return l.querySelectorAll('[lang="he"]').length === 1 &&
          getComputedStyle(l.querySelector('.line-he')).whiteSpace !== 'nowrap';
      }));

      // ---------- and the text alongside it ----------
      await page.evaluate(() => document.querySelector('.chip[data-mode="text"]').click());
      check('daf tab: the text mode switches over', await page.evaluate(() => {
        const d = document.getElementById('daf');
        return d.classList.contains('mode-text') &&
          getComputedStyle(document.querySelector('.daf-scan')).display === 'none' &&
          getComputedStyle(document.querySelector('.daf-text')).display !== 'none';
      }));
      const textCredit = await credits();
      check('daf tab: and brings its own credit with it',
        textCredit.length === 1 && textCredit[0].includes('Sefaria'),
        JSON.stringify(textCredit.map(c => c.slice(0, 30))));

      // Neither disclaimer may go on claiming this text was AI-written.
      const notice = await page.evaluate(() => [...document.querySelectorAll('.disclaimer')]
        .filter(e => getComputedStyle(e).display !== 'none')
        .map(e => e.className.trim()));
      check('daf tab: the AI notices give way to the source notice',
        notice.length === 1 && notice[0].includes('source'), JSON.stringify(notice));
      check('daf tab: the Davidson licence is credited', await page.evaluate(() =>
        /CC BY-NC/.test(document.querySelector('.daf-credit.for-text').innerText)));

      // Left-to-right screen order per amud. Rashi sits on the inner margin:
      // left of the text on amud alef (a recto), right of it on amud bet.
      const order = amud => page.evaluate(i => {
        const seg = [...document.querySelectorAll('.amud')][i].querySelector('.seg');
        return [...seg.querySelectorAll('.col')]
          .filter(c => getComputedStyle(c).display !== 'none')
          .map(c => [c.getBoundingClientRect().left, c.className.split(' ')[1]])
          .sort((a, b) => a[0] - b[0]).map(p => p[1]);
      }, amud);
      check('daf tab: amud alef puts Rashi on the inner (left) margin',
        JSON.stringify(await order(0)) === '["rashi","gemara","tosafot"]', JSON.stringify(await order(0)));
      check('daf tab: amud bet mirrors it',
        JSON.stringify(await order(1)) === '["tosafot","gemara","rashi"]', JSON.stringify(await order(1)));
      check('daf tab: the Gemara column is the widest', await page.evaluate(() => {
        const w = c => document.querySelector('.seg .col.' + c).getBoundingClientRect().width;
        return w('gemara') > w('rashi') && w('gemara') > w('tosafot');
      }));

      // The translation is off until asked for, and the chips are remembered.
      const enShown = () => page.evaluate(() =>
        getComputedStyle(document.querySelector('.g-en')).display !== 'none');
      check('daf tab: the translation starts hidden', (await enShown()) === false);
      await page.evaluate(() => document.querySelector('.chip[data-daf="en"]').click());
      check('daf tab: the English chip reveals it', (await enShown()) === true);

      const rashiWidth = () => page.evaluate(() =>
        document.querySelector('.seg .col.gemara').getBoundingClientRect().width);
      const wide = await rashiWidth();
      await page.evaluate(() => document.querySelector('.chip[data-daf="rashi"]').click());
      check('daf tab: dropping Rashi hands its width to the Gemara',
        (await rashiWidth()) > wide, `${Math.round(wide)} → ${Math.round(await rashiWidth())}`);

      const { page: p3 } = await open(browser, `${BASE}/${withDaf.file}?lang=en`);
      await p3.evaluate(() => document.querySelector('.tab[data-v="daf"]').click());
      check('daf tab: the chips are remembered', await p3.evaluate(() => {
        const d = document.getElementById('daf');
        return d.classList.contains('hide-rashi') && d.classList.contains('show-en');
      }));
      await p3.close();
      await page.screenshot({ path: 'shot-daf-tzurat.png', fullPage: false });

      // On a phone the columns stack and the commentary folds away, but only
      // because the script folded it — the markup itself is never hidden.
      await page.setViewport({ width: 420, height: 900 });
      await page.evaluate(() => document.querySelector('.chip[data-daf="rashi"]').click());
      await new Promise(r => setTimeout(r, 150));
      // Stacked, and stacked in reading order: a margin printed above the
      // passage it comments on would be no use to anyone.
      check('daf tab: the columns stack under the Gemara on a phone', await page.evaluate(() => {
        const seg = [...document.querySelectorAll('.seg')]
          .find(s => s.querySelectorAll('.col:not(.empty)').length === 3);
        const box = c => seg.querySelector('.col.' + c).getBoundingClientRect();
        const g = box('gemara');
        return ['rashi', 'tosafot'].every(c =>
          Math.abs(box(c).left - g.left) < 2 && box(c).top > g.top);
      }));
      const body = () => page.evaluate(() =>
        getComputedStyle(document.querySelector('.col.rashi .col-body')).display !== 'none');
      check('daf tab: the commentary starts folded there', (await body()) === false);
      await page.evaluate(() => document.querySelector('.col.rashi .col-head').click());
      check('daf tab: its heading unfolds it', (await body()) === true);
      await page.close();
    }
  }

  // ---------- read aloud ----------
  // Headless Chrome ships no voices, so the real synthesiser would refuse every
  // utterance and the queue would never move. A stub stands in: it reports the
  // voices this check wants to exist, records what it was asked to say, and
  // ends each utterance on the next tick. That is enough to test the things
  // that can only go wrong at runtime — where a section stops, which voice a
  // Hebrew quotation gets, and what happens when there is no Hebrew voice.
  // Voices are given as 'en-US' for a plain local one, or ['Zarvox', 'en-US']
  // to name it, or ['Google US English', 'en-US', false] to make it a network
  // voice — which is the one kind that gets cut off, so it is chunked short.
  async function stubbedSpeech(url, voiceLangs) {
    const page = await browser.newPage();
    const errors = [];
    page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
    page.on('pageerror', e => errors.push(String(e)));
    await page.evaluateOnNewDocument(langs => {
      const said = [];
      window.__said = said;
      window.__cancels = 0;
      // speechSynthesis is a prototype getter — plain assignment is ignored.
      Object.defineProperty(window, 'SpeechSynthesisUtterance', {
        configurable: true,
        value: function (text) { this.text = text; }
      });
      Object.defineProperty(window, 'speechSynthesis', {
        configurable: true,
        value: {
          getVoices: () => langs.map(l => Array.isArray(l)
            ? { name: l[0], lang: l[1], default: false, localService: l[2] !== false }
            : { name: 'stub-' + l, lang: l, default: false, localService: true }),
          addEventListener() {},
          speak(u) {
            said.push({ text: u.text, lang: u.lang, voice: u.voice && u.voice.name });
            setTimeout(() => u.onstart && u.onstart(), 0);
            setTimeout(() => u.onend && u.onend(), 4);
          },
          cancel() { window.__cancels++; }
        }
      });
    }, voiceLangs);
    await page.goto(url, { waitUntil: 'networkidle0' });
    return { page, errors };
  }

  // Let the stub work through the queue, then let it settle.
  async function settled(page) {
    let n = -1;
    for (let i = 0; i < 100; i++) {
      const now = await page.evaluate(() => window.__said.length);
      if (now === n) return now;
      n = now;
      await new Promise(r => setTimeout(r, 60));
    }
    return n;
  }

  {
    const { page, errors } = await stubbedSpeech(`${BASE}/Chullin_98.html?lang=en`, ['en-US', 'es-ES', 'he-IL']);
    check('speak: no console errors', errors.length === 0, errors.join(' | ') || 'none');

    const counts = await page.evaluate(() => {
      const heads = document.querySelectorAll('.sheet h2, .sheet h3');
      return [heads.length, [...heads].filter(h => h.querySelector(':scope > button.speak')).length];
    });
    check('speak: every heading in the sheet has a button', counts[0] > 0 && counts[0] === counts[1],
      `${counts[1]} of ${counts[0]}`);

    const heads = await page.evaluate(() =>
      [...document.querySelectorAll('.sheet[data-lang~="en"] h2')]
        .map(h => h.textContent.replace(/[🔊⏹]/g, '').trim()));
    await page.evaluate(() => document.querySelector('.sheet[data-lang~="en"] h2 button.speak').click());

    check('speak: the button shows it is playing',
      await page.evaluate(() => {
        const b = document.querySelector('.sheet[data-lang~="en"] h2 button.speak');
        return b.classList.contains('on') && b.getAttribute('aria-pressed') === 'true';
      }));
    check('speak: the block being spoken is marked',
      await page.evaluate(() => document.querySelectorAll('.speaking').length) === 1);

    await settled(page);
    const said = await page.evaluate(() => window.__said);
    check('speak: starts with the heading, without the button glyph',
      said.length > 3 && said[0].text === heads[0], JSON.stringify(said[0] && said[0].text));
    check('speak: stops at the next section',
      !said.some(s => s.text.includes(heads[1].slice(0, 20))), heads[1]);

    const he = said.filter(s => /[֐-׿]/.test(s.text));
    check('speak: Hebrew is spoken by a Hebrew voice',
      he.length > 0 && he.every(s => s.lang === 'he-IL' && s.voice === 'stub-he-IL'),
      `${he.length} Hebrew utterance(s)`);
    check('speak: the rest is spoken by the sheet\'s own voice',
      said.filter(s => !/[֐-׿]/.test(s.text)).every(s => s.lang === 'en-US'));
    // Every utterance boundary is a pause and a reset of the voice's
    // intonation, which is what made this sound like a robot reading a list.
    // A local voice can take a whole paragraph, so it gets one.
    const longest = Math.max(...said.map(s => s.text.length));
    check('speak: a local voice is given whole paragraphs',
      longest > 300 && longest <= 1000, longest);
    check('speak: nothing is said that is only punctuation',
      said.every(s => /[0-9A-Za-zÀ-ɏ֐-׿]/.test(s.text)),
      JSON.stringify(said.filter(s => !/[0-9A-Za-zÀ-ɏ֐-׿]/.test(s.text)).map(s => s.text)));
    check('speak: a quotation is not chopped around its quote marks',
      said.some(s => /^[֐-׿]/.test(s.text) && s.text.split(/\s+/).length > 2),
      said.filter(s => /^[֐-׿]/.test(s.text)).length + ' Hebrew utterance(s)');

    // finishing releases the button, so the section can be replayed
    check('speak: the button resets when the section ends',
      await page.evaluate(() => !document.querySelector('button.speak.on') &&
                                !document.querySelector('.speaking')));

    // Spanish: the sheet's language decides the voice, not the reader's chrome
    await page.click('#lang-btn');
    await page.evaluate(() => { window.__said.length = 0; });
    await page.evaluate(() => document.querySelector('.sheet[data-lang~="es"] h2 button.speak').click());
    await new Promise(r => setTimeout(r, 120));
    const es = await page.evaluate(() => window.__said);
    check('speak: the Spanish sheet is read in Spanish',
      es.length > 0 && es.filter(s => !/[֐-׿]/.test(s.text)).every(s => s.lang === 'es-ES'),
      es.length ? es[0].lang : 'nothing said');
    const label = await page.evaluate(() =>
      document.querySelector('.sheet[data-lang~="es"] h2 button.speak').title);
    check('speak: the button label follows the reader\'s language', /voz alta|lectura/.test(label), label);

    // Escape stops it wherever it is
    await page.keyboard.press('Escape');
    check('speak: Escape stops the reading',
      await page.evaluate(() => window.__cancels > 0 && !document.querySelector('button.speak.on')));
    await page.close();
  }

  // The voice is chosen, not accepted: macOS lists novelty voices among the
  // real ones and offers "Eddy" for Spanish before Mónica.
  {
    const { page } = await stubbedSpeech(`${BASE}/Chullin_98.html?lang=en`, [
      ['Albert', 'en-US'], ['Zarvox', 'en-US'], ['Samantha', 'en-US'],
      ['Samantha (Enhanced)', 'en-US'],
      ['Eddy (Spanish (Spain))', 'es-ES'], ['Mónica', 'es-ES']
    ]);
    await page.evaluate(() => document.querySelector('.sheet[data-lang~="en"] h2 button.speak').click());
    await new Promise(r => setTimeout(r, 150));
    const en = await page.evaluate(() => window.__said[0].voice);
    check('speak: picks a real voice over a novelty one, best build first',
      en === 'Samantha (Enhanced)', en);

    // the stub races through a section in milliseconds, so there is nothing
    // left playing to stop by now
    await page.evaluate(() => { window.__said.length = 0; });
    await page.click('#lang-btn');
    await page.evaluate(() => document.querySelector('.sheet[data-lang~="es"] h2 button.speak').click());
    await new Promise(r => setTimeout(r, 150));
    const es = await page.evaluate(() => window.__said.length && window.__said[0].voice);
    check('speak: Spanish gets Mónica, not Eddy', es === 'Mónica', es);
    await page.close();
  }

  // A network voice is the one that gets cut off mid-word, so it — and only it
  // — is fed short utterances.
  {
    const { page } = await stubbedSpeech(`${BASE}/Chullin_98.html?lang=en`,
      [['Google US English', 'en-US', false], ['stub-he-IL', 'he-IL', false]]);
    await page.evaluate(() => document.querySelector('.sheet[data-lang~="en"] h2 button.speak').click());
    await settled(page);
    const longest = await page.evaluate(() =>
      Math.max(...window.__said.map(s => s.text.length)));
    check('speak: a network voice is fed utterances it will not cut off',
      longest > 0 && longest <= 260, longest);
    await page.close();
  }

  // With no Hebrew voice installed, the quotations are skipped rather than
  // handed to a voice that would spell them out letter by letter.
  {
    const { page } = await stubbedSpeech(`${BASE}/Chullin_98.html?lang=en`, ['en-US']);
    await page.evaluate(() => document.querySelector('.sheet[data-lang~="en"] h2 button.speak').click());
    await settled(page);
    const said = await page.evaluate(() => window.__said);
    check('speak: Hebrew is skipped when no Hebrew voice exists',
      said.length > 3 && !said.some(s => /[֐-׿]/.test(s.text)),
      `${said.length} utterance(s)`);
    await page.close();
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

    await page.click('#lang-btn');
    await new Promise(r => setTimeout(r, 250));
    const zmanHe = await page.evaluate(() => document.getElementById('zman').textContent);
    check('archive: sunset line switches to Hebrew', zmanHe.includes('שקיעה'), zmanHe);
    const badgeHe = await page.evaluate(() => document.querySelector('li.today .badge').textContent);
    check('archive: badge switches to Hebrew', badgeHe === 'היום' || badgeHe === 'האחרון', badgeHe);
    check('archive: the list turns right to left',
      await page.evaluate(() => document.documentElement.dir === 'rtl'));
    await page.screenshot({ path: 'shot-archive-he.png', fullPage: true });
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
