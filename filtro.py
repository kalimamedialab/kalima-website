"""
filtro.py - smistamento dei messaggi PRIMA di spendere token sul modello grande.

Tre livelli, dal più economico al più costoso:
  1. prefiltro(): regole semplici, zero token. Scarta lo spam evidente.
  2. triage(): una chiamata brevissima a un modello piccolo (istruzioni in ia/triage.md, circa 500 parole).
  3. solo se il messaggio è `idoneo` o `vago` si usa il modello grande con linee guida e conoscenza.

Cosa succede per ogni categoria (tabella AZIONI):
  ignora             nessuna risposta, nessun resoconto: solo una riga nell'archivio
  risposta_fissa     risposta scritta una volta per tutte (nessun token), nessun resoconto immediato
  chiedi_dettagli    risposta breve con 1-2 domande, resoconto in attesa finché non rispondono
  rispondi_e_riferisci risposta completa e resoconto subito

Uso (nel codice che riceve il modulo):
    from filtro import prefiltro, smista
    p = prefiltro(testo, honeypot=campo_nascosto, secondi=tempo_di_compilazione)
    if p[0] == "scarta": archivio.registra(tema="spam", ...); return
    esito = smista(testo, chiama_modello_piccolo)       # chiama(sistema, utente) -> testo
    # esito["azione"] dice cosa fare; esito["categoria"], esito["lingua"], esito["domande"]...
"""
import json
import re
from pathlib import Path

AZIONI = {
    "spam": "ignora", "ostile": "ignora", "manipolazione": "ignora", "fornitore": "ignora",
    "candidatura": "risposta_fissa", "fuori_ambito": "risposta_fissa",
    "vago": "chiedi_dettagli", "idoneo": "rispondi_e_riferisci",
}

PAROLE_SPAM = [
    "backlink", "guest post", "seo ", "rank #1", "first page of google", "prima pagina di google", "posizionamento",
    "casino", "casinò", "crypto", "bitcoin", "forex", "viagra", "cialis", "loan offer", "prestito immediato",
    "lottery", "you have won", "hai vinto", "whatsapp +", "telegram", "click here", "clicca qui", "unsubscribe",
    "web design services", "website redesign", "boost your traffic", "increase your sales", "lead generation",
    "buy followers", "adult", "escort", "invoice attached", "fattura allegata",
]
DOMINI_USA_E_GETTA = ("mailinator.", "guerrillamail.", "10minutemail.", "tempmail.", "yopmail.", "sharklasers.")
_URL = re.compile(r"https?://|www\.", re.I)
_recenti = {}


def prefiltro(testo, honeypot="", secondi=None, email="", visti=None):
    """Restituisce (decisione, motivo): 'scarta' | 'dubbio' | 'passa'. Nessun token speso."""
    t = (testo or "").strip()
    if honeypot:
        return "scarta", "campo nascosto compilato"
    if secondi is not None and secondi < 3:
        return "scarta", "compilato in meno di 3 secondi"
    if len(t) < 3:
        return "scarta", "messaggio vuoto"
    if any(email.lower().endswith(d) or d in email.lower() for d in DOMINI_USA_E_GETTA):
        return "scarta", "email usa e getta"
    chiave = re.sub(r"\W+", "", t.lower())[:300]
    registro = visti if visti is not None else _recenti
    if chiave in registro:
        return "scarta", "messaggio identico già ricevuto"
    registro[chiave] = True
    punti = 0
    n_url = len(_URL.findall(t))
    punti += 2 if n_url >= 3 else (1 if n_url >= 1 else 0)
    basso = t.lower()
    punti += 2 * sum(1 for p in PAROLE_SPAM if p in basso)
    lettere = [c for c in t if c.isalpha()]
    if len(lettere) > 20 and sum(c.isupper() for c in lettere) / len(lettere) > 0.6:
        punti += 1
    if len(t) > 3000:
        punti += 1
    if punti >= 5:
        return "scarta", f"punteggio spam {punti}"
    if punti >= 2:
        return "dubbio", f"punteggio spam {punti}"
    return "passa", "ok"


def _json(testo):
    m = re.search(r"\{.*\}", testo or "", re.S)
    try:
        return json.loads(m.group(0)) if m else None
    except Exception:
        return None


def smista(testo, chiama, istruzioni_path=None):
    """Una chiamata breve a un modello piccolo. `chiama(sistema, utente) -> str` lo fornisci tu.
    In caso di errore o JSON illeggibile il messaggio viene trattato come idoneo (meglio una risposta in più
    che un messaggio vero perso)."""
    sistema = Path(istruzioni_path or Path(__file__).parent / "ia" / "triage.md").read_text(encoding="utf-8")
    try:
        dati = _json(chiama(sistema, "MESSAGGIO DA CLASSIFICARE:\n" + (testo or "")[:4000]))
    except Exception:
        dati = None
    if not dati or dati.get("categoria") not in AZIONI:
        dati = {"categoria": "idoneo", "motivo": "triage non riuscito"}
    dati["azione"] = AZIONI[dati["categoria"]]
    if dati["categoria"] == "ostile" and dati.get("minaccia"):
        dati["azione"] = "rispondi_e_riferisci"  # le minacce dirette arrivano a te, senza risposta lunga
        dati["solo_resoconto"] = True
    dati["domande"] = (dati.get("domande") or [])[:2]
    return dati


RISPOSTE_FISSE = {
    "candidatura": {
        "it": "Grazie per il messaggio. Al momento non c'è una selezione in corso e per ora non servono altri documenti. Abbiamo inoltrato il messaggio a Kalima.",
        "en": "Thank you for your message. There is no selection in progress at the moment and no further documents are needed. We have passed your message on to Kalima.",
    },
    "fuori_ambito": {
        "it": "Grazie per il messaggio. Quello che chiedi non rientra tra le attività di Kalima Media Lab, che si occupa di scuola online di italiano, strumenti digitali per organizzazioni non profit, testate bilingui e materiali didattici. Per questo non possiamo aiutarti su questo punto.",
        "en": "Thank you for your message. What you are asking is outside the activities of Kalima Media Lab, which works on online Italian courses, digital tools for non-profit organisations, bilingual news sites and teaching materials. For this reason we cannot help with this request.",
    },
}


def risposta_fissa(categoria, lingua):
    """Testo fisso. Se la lingua non c'è, inglese: la dichiarazione di IA e la firma le aggiunge il tuo codice."""
    r = RISPOSTE_FISSE.get(categoria, {})
    return r.get(lingua) or r.get("en", "")


if __name__ == "__main__":
    print(prefiltro("We can rank your website #1 on Google. Click here https://a.com https://b.com https://c.com"))
    print(prefiltro("Buongiorno, siamo una cooperativa e cerchiamo un archivio per i progetti", secondi=40))
    finto = lambda s, u: '{"categoria": "vago", "lingua": "it", "domande": ["Per chi serve?", "Che livello?", "Terza?"], "motivo": "generico"}'
    print(smista("Vorrei informazioni", finto))
    print(smista("x", lambda s, u: "non json"))
    print(risposta_fissa("candidatura", "it"))
