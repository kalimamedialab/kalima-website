"""
Kalima Media Lab, www.kalimamedialab.com
Flask app pubblica. Repo a sé (github.com/kalimamedialab/kalima-website), radice del servizio Railway.

Lingue: una pagina per lingua, /<lingua>/. I testi stanno in traduzioni/<lingua>.json
(chiavi a punti); l'italiano è il riferimento. Una chiave che manca in una lingua si mostra
in inglese, e se manca anche lì in italiano.
/ porta alla lingua del visitatore: cookie kalima_lingua, poi Accept-Language, poi italiano.
Pagine dei servizi (/<lingua>/ong/, /<lingua>/media-bilingue/…): elenco in PAGINE, modello templates/servizio.html.
Modulo di contatto (home e pagina ONG): POST /<lingua>/contatto/, risposta automatica in contatti.py.
"""

import json
import os
import re
import time
import urllib.request
from xml.sax.saxutils import escape

from flask import Flask, abort, make_response, redirect, render_template, request

import contatti
from markupsafe import Markup
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__, template_folder='templates', static_folder='static')
# Railway sta davanti all'app: senza questo Flask crede di essere in http (redirect in http://, cookie senza Secure).
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Indirizzo usato in canonical, hreflang e sitemap. www perché kalimamedialab.com senza www oggi dà 403 (DNS).
SITO = os.environ.get('SITO_URL', 'https://www.kalimamedialab.com').rstrip('/')
COOKIE_LINGUA = 'kalima_lingua'

# Lingue del sito, nell'ordine del selettore. La prima è la predefinita.
# nome = il nome della lingua scritto in quella lingua (niente bandiere: una bandiera è un paese, non una lingua).
# hreflang: solo se diverso dal codice (pt = portoghese del Brasile).
# ricaduta: lingua dei testi che mancano (predefinita l'inglese; il francese dove è la seconda lingua).
# Per aggiungere una lingua: una riga qui + traduzioni/<codice>.json.
LINGUE = {
    'it': {'nome': 'Italiano', 'dir': 'ltr'},
    'en': {'nome': 'English', 'dir': 'ltr'},
    'fr': {'nome': 'Français', 'dir': 'ltr'},
    'es': {'nome': 'Español', 'dir': 'ltr'},
    'pt': {'nome': 'Português', 'dir': 'ltr', 'hreflang': 'pt-BR'},
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
    'wo': {'nome': 'Wolof', 'dir': 'ltr', 'ricaduta': 'fr'},
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


RICADUTA = 'en'  # lingua usata per le chiavi che mancano, prima dell'italiano (salvo 'ricaduta' in LINGUE)


def hreflang(codice):
    return LINGUE[codice].get('hreflang', codice)


def lingua_del_testo(lingua, chiave):
    """In che lingua si mostra davvero una chiave: la lingua della pagina, poi la sua ricaduta
    (di solito l'inglese), poi l'inglese, poi l'italiano."""
    ricaduta = LINGUE.get(lingua, {}).get('ricaduta', RICADUTA)
    for codice in (lingua, ricaduta, RICADUTA, PREDEFINITA):
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


EMAIL_INFO = email_protetta('projects')  # indirizzo di contatto del sito: {email} nei testi


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
        ha=lambda chiave: lingua_del_testo(lingua, chiave) == lingua,  # testo scritto nella lingua della pagina?
        hreflang=hreflang,
        email=email_protetta,
        percorso_lingua=lambda codice: f'/{codice}/{pagina}',  # la stessa pagina in un'altra lingua
        versione_css=VERSIONE_CSS,
        adesso=int(time.time()),
    )


def _pagina(lingua, stato=200, **modulo):
    arabita_titoli, banglita_titoli = get_titoli()
    html = render_template(
        'index.html',
        arabita_titoli=arabita_titoli,
        banglita_titoli=banglita_titoli,
        **modulo,
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


# Lingue con la pagina scritta nella loro lingua (le altre mostrano la ricaduta, senza indicizzazione).
def _lingue_con(chiave):
    return [c for c in LINGUE if chiave in TRADUZIONI[c]]


def _lingue_privacy():
    return _lingue_con('privacy.2.testo')


# Pagine dei servizi. Chiave = indirizzo (/<lingua>/<slug>/).
# p = prefisso delle chiavi nei JSON (p.titolo, p.meta, p.sotto, p.cosa, p.1.t/p.1.d…, p.perche.t/d, p.come.t, p.come.1-3);
# tema = voce preselezionata nel modulo; icone = una per blocco (percorsi SVG 24×24).
ICONA_GLOBO = '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>'
ICONA_DOCUMENTO = '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6M8 13h8M8 17h6"/>'
PAGINE = {
    'ong': dict(p='ong', tema='ong', pubblico='NGOs, nonprofits', icone=[
        '<path d="M3 7h18v13H3zM8 3h8v4"/><circle cx="11" cy="13" r="3"/><path d="m13.5 15.5 2.5 2.5"/>',
        '<ellipse cx="12" cy="6" rx="8" ry="3"/><path d="M4 6v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
        ICONA_DOCUMENTO,
        '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
        '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/>',
        ICONA_GLOBO,
    ]),
    'media-bilingue': dict(p='media', tema='media', pubblico='Diaspora associations, NGOs, cultural institutions', icone=[
        '<rect x="3" y="4" width="18" height="13" rx="2"/><path d="M8 21h8M12 17v4"/>',
        '<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13 7l4 4"/>',
        '<path d="m21 4-18 7 6 2 2 6 3-4 5 4z"/>',
        '<path d="M4 5a2 2 0 0 1 2-2h12v18H6a2 2 0 0 1-2-2z"/><path d="M8 7h6M8 11h6"/>',
    ]),
    'materiali-didattici': dict(p='materiali', tema='materiali', pubblico='Italian language schools, cultural centres, NGOs', icone=[
        ICONA_DOCUMENTO,
        '<rect x="3" y="3" width="18" height="18" rx="3"/><path d="m8 12 3 3 5-6"/>',
        '<path d="M3 10v4M7 7v10M11 4v16M15 8v8M19 11v2"/>',
        '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
    ]),
    'comunicazione-multilingue': dict(p='comunicazione', tema='comunicazione', pubblico='Organizations with multilingual audiences', icone=[
        ICONA_GLOBO,
        '<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>',
        '<rect x="3" y="4" width="18" height="17" rx="2"/><path d="M3 9h18M8 2v4M16 2v4"/>',
        '<path d="M4 5h8M8 3v2M5 9c1.5 3 4 5 7 6M11 5c-1 4-3.5 7-7 9"/><path d="m13 21 4-9 4 9M14.5 18h5"/>',
    ]),
}


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


def _pagina_servizio(lingua, slug, stato=200, **modulo):
    pagina = PAGINE[slug]
    lingua_testo = lingua_del_testo(lingua, f"{pagina['p']}.1.d")
    html = render_template(
        'servizio.html',
        slug=slug,
        p=pagina['p'],
        icone=pagina['icone'],
        pubblico=pagina['pubblico'],
        tema_pagina=pagina['tema'],
        lingua_testo=lingua_testo,
        dir_testo=LINGUE[lingua_testo]['dir'],
        tradotta=lingua_testo == lingua,
        lingue_pagina=_lingue_con(f"{pagina['p']}.1.d"),
        **modulo,
        **_comuni(lingua, f'{slug}/'),
    )
    return make_response(html, stato)


@app.route('/<lingua>/<slug>/')
def servizio(lingua, slug):
    if lingua not in LINGUE or slug not in PAGINE:
        abort(404)
    return _imposta_cookie(_pagina_servizio(lingua, slug), lingua)


# ── Modulo di contatto ──────────────────────────────────────────────────────
EMAIL_VALIDA = re.compile(r'^[^@\s<>]+@[^@\s<>]+\.[^@\s<>]{2,}$')
INVII_ORA = 5          # messaggi per indirizzo IP in un'ora (per worker)
SECONDI_MINIMI = 3     # chi invia prima di così è un programma
_invii = {}


def _troppi_invii(ip):
    adesso = time.time()
    recenti = [t for t in _invii.get(ip, []) if adesso - t < 3600]
    _invii[ip] = recenti
    if len(recenti) >= INVII_ORA:
        return True
    recenti.append(adesso)
    return False


@app.route('/<lingua>/contatto/', methods=['POST'])
def contatto(lingua):
    if lingua not in LINGUE:
        abort(404)
    f = request.form
    origine = f.get('origine') if f.get('origine') in PAGINE else 'home'
    dati = {
        'nome': f.get('nome', '').strip()[:120],
        'email': f.get('email', '').strip()[:200],
        'organizzazione': f.get('organizzazione', '').strip()[:200],
        'tema': f.get('tema') if f.get('tema') in contatti.TEMI else 'altro',
        'messaggio': f.get('messaggio', '').strip()[:5000],
        'lingua': lingua,
        'origine': origine,
        # campo trappola «sito» (nascosto alle persone): se è compilato lo scarta il prefiltro di contatti.py
        'honeypot': (f.get('sito') or '').strip()[:200],
    }
    try:
        secondi = time.time() - int(f.get('t0', '0'))
    except ValueError:
        secondi = 0
    # Trappole per i programmi. Si risponde sempre «grazie», così il programma non impara niente.
    # Campo nascosto compilato: va a contatti.avvia, che lo scarta e lo registra (log e archivio).
    if dati['honeypot']:
        t = traduttore(lingua)
        contatti.avvia(dati, (str(t('email.oggetto')), str(t('email.testo')).replace('{nome}', dati['nome'])))
        return redirect(f'/{lingua}/grazie/', 303)
    # Invio troppo veloce: scartato qui.
    if secondi < SECONDI_MINIMI:
        return redirect(f'/{lingua}/grazie/', 303)

    errore = None
    if not (dati['nome'] and EMAIL_VALIDA.match(dati['email']) and len(dati['messaggio']) >= 10
            and f.get('consenso')):
        errore = 'modulo.errore'
    elif _troppi_invii(request.remote_addr or '-'):
        errore = 'modulo.troppi'
    if errore:
        stato = 400 if errore == 'modulo.errore' else 429
        if origine in PAGINE:
            return _pagina_servizio(lingua, origine, stato, modulo=dati, errore=errore)
        return _pagina(lingua, stato, modulo=dati, errore=errore)

    t = traduttore(lingua)
    riserva = (str(t('email.oggetto')), str(t('email.testo')).replace('{nome}', dati['nome']))
    contatti.avvia(dati, riserva)
    return redirect(f'/{lingua}/grazie/', 303)


@app.route('/<lingua>/grazie/')
def grazie(lingua):
    if lingua not in LINGUE:
        abort(404)
    return render_template('grazie.html', **_comuni(lingua, 'grazie/'))


# Messaggi vaghi: chi ha scritto risponde da questa pagina (link con token nell'e-mail, contatti.py).
@app.route('/contatti/continua/<token>', methods=['GET', 'POST'])
def contatti_continua(token):
    if request.method == 'POST':
        ok = contatti.riprendi_approfondimento(token, request.form.get('testo', ''))
        return ('Grazie, abbiamo ricevuto la tua risposta.' if ok
                else 'Questo link non è più valido. Se vuoi, scrivici di nuovo dal modulo di contatto.')
    return ('<form method="post"><textarea name="testo" rows="8" required maxlength="4000"></textarea>'
            '<button type="submit">Invia</button></form>')


# ── Sitemap e robots ────────────────────────────────────────────────────────
def _url_sitemap(pagina, codici, x_default=None):
    """Una <url> per lingua, ognuna con tutte le alternative."""
    alternative = ''.join(
        f'<xhtml:link rel="alternate" hreflang="{hreflang(c)}" href="{escape(SITO)}/{c}/{pagina}"/>' for c in codici
    )
    if x_default:
        alternative += f'<xhtml:link rel="alternate" hreflang="x-default" href="{escape(SITO)}/{x_default}/{pagina}"/>'
    return [f'<url><loc>{escape(SITO)}/{c}/{pagina}</loc>{alternative}</url>' for c in codici]


@app.route('/sitemap.xml')
def sitemap():
    righe = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
             'xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    righe += _url_sitemap('', LINGUE, x_default=RICADUTA)
    for slug, pagina in PAGINE.items():
        righe += _url_sitemap(f'{slug}/', _lingue_con(f"{pagina['p']}.1.d"), x_default=RICADUTA)
    # Privacy: solo le versioni scritte davvero nella loro lingua.
    righe += _url_sitemap('privacy/', _lingue_privacy())
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
