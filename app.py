"""
Kalima Media Lab — www.kalimamedialab.com
Flask app pubblica. Repo a sé (github.com/kalimamedialab/kalima-website), radice del servizio Railway.

Lingue: una pagina per lingua, /<lingua>/. I testi stanno in traduzioni/<lingua>.json
(chiavi a punti); l'italiano è il riferimento e copre le chiavi mancanti delle altre lingue.
/ porta alla lingua del visitatore: cookie kalima_lingua, poi Accept-Language, poi italiano.
"""

import json
import os
import time
import urllib.request
from xml.sax.saxutils import escape

from flask import Flask, abort, make_response, redirect, render_template, request
from markupsafe import Markup

app = Flask(__name__, template_folder='templates', static_folder='static')

SITO = os.environ.get('SITO_URL', 'https://kalimamedialab.com').rstrip('/')
COOKIE_LINGUA = 'kalima_lingua'

# Lingue del sito, nell'ordine della barra. La prima è la predefinita.
# Per aggiungere una lingua: una riga qui + traduzioni/<codice>.json.
LINGUE = {
    'it': {'bandiera': '🇮🇹', 'etichetta': 'IT', 'dir': 'ltr'},
    'en': {'bandiera': '🇬🇧', 'etichetta': 'EN', 'dir': 'ltr'},
    'fr': {'bandiera': '🇫🇷', 'etichetta': 'FR', 'dir': 'ltr'},
    'es': {'bandiera': '🇪🇸', 'etichetta': 'ES', 'dir': 'ltr'},
    'ar': {'bandiera': '🇸🇦', 'etichetta': 'AR', 'dir': 'rtl'},
    'zh': {'bandiera': '🇨🇳', 'etichetta': 'ZH', 'dir': 'ltr'},
    'bn': {'bandiera': '🇧🇩', 'etichetta': 'বাং', 'dir': 'ltr'},
    'ur': {'bandiera': '🇵🇰', 'etichetta': 'UR', 'dir': 'rtl'},
    'hi': {'bandiera': '🇮🇳', 'etichetta': 'HI', 'dir': 'ltr'},
    'tr': {'bandiera': '🇹🇷', 'etichetta': 'TR', 'dir': 'ltr'},
    'ro': {'bandiera': '🇷🇴', 'etichetta': 'RO', 'dir': 'ltr'},
    'tl': {'bandiera': '🇵🇭', 'etichetta': 'TL', 'dir': 'ltr'},
    'wo': {'bandiera': '🇸🇳', 'etichetta': 'WO', 'dir': 'ltr'},
    'sq': {'bandiera': '🇦🇱', 'etichetta': 'SQ', 'dir': 'ltr'},
    'am': {'bandiera': '🇪🇹', 'etichetta': 'አማ', 'dir': 'ltr'},
    'ti': {'bandiera': '🇪🇷', 'etichetta': 'ትግ', 'dir': 'ltr'},
    'ru': {'bandiera': '🇷🇺', 'etichetta': 'RU', 'dir': 'ltr'},
    'be': {'bandiera': '🇧🇾', 'etichetta': 'BE', 'dir': 'ltr'},
    'uk': {'bandiera': '🇺🇦', 'etichetta': 'UK', 'dir': 'ltr'},
    'fa': {'bandiera': '🇮🇷', 'etichetta': 'فا', 'dir': 'rtl'},
}
PREDEFINITA = next(iter(LINGUE))


# ── Traduzioni ──────────────────────────────────────────────────────────────
def _carica_traduzioni():
    cartella = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'traduzioni')
    testi = {}
    for codice in LINGUE:
        percorso = os.path.join(cartella, f'{codice}.json')
        with open(percorso, encoding='utf-8') as f:
            testi[codice] = json.load(f)
    return testi


TRADUZIONI = _carica_traduzioni()


def traduttore(lingua):
    """t('chiave') nella lingua della pagina; se manca, l'italiano; se manca anche quello, la chiave."""
    def t(chiave):
        testo = TRADUZIONI[lingua].get(chiave)
        if testo is None:
            testo = TRADUZIONI[PREDEFINITA].get(chiave, chiave)
        return Markup(testo)  # i testi sono nostri e possono contenere <br>, <em>
    return t


# ── Feed RSS di Arabita e Banglita (cache in memoria, 10 minuti) ────────────
CACHE_FEED_SECONDI = 600
_cache_feed = {}


def _fetch_feed(url, limit=3):
    salvato = _cache_feed.get(url)
    if salvato and time.time() - salvato[0] < CACHE_FEED_SECONDI:
        return salvato[1]
    try:
        import feedparser
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'KalimaMediaLab/1.0 (+https://kalimamedialab.com)'}
        )
        with urllib.request.urlopen(req, timeout=6) as r:
            data = r.read()
        feed = feedparser.parse(data)
        risultati = []
        for entry in feed.entries[:limit]:
            title = entry.get('title', '')
            # prova separatori: · oppure -
            sep = None
            for s in [' · ', ' - ', ' – ']:
                if s in title:
                    sep = s
                    break
            if sep:
                parts = title.split(sep, 1)
                risultati.append({'it': parts[0].strip(), 'l2': parts[1].strip()})
            else:
                risultati.append({'it': title.strip(), 'l2': ''})
    except Exception as e:
        print(f"[WARN] feed {url}: {e}")
        if salvato:
            return salvato[1]  # meglio i titoli di prima che nessuno
        return []
    _cache_feed[url] = (time.time(), risultati)
    return risultati


def get_titoli():
    arabita = _fetch_feed('https://arabita.news/rss.xml')
    banglita = _fetch_feed('https://banglita.news/rss.xml')
    return arabita, banglita


# ── Pagine ──────────────────────────────────────────────────────────────────
def _lingua_preferita():
    cookie = request.cookies.get(COOKIE_LINGUA, '')
    if cookie in LINGUE:
        return cookie
    return request.accept_languages.best_match(list(LINGUE)) or PREDEFINITA


def _pagina(lingua, stato=200):
    arabita_titoli, banglita_titoli = get_titoli()
    html = render_template(
        'index.html',
        lingua=lingua,
        info_lingua=LINGUE[lingua],
        lingue=LINGUE,
        predefinita=PREDEFINITA,
        sito=SITO,
        t=traduttore(lingua),
        arabita_titoli=arabita_titoli,
        banglita_titoli=banglita_titoli,
    )
    return make_response(html, stato)


@app.route('/')
def radice():
    risposta = redirect(f'/{_lingua_preferita()}/', 302)
    risposta.headers['Vary'] = 'Cookie, Accept-Language'
    return risposta


@app.route('/<lingua>/')
def index(lingua):
    if lingua not in LINGUE:
        abort(404)
    risposta = _pagina(lingua)
    # Chi apre una lingua la sceglie: la ritroverà su /
    risposta.set_cookie(COOKIE_LINGUA, lingua, max_age=365 * 24 * 3600, samesite='Lax',
                        secure=request.is_secure)
    return risposta


@app.route('/sitemap.xml')
def sitemap():
    righe = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
             'xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    alternative = ''.join(
        f'<xhtml:link rel="alternate" hreflang="{c}" href="{escape(SITO)}/{c}/"/>' for c in LINGUE
    ) + f'<xhtml:link rel="alternate" hreflang="x-default" href="{escape(SITO)}/"/>'
    for c in LINGUE:
        righe.append(f'<url><loc>{escape(SITO)}/{c}/</loc>{alternative}</url>')
    righe.append('</urlset>')
    risposta = make_response('\n'.join(righe))
    risposta.headers['Content-Type'] = 'application/xml; charset=utf-8'
    return risposta


@app.route('/robots.txt')
def robots():
    risposta = make_response(f'User-agent: *\nAllow: /\nSitemap: {SITO}/sitemap.xml\n')
    risposta.headers['Content-Type'] = 'text/plain; charset=utf-8'
    return risposta


@app.errorhandler(404)
def not_found(e):
    lingua = _lingua_preferita()
    return _pagina(lingua, 404)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    app.run(host='0.0.0.0', port=port, debug=False)
