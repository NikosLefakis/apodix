(function () {
    /* copy button */
    var btn = document.getElementById('copy');
    if (btn) {
      btn.addEventListener('click', function () {
        try {
          navigator.clipboard.writeText('apodix verify .').then(function () {
            btn.textContent = 'Copied';
            setTimeout(function () { btn.textContent = 'Copy'; }, 1800);
          });
        } catch (e) { /* clipboard unavailable: leave button as is */ }
      });
    }

    /* copy buttons inside code panels */
    [].forEach.call(document.querySelectorAll('.copy-btn'), function (b) {
      b.addEventListener('click', function () {
        var target = document.getElementById(b.getAttribute('data-target'));
        try {
          navigator.clipboard.writeText(target.textContent).then(function () {
            b.textContent = 'Copied';
            setTimeout(function () { b.textContent = 'Copy'; }, 1800);
          });
        } catch (e) { /* clipboard unavailable: leave button as is */ }
      });
    });

    /* scroll-driven moments: 1) Euclid construction, 2) pinned story, 3) the closing square */
    var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var clamp = function (v) { return Math.max(0, Math.min(1, v)); };

    var hero = document.querySelector('.hero');
    function bindEuclid(svg) {
      var parts = [].slice.call(svg.querySelectorAll('[data-from]'));
      parts.forEach(function (el) {
        if (el.classList.contains('dr')) { el.style.strokeDasharray = '1'; el.style.strokeDashoffset = '1'; }
        if (el.classList.contains('pop')) { el.style.transformBox = 'fill-box'; el.style.transformOrigin = 'center'; }
      });
      return function (t) {
        parts.forEach(function (el) {
          var from = +el.getAttribute('data-from'), to = +el.getAttribute('data-to');
          var k = clamp((t - from) / (to - from));
          if (el.classList.contains('dr')) el.style.strokeDashoffset = String(1 - k);
          else if (el.classList.contains('pop')) { el.style.opacity = k > 0 ? '1' : '0'; el.style.transform = 'scale(' + (0.3 + 0.7 * k) + ')'; }
          else el.style.opacity = String(k);
        });
      };
    }
    var paintHero = bindEuclid(document.getElementById('euclid'));
    var paintGap = bindEuclid(document.getElementById('euclid2'));
    var gapSection = document.querySelector('.gap');

    var story = document.querySelector('.story');
    var track = story.querySelector('.story-track');
    var lines = [].slice.call(story.querySelectorAll('.ln[data-at]'));
    var steps = [].slice.call(story.querySelectorAll('.s'));
    var bar = story.querySelector('.story-progress');
    var pinQuery = window.matchMedia('(min-width: 981px) and (min-height: 640px) and (prefers-reduced-motion: no-preference)');

    var qed = document.getElementById('qed');
    var footer = document.querySelector('.site-footer');

    var intro = reduce ? 1 : 0;

    function update() {
      var vh = window.innerHeight;
      var s = clamp(window.scrollY / (hero.offsetHeight * 0.85));
      paintHero(reduce ? 1 : Math.max(intro, 0.3 + 0.7 * s));
      var gr = gapSection.getBoundingClientRect();
      paintGap(reduce ? 1 : clamp((vh * 0.85 - gr.top) / (vh * 0.7)));

      if (story.classList.contains('is-pinned')) {
        var r = track.getBoundingClientRect();
        var p = clamp(-r.top / (r.height - vh));
        lines.forEach(function (l) { l.classList.toggle('on', p >= parseFloat(l.getAttribute('data-at'))); });
        var idx = Math.min(steps.length - 1, Math.floor(p * steps.length));
        steps.forEach(function (st, i) { st.classList.toggle('active', i === idx); st.classList.toggle('done', i < idx); });
        bar.style.setProperty('--p', p);
      }

      var fr = footer.getBoundingClientRect();
      var q = reduce ? 1 : clamp((vh - fr.top) / (fr.height * 0.8));
      qed.style.transform = 'scale(' + q + ')';
    }

    var ticking = false;
    function onScroll() {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(function () { ticking = false; update(); });
    }
    function setMode() { story.classList.toggle('is-pinned', pinQuery.matches); update(); }

    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);
    if (pinQuery.addEventListener) pinQuery.addEventListener('change', setMode); else pinQuery.addListener(setMode);
    setMode();

    /* the first circles draw themselves on load, then scroll takes over */
    if (!reduce) {
      var t0 = null;
      (function tick(ts) {
        if (t0 === null) t0 = ts;
        var k = clamp((ts - t0) / 1600);
        intro = 0.3 * (1 - Math.pow(1 - k, 3));
        update();
        if (k < 1) requestAnimationFrame(tick);
      })(performance.now());
    }
  })();
