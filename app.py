"""
Kalima Media Lab, www.kalimamedialab.com
Flask app pubblica. Repo a sé (github.com/kalimamedialab/kalima-website), radice del servizio Railway.

Lingue: una pagina per lingua, /<lingua>/. I testi stanno in traduzioni/<lingua>.json
(chiavi a punti); l'italiano è il riferimento. Una chiave che manca in una lingua si mostra
in inglese, e se manca anche lì in italiano.
/ porta alla lingua del visitatore: cookie kalima_lingua, poi Accept-Language, poi italiano.
"""

import json
import os
import time
import urllib.request
from xml.sax.saxutils import escape

from flask import Flask, abort, make_response, redirect, render_template, request
from markupsafe import Markup
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__, template_folder='templates', static_folder='static')
# Railway sta davanti all'app: senza questo Flask crede di essere in http (redirect in http://, cookie senza Secure).
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Indirizzo usato in canonical, hreflang e sitemap. www perché kalimamedialab.com senza www oggi dà 403 (DNS).
SITO = os.environ.get('SITO_URL', 'https://www.kalimamedialab.com').rstrip('/')
COOKIE_LINGUA = 'kalima_lingua'

# Lingue del sito, nell'ordine del selettore. La prima è la predefinita.
# nome = il nome della lingua scritto in quella lingua (niente bandiere: una bandiera è un paese, non una lingua).
# Per aggiungere una lingua: una riga qui + traduzioni/<codice>.json.
LINGUE = {
    'it': {'nome': 'Italiano', 'dir': 'ltr'},
    'en': {'nome': 'English', 'dir': 'ltr'},
    'fr': {'nome': 'Français', 'dir': 'ltr'},
    'es': {'nome': 'Español', 'dir': 'ltr'},
    'de': {'nome': 'Deutsch', 'dir': 'ltr'},
    'ro': {'nome': 'Română', 'dir': 'ltr'},
    'pl': {'nome': 'Polski', 'dir': 'ltr'},
    'sq': {'nome': 'Shqip', 'dir': 'ltr'},
    'lv': {'nome': 'Latviešu', 'dir': 'ltr'},
    'uk': {'nome': 'Українська', 'dir': 'ltr'},
    'ru': {'nome': 'Русский', 'dir': 'ltr'},
    'be': {'nome': 'Беларуская', 'dir': 'ltr'},
    'tr': {'nome': 'Türkçe', 'dir': 'ltr'},
    'ar': {'nome': 'العربية', 'dir': 'rtl'},
    'fa': {'nome': 'فارسی', 'dir': 'rtl'},
    'ur': {'nome': 'اردو', 'dir': 'rtl'},
    'hi': {'nome': 'हिन्दी', 'dir': 'ltr'},
    'bn': {'nome': 'বাংলা', 'dir': 'ltr'},
    'si': {'nome': 'සිංහල', 'dir': 'ltr'},
    'th': {'nome': 'ไทย', 'dir': 'ltr'},
    'zh': {'nome': '中文', 'dir': 'ltr'},
    'ja': {'nome': '日本語', 'dir': 'ltr'},
    'tl': {'nome': 'Tagalog', 'dir': 'ltr'},
    'am': {'nome': 'አማርኛ', 'dir': 'ltr'},
    'ti': {'nome': 'ትግርኛ', 'dir': 'ltr'},
    'wo': {'nome': 'Wolof', 'dir': 'ltr'},
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


RICADUTA = 'en'  # lingua usata per le chiavi che mancano, prima dell'italiano


def lingua_del_testo(lingua, chiave):
    """In che lingua si mostra davvero una chiave: la lingua della pagina, poi l'inglese, poi l'italiano."""
    for codice in (lingua, RICADUTA, PREDEFINITA):
        if chiave in TRADUZIONI.get(codice, {}):
            return codice
    return None


def email_protetta(utente, dominio='kalimamedialab.com', classe=''):
    """Indirizzo e-mail non leggibile dai programmi che raccolgono indirizzi: nell'HTML ci sono solo
    i due pezzi rovesciati; lo script in fondo alle pagine li ricompone in un link mailto.
    Senza JavaScript si legge «utente [at] dominio [dot] com»."""
    return Markup(
        '<a class="email-protetta {classe}" href="#" data-u="{u}" data-d="{d}">{testo}</a>'
    ).format(classe=classe, u=utente[::-1], d=dominio[::-1],
             testo=f'{utente} [at] {dominio.replace(".", " [dot] ")}')


EMAIL_INFO = email_protetta('info')


def traduttore(lingua):
    """t('chiave') nella lingua della pagina (con le ricadute di lingua_del_testo); se non c'è da nessuna parte, la chiave.
    {email} nel testo diventa l'indirizzo info protetto."""
    def t(chiave):
        codice = lingua_del_testo(lingua, chiave)
        if codice is None:
            return chiave
        # i testi sono nostri e possono contenere <br>, <em>, <ul>
        return Markup(TRADUZIONI[codice][chiave]).replace('{email}', EMAIL_INFO)
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


_CSS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'css', 'sito.css')
VERSIONE_CSS = str(int(os.path.getmtime(_CSS)))  # cambia a ogni modifica: niente CSS vecchio in cache


def _comuni(lingua, pagina=''):
    """Variabili che servono a tutti i template. pagina = percorso dopo /<lingua>/ (es. 'privacy/')."""
    return dict(
        lingua=lingua,
        info_lingua=LINGUE[lingua],
        lingue=LINGUE,
        predefinita=PREDEFINITA,
        sito=SITO,
        t=traduttore(lingua),
        email=email_protetta,
        percorso_lingua=lambda codice: f'/{codice}/{pagina}',  # la stessa pagina in un'altra lingua
        versione_css=VERSIONE_CSS,
    )


def _pagina(lingua, stato=200):
    arabita_titoli, banglita_titoli = get_titoli()
    html = render_template(
        'index.html',
        arabita_titoli=arabita_titoli,
        banglita_titoli=banglita_titoli,
        **_comuni(lingua),
    )
    return make_response(html, stato)


def _imposta_cookie(risposta, lingua):
    # Chi apre una lingua la sceglie: la ritroverà su /
    risposta.set_cookie(COOKIE_LINGUA, lingua, max_age=365 * 24 * 3600, samesite='Lax',
                        secure=request.is_secure)
    return risposta


@app.route('/')
def radice():
    risposta = redirect(f'/{_lingua_preferita()}/', 302)
    risposta.headers['Vary'] = 'Cookie, Accept-Language'
    return risposta


@app.route('/<lingua>/')
def index(lingua):
    if lingua not in LINGUE:
        abort(404)
    return _imposta_cookie(_pagina(lingua), lingua)


# Lingue con l'informativa privacy scritta nella loro lingua (le altre mostrano la ricaduta).
def _lingue_privacy():
    return [c for c in LINGUE if 'privacy.2.testo' in TRADUZIONI[c]]


@app.route('/<lingua>/privacy/')
def privacy(lingua):
    if lingua not in LINGUE:
        abort(404)
    lingua_testo = lingua_del_testo(lingua, 'privacy.2.testo')
    html = render_template(
        'privacy.html',
        lingua_testo=lingua_testo,
        dir_testo=LINGUE[lingua_testo]['dir'],
        tradotta=lingua_testo == lingua,
        lingue_privacy=_lingue_privacy(),
        **_comuni(lingua, 'privacy/'),
    )
    return _imposta_cookie(make_response(html), lingua)


@app.route('/privacy')
@app.route('/privacy/')
def privacy_senza_lingua():
    risposta = redirect(f'/{_lingua_preferita()}/privacy/', 302)
    risposta.headers['Vary'] = 'Cookie, Accept-Language'
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
    # Privacy: solo le versioni scritte davvero nella loro lingua.
    lingue_privacy = _lingue_privacy()
    alternative_privacy = ''.join(
        f'<xhtml:link rel="alternate" hreflang="{c}" href="{escape(SITO)}/{c}/privacy/"/>' for c in lingue_privacy
    )
    for c in lingue_privacy:
        righe.append(f'<url><loc>{escape(SITO)}/{c}/privacy/</loc>{alternative_privacy}</url>')
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
