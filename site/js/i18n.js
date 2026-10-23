/* English lives in the HTML. This file holds the Greek text and the language toggle.
   Elements opt in with data-i18n (text), data-i18n-html (markup) or
   data-i18n-attr="attribute:key". The tool's own output (terminal, report card) stays English. */
(function () {
  'use strict';

  var STORE = 'apodix-lang';

  var EL = {
    'lang.group': 'Γλώσσα',
    'nav.how': 'Πώς λειτουργεί',
    'nav.try': 'Δοκίμασέ το',
    'nav.fits': 'Πού ταιριάζει',
    'nav.limits': 'Όρια',

    'ui.copy': 'Αντιγραφή',
    'ui.copied': 'Αντιγράφηκε',
    'ui.star': 'Star στο GitHub',

    'hero.note': 'Λειτουργικό πρωτότυπο. Δεν έχει δημοσιευτεί ακόμα.',
    'hero.h1': 'Το «τελείωσα» δεν είναι απόδειξη.',
    'hero.lead': 'Το Apodix ελέγχει τη δουλειά που λέει ότι ολοκλήρωσε ο AI agent σου. Για κάθε κριτήριο αποδοχής δείχνει τι έχει αποδειχθεί, τι δεν έχει αποδειχθεί και τι λείπει.',
    'hero.copyAria': 'Αντιγραφή εντολής',
    'hero.see': 'Δες πώς λειτουργεί',
    'hero.small': 'Τρέξε το σε ένα project Python που χρησιμοποιεί pytest. Δεν είναι ακόμα στο PyPI, οπότε <a href="#try">εγκατέστησέ το από το repo</a>.',
    'hero.ledgerAria': 'Παράδειγμα αναφοράς: ένα από τρία κριτήρια αποδοχής έχει αποδειχθεί, ένα δεν έχει αποδειχθεί και ένα λείπει.',

    'gap.title': 'Τα πράσινα tests μπορεί να χάνουν το νόημα.',
    'gap.lead': 'Ένας agent μπορεί να περάσει όλα τα tests που έγραψε και να παραλείψει τα μισά από όσα ζήτησες. Τα tests που περνούν δεν λένε τίποτα για απαιτήσεις που κανείς δεν δοκίμασε.',
    'gap.sayH': 'Τι λέει ο agent',
    'gap.bubble': 'Και οι τρεις απαιτήσεις έχουν υλοποιηθεί. <b>Και τα 12 tests περνούν.</b>',
    'gap.testsLabel': '12 tests, 12 πράσινα',
    'gap.findH': 'Τι βρίσκει το Apodix',
    'gap.found': '1 από 3 <small>κριτήρια αποδεδειγμένα</small>',
    'gap.foundSub': 'Τα 12 tests καλύπτουν καλά μία απαίτηση. Οι άλλες δύο δεν έχουν tests ή δεν μπορούν να ελεγχθούν όπως είναι γραμμένες.',
    'gap.li1': '<span class="dot p"></span>Έκπτωση πάνω από €100: αποδεδειγμένο',
    'gap.li2': '<span class="dot m"></span>Είδη χωρίς έκπτωση: λείπει',
    'gap.li3': '<span class="dot u"></span>Κενός κωδικός προσφοράς: μη αποδεδειγμένο',

    'ver.title': 'Τρεις ετυμηγορίες. Κανένα «ίσως».',
    'ver.lead': 'Κάθε κριτήριο καταλήγει σε μία ακριβώς κατάσταση, ώστε ο reviewer να ξέρει πού να κοιτάξει. Οι ετικέτες Proven, Unproven και Missing είναι αυτές που τυπώνει το εργαλείο.',
    'ver.a.h': 'Ένα test το φυλάει',
    'ver.a.p': 'Το test περνάει σήμερα και αποτυγχάνει όταν το Apodix χαλάει επίτηδες τον αντίστοιχο κώδικα.',
    'ver.a.ex': 'Άλλαξε το 10% σε 5% και το test κοκκινίζει.',
    'ver.b.h': 'Υπάρχει test, αλλά δεν φυλάει τίποτα',
    'ver.b.p': 'Ο κώδικας μπορεί να είναι σωστός, αλλά κανείς δεν θα το πρόσεχε αν ήταν λάθος.',
    'ver.b.ex': 'Σβήσε τον έλεγχο και το test συνεχίζει να περνάει.',
    'ver.c.h': 'Τίποτα δεν το καλύπτει',
    'ver.c.p': 'Κανένας κώδικας ή test δεν αφορά αυτή την απαίτηση. Ο agent την ξέχασε ή δεν την κατάλαβε ποτέ.',
    'ver.c.ex': 'Οι λέξεις «no discount» δεν εμφανίζονται πουθενά στο diff.',

    'how.title': 'Πώς ελέγχει το Apodix τη δουλειά',
    'how.lead': 'Το μοντέλο δεν βαθμολογεί ποτέ τον εαυτό του: το αποτέλεσμα προκύπτει από την εκτέλεση κώδικα.',
    'how.s1h': 'Διαβάζει τα κριτήρια',
    'how.s1p': 'Διαβάζει τα κριτήρια αποδοχής από ένα αρχείο markdown και κρατά το ID του καθενός. Τα GitHub issues έρχονται σύντομα.',
    'how.s2h': 'Βρίσκει τις αποδείξεις',
    'how.s2p': 'Συνδέει κάθε κριτήριο με τα tests που έχουν σημανθεί να το καλύπτουν και καταγράφει ποιες γραμμές κώδικα εκτέλεσαν.',
    'how.s3h': 'Το χαλάει επίτηδες',
    'how.s3p': 'Αλλάζει τον αντίστοιχο κώδικα σε ένα προσωρινό αντίγραφο και ξανατρέχει τα tests. Ένα test που πραγματικά φυλάει κάτι κοκκινίζει.',
    'how.s4h': 'Βάζει τη σφραγίδα',
    'how.s4p': 'Επιστρέφει Proven, Unproven ή Missing για κάθε κριτήριο και στέλνει τα κενά πίσω στον agent.',
    'how.termAria': 'Έξοδος του terminal για την εντολή apodix verify, που χτίζεται βήμα προς βήμα',

    'try.title': 'Δοκίμασε το πρωτότυπο',
    'try.lead': 'Εγκατέστησέ το από το repo και τρέξε το στο demo του καλαθιού. Ένας agent ισχυρίστηκε ότι και οι τρεις απαιτήσεις ολοκληρώθηκαν. Το Apodix βρίσκει μία.',
    'try.small': 'Χρειάζεται Python 3.10 ή νεότερη. Το README έχει τις εντολές για Windows. Μετά τρέξ’ το στο <code>demo/cart_fixed</code> για να δεις 3 από 3 αποδεδειγμένα.',
    'try.os': 'macOS και Linux',
    'try.outAria': 'Αναμενόμενο αποτέλεσμα',

    'fits.title': 'Δουλεύει εκεί που ήδη δουλεύεις.',
    'fits.lead': 'Σήμερα υπάρχει μόνο η γραμμή εντολών. Τα άλλα δύο έρχονται και θα μοιράζονται την ίδια μηχανή και τις ίδιες ετυμηγορίες.',
    'fits.a.p': 'Σχεδιάζεται. Το Claude καλεί το <code>verify_done</code> πριν πει ότι τελείωσε και διορθώνει μόνο του ό,τι λείπει.',
    'fits.b.p': 'Σχεδιάζεται. Κάθε pull request παίρνει έναν πίνακα αποδείξεων ως σχόλιο. Οι reviewers διαβάζουν ετυμηγορίες αντί να σκρολάρουν σε ένα diff.',
    'fits.c.h': 'Γραμμή εντολών',
    'fits.c.p': 'Διαθέσιμο τώρα. Τρέξε το τοπικά ή σε οποιοδήποτε CI. Η έξοδος είναι κείμενο, Markdown ή JSON, και ο κωδικός εξόδου είναι 1 μέχρι να αποδειχθούν όλα τα κριτήρια.',

    'lim.title': 'Τι δεν μπορεί να αποδείξει ακόμα.',
    'lim.lead': 'Ένα εργαλείο απόδειξης που υπερβάλλει είναι χειρότερο από κανένα. Να πού σταματά η πρώτη έκδοση.',
    'lim.l1': '<b>Γλώσσες</b><span>Πρώτα Python με pytest. Η TypeScript έρχεται μετά.</span>',
    'lim.l2': '<b>Είδη κανόνων</b><span>Ό,τι μπορεί να ελέγξει ένα unit test. Η οπτική διάταξη και ο χρονισμός μένουν εκτός προς το παρόν.</span>',
    'lim.l3': '<b>Εξωτερικές υπηρεσίες</b><span>Πληρωμές, email και άλλα APIs χρειάζονται mocks. Το Apodix θα το πει όταν ένας κανόνας εξαρτάται από κάποιο.</span>',
    'lim.l4': '<b>Ασαφή κριτήρια</b><span>Το «κάν’ το να αισθάνεται γρήγορο» δεν αποδεικνύεται. Το Apodix το επισημαίνει και ζητά κάτι μετρήσιμο.</span>',

    'cta.title': 'Βοήθησε να χτιστεί το πρώτο εργαλείο απόδειξης για AI agents.',
    'cta.p': 'Το Apodix είναι ανοιχτού κώδικα από την πρώτη μέρα. Δοκίμασε την πρώτη έκδοση, ανέφερε τις περιπτώσεις που αποτυγχάνει ή πάρε ένα good first issue.',
    'cta.issues': 'Good first issues',

    'foot.ety': '<span class="gr" lang="grc">ἀπόδειξις</span>\n      <i>apódeixis</i>, «επίδειξη, ανάδειξη», δηλαδή απόδειξη. Ο Ευκλείδης έκλεινε τις αποδείξεις του με <span lang="grc">ὅπερ ἔδει δεῖξαι</span>, «όπερ έδει δείξαι», και το τετράγωνο ∎ σημαδεύει ακόμα το τέλος μιας απόδειξης.',
    'foot.credit': 'Σχεδίαση και ανάπτυξη: <a class="credit" href="https://nikoslefakis.vercel.app" rel="author">Nikos Lefakis</a>',
    'foot.license': 'Άδεια MIT. Φτιαγμένο ανοιχτά.'
  };

  var META = {
    el: {
      title: 'Apodix: απόδειξη ότι ο AI agent σου ολοκλήρωσε πραγματικά τη δουλειά',
      description: 'Το Apodix ελέγχει κάθε κριτήριο αποδοχής που ο AI agent σου λέει ότι ολοκλήρωσε και δείχνει τι είναι αποδεδειγμένο, μη αποδεδειγμένο ή λείπει.',
      ogDescription: 'Ελέγχει κάθε κριτήριο αποδοχής που ο AI coding agent σου λέει ότι ολοκλήρωσε.'
    }
  };

  var UI_EN = { 'ui.copy': 'Copy', 'ui.copied': 'Copied' };

  var meta = {
    description: document.querySelector('meta[name="description"]'),
    ogTitle: document.querySelector('meta[property="og:title"]'),
    ogDescription: document.querySelector('meta[property="og:description"]')
  };
  var original = {
    title: document.title,
    description: meta.description && meta.description.content,
    ogDescription: meta.ogDescription && meta.ogDescription.content
  };

  var current = 'en';

  function read() { try { return localStorage.getItem(STORE); } catch (e) { return null; } }
  function write(value) { try { localStorage.setItem(STORE, value); } catch (e) { /* storage blocked: choice lasts for this visit only */ } }

  function preferred() {
    var fromUrl = new URLSearchParams(window.location.search).get('lang');
    if (fromUrl === 'el' || fromUrl === 'en') return fromUrl;
    var saved = read();
    if (saved === 'el' || saved === 'en') return saved;
    var langs = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language || 'en'];
    return /^el\b/i.test(langs[0]) ? 'el' : 'en';
  }

  function t(key) {
    return current === 'el' && EL[key] !== undefined ? EL[key] : UI_EN[key] || EL[key] || key;
  }

  function each(selector, fn) { [].forEach.call(document.querySelectorAll(selector), fn); }

  function apply(lang) {
    current = lang;
    document.documentElement.lang = lang;

    each('[data-i18n]', function (el) {
      if (el.dataset.en === undefined) el.dataset.en = el.textContent;
      el.textContent = lang === 'el' && EL[el.dataset.i18n] !== undefined ? EL[el.dataset.i18n] : el.dataset.en;
    });

    each('[data-i18n-html]', function (el) {
      if (el.dataset.enHtml === undefined) el.dataset.enHtml = el.innerHTML;
      el.innerHTML = lang === 'el' && EL[el.dataset.i18nHtml] !== undefined ? EL[el.dataset.i18nHtml] : el.dataset.enHtml;
    });

    each('[data-i18n-attr]', function (el) {
      el.dataset.i18nAttr.split(';').forEach(function (pair) {
        var parts = pair.split(':'), attr = parts[0].trim(), key = parts[1].trim();
        var store = 'en' + attr.replace(/(^|-)(\w)/g, function (m, a, c) { return c.toUpperCase(); });
        if (el.dataset[store] === undefined) el.dataset[store] = el.getAttribute(attr) || '';
        el.setAttribute(attr, lang === 'el' && EL[key] !== undefined ? EL[key] : el.dataset[store]);
      });
    });

    document.title = lang === 'el' ? META.el.title : original.title;
    if (meta.description) meta.description.content = lang === 'el' ? META.el.description : original.description;
    if (meta.ogTitle) meta.ogTitle.content = document.title;
    if (meta.ogDescription) meta.ogDescription.content = lang === 'el' ? META.el.ogDescription : original.ogDescription;

    each('.lang button', function (b) { b.setAttribute('aria-pressed', String(b.dataset.lang === lang)); });
  }

  window.apodixI18n = { t: t, get lang() { return current; } };

  each('.lang button', function (b) {
    b.addEventListener('click', function () {
      write(b.dataset.lang);
      apply(b.dataset.lang);
    });
  });

  apply(preferred());
})();
