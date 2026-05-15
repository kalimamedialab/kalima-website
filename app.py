"""
Kalima Media Lab — www.kalimamedialab.com
Flask app pubblica. Root Directory su Railway: kalima/website_pub
"""

import os
import sys
import urllib.request
from flask import Flask, render_template

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', 'kalima-dev-secret')

def _fetch_feed(url, limit=3):
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
            if ' · ' in title:
                parts = title.split(' · ', 1)
                risultati.append({'it': parts[0].strip(), 'l2': parts[1].strip()})
            else:
                risultati.append({'it': title.strip(), 'l2': ''})
        return risultati
    except Exception as e:
        print(f"[WARN] feed {url}: {e}")
        return []

def get_titoli():
    arabita  = _fetch_feed('https://arabita.news/rss.xml')
    banglita = _fetch_feed('https://banglita.news/rss.xml')
    return arabita, banglita

@app.route('/')
def index():
    arabita_titoli, banglita_titoli = get_titoli()
    return render_template('index.html',
        arabita_titoli=arabita_titoli,
        banglita_titoli=banglita_titoli,
    )

@app.errorhandler(404)
def not_found(e):
    arabita_titoli, banglita_titoli = get_titoli()
    return render_template('index.html',
        arabita_titoli=arabita_titoli,
        banglita_titoli=banglita_titoli,
    ), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    app.run(host='0.0.0.0', port=port, debug=False)
