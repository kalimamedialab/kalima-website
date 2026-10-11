"""
prova_trappola.py — prova del campo trappola («sito») del modulo di contatto.

Uso:  python prova_trappola.py

Non chiama l'IA, non manda e-mail, non scrive nell'archivio: quelle tre parti
sono sostituite da versioni finte. Il prefiltro di filtro.py invece è quello vero.
contatti.avvia di solito lavora in un thread; qui gira subito, così il log si vede.

a) modulo con «sito» vuoto: pagina di ringraziamento, nessuno scarto dal prefiltro;
b) modulo con «sito» = "http://spam.example": STESSA risposta, e nel log
   «scartato dal prefiltro: campo nascosto compilato».
"""
import contextlib
import io
import os
import time

os.environ.pop('ANTHROPIC_API_KEY', None)   # niente IA, nemmeno per sbaglio

import app as sito_app   # noqa: E402
import contatti          # noqa: E402

email_finte, archiviati = [], []
contatti.chiedi_a_claude = lambda *a, **k: None
contatti.invia_email = lambda a, oggetto, testo, rispondi_a=None: email_finte.append(a) or True
contatti._archivia = lambda dati, stato='completato', **k: archiviati.append(stato)
contatti.avvia = lambda dati, riserva: contatti.gestisci(dati, riserva)   # senza thread

client = sito_app.app.test_client()


def invia(sito):
    contatti._RECENTI.clear() if hasattr(contatti._RECENTI, 'clear') else None
    log = io.StringIO()
    with contextlib.redirect_stdout(log):
        r = client.post('/it/contatto/', data={
            'nome': 'Prova', 'email': 'prova@example.com', 'organizzazione': '',
            'tema': 'altro', 'messaggio': 'Buongiorno, vorrei informazioni sui vostri servizi per una cooperativa.',
            'consenso': '1', 't0': str(int(time.time()) - 30), 'origine': 'home', 'sito': sito,
        })
    return r, log.getvalue()


ra, log_a = invia('')
rb, log_b = invia('http://spam.example')

ok_a = ra.status_code == 303 and ra.headers['Location'].endswith('/it/grazie/') and 'scartato dal prefiltro' not in log_a
ok_stessa = (ra.status_code, ra.headers.get('Location')) == (rb.status_code, rb.headers.get('Location'))
ok_b = 'scartato dal prefiltro: campo nascosto compilato' in log_b

print(f"a) sito vuoto      -> {ra.status_code} {ra.headers.get('Location')}  {'OK' if ok_a else 'NO'}")
print(f"b) sito compilato  -> {rb.status_code} {rb.headers.get('Location')}  stessa risposta: {'OK' if ok_stessa else 'NO'}")
print(f"   log b: {'OK' if ok_b else 'NO'}  {[r for r in log_b.splitlines() if 'prefiltro' in r]}")
print(f"   archivio finto: {archiviati}  e-mail finte a: {email_finte}")
print('TUTTO OK' if ok_a and ok_b and ok_stessa else 'QUALCOSA NON VA')
