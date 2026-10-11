"""
conoscenza.py - lettura della cartella `conoscenza/` per il risponditore di Kalima.

Cosa fa
- legge i file .md e .txt della cartella (e, se installati i pacchetti, .docx e .pdf);
- spezza ogni file in blocchi per titolo;
- cerca i blocchi più utili per una domanda (metodo BM25, senza servizi esterni);
- restituisce un testo pronto da inserire nel prompt, con fonte e data di verifica;
- segnala i file da riverificare.

Uso minimo in contatti.py (tre righe):
    from pathlib import Path
    from conoscenza import Conoscenza
    K = Conoscenza(Path(__file__).parent / "ia" / "conoscenza")   # una volta all'avvio
    extra = K.contesto(parole_chiave_italiane, k=5)   # per ogni messaggio

IMPORTANTE: chi scrive può usare qualsiasi lingua, ma i file sono in italiano.
Per questo `contesto()` va chiamato con parole chiave in italiano (5-12 parole),
che il modello estrae dal messaggio con una chiamata breve prima di rispondere.
"""
import math
import re
from collections import Counter
from datetime import date
from pathlib import Path

STOP = set("""a ad al alla alle allo agli ai anche che chi ci come con contro cui da dal dalla dalle dei del della delle
di dove e ed fra gli ha hanno ho i il in io la le lo loro lui ma me mi molto nei nel nella nelle non noi nostro o per
perche piu quale quali quando quello questa queste questi questo se si sia sono su sua suo tra tu un una uno vi voi""".split())


def _token(testo):
    parole = re.findall(r"[a-zàèéìòù0-9]+", testo.lower())
    out = []
    for p in parole:
        if p in STOP or len(p) < 2:
            continue
        # taglio semplice dei suffissi per far combaciare singolare/plurale
        if len(p) > 5:
            p = re.sub(r"(zione|zioni|mente|ità|ita|ale|ali|are|ere|ire|ato|ati|ata|ate|ico|ici|iche|ica|[aeio])$", "", p)
        out.append(p)
    return out


def _front_matter(testo):
    meta, corpo = {}, testo
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", testo, re.S)
    if m:
        for riga in m.group(1).splitlines():
            if ":" in riga:
                k, v = riga.split(":", 1)
                meta[k.strip()] = v.strip()
        corpo = m.group(2)
    return meta, corpo


def _leggi_file(p):
    s = p.suffix.lower()
    if s in (".md", ".txt"):
        return p.read_text(encoding="utf-8", errors="ignore")
    if s == ".docx":
        from docx import Document  # pip install python-docx
        return "\n".join(par.text for par in Document(str(p)).paragraphs)
    if s == ".pdf":
        from pypdf import PdfReader  # pip install pypdf
        return "\n".join((pg.extract_text() or "") for pg in PdfReader(str(p)).pages)
    return ""


class Conoscenza:
    def __init__(self, cartella, includi_bozze=False):
        self.blocchi = []
        self.da_riverificare = []
        oggi = date.today().isoformat()
        for p in sorted(Path(cartella).rglob("*")):
            if not p.is_file() or p.suffix.lower() not in (".md", ".txt", ".docx", ".pdf"):
                continue
            if p.name.startswith("00_") or "fonti_originali" in p.parts:
                continue
            try:
                meta, corpo = _front_matter(_leggi_file(p))
            except Exception as e:  # file illeggibile: si salta, non si blocca il risponditore
                print(f"[conoscenza] saltato {p.name}: {e}")
                continue
            if meta.get("bozza", "").lower() in ("si", "sì", "true") and not includi_bozze:
                continue
            if meta.get("prossima_verifica") and meta["prossima_verifica"] < oggi:
                self.da_riverificare.append(p.name)
            titolo_doc = meta.get("titolo", p.stem)
            for titolo_sez, testo in self._sezioni(corpo):
                for parte in self._spezza(testo):
                    self.blocchi.append({
                        "file": p.name, "titolo": titolo_doc, "sezione": titolo_sez,
                        "testo": parte, "verificato": meta.get("verificato", "data non indicata"),
                        "fonti": meta.get("fonti", "fonte non indicata"),
                        "toks": _token(titolo_doc + " " + titolo_sez + " " + parte),
                    })
        n = len(self.blocchi) or 1
        self.lung_media = sum(len(b["toks"]) for b in self.blocchi) / n
        df = Counter()
        for b in self.blocchi:
            df.update(set(b["toks"]))
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    @staticmethod
    def _sezioni(corpo):
        parti, titolo, buf = [], "", []
        for riga in corpo.splitlines():
            if riga.startswith("#"):
                if buf:
                    parti.append((titolo, "\n".join(buf).strip()))
                titolo, buf = riga.lstrip("# ").strip(), []
            else:
                buf.append(riga)
        if buf:
            parti.append((titolo, "\n".join(buf).strip()))
        return [(t, x) for t, x in parti if x]

    @staticmethod
    def _spezza(testo, massimo=1400):
        if len(testo) <= massimo:
            return [testo]
        out, cur = [], ""
        for par in testo.split("\n"):
            if len(cur) + len(par) > massimo and cur:
                out.append(cur.strip())
                cur = ""
            cur += par + "\n"
        if cur.strip():
            out.append(cur.strip())
        return out

    def cerca(self, domanda, k=5):
        q = _token(domanda)
        if not q or not self.blocchi:
            return []
        punteggi = []
        for b in self.blocchi:
            tf = Counter(b["toks"])
            L = len(b["toks"]) or 1
            s = 0.0
            for t in q:
                if t in tf:
                    s += self.idf.get(t, 0) * (tf[t] * 2.2) / (tf[t] + 1.2 * (0.25 + 0.75 * L / self.lung_media))
            if s > 0:
                punteggi.append((s, b))
        punteggi.sort(key=lambda x: -x[0])
        return [b for _, b in punteggi[:k]]

    def contesto(self, domanda, k=5, max_caratteri=7000):
        """Testo da inserire nel prompt. Vuoto se non c'è nulla di pertinente."""
        trovati = self.cerca(domanda, k)
        if not trovati:
            return ""
        righe = ["INFORMAZIONI VERIFICATE DISPONIBILI (da usare solo se pertinenti; riportare sempre che vanno controllate presso l'ente competente):"]
        tot = 0
        for b in trovati:
            blocco = (f"[{b['titolo']} / {b['sezione']} | verificato il {b['verificato']} | fonti: {b['fonti']}]\n{b['testo']}")
            if tot + len(blocco) > max_caratteri:
                break
            righe.append(blocco)
            tot += len(blocco)
        return "\n\n".join(righe)


def converti_in_bozza(sorgente, destinazione):
    """Converte PDF e Word di `sorgente` in bozze .md in `destinazione`, marcate bozza: si.
    Le bozze NON vengono lette dal risponditore finché non le rivedi e togli la riga `bozza`."""
    dest = Path(destinazione)
    dest.mkdir(parents=True, exist_ok=True)
    for p in Path(sorgente).iterdir():
        if p.suffix.lower() in (".pdf", ".docx", ".txt", ".md"):
            testo = _leggi_file(p).strip()
            if not testo:
                continue
            intestazione = (
                f"---\ntitolo: {p.stem}\nambito: DA COMPILARE\nverificato: DA COMPILARE\n"
                f"prossima_verifica: DA COMPILARE\nfonti: materiale ricevuto, file originale {p.name}\n"
                f"affidabilita: DA COMPILARE\nlimiti: DA COMPILARE\nbozza: si\n---\n\n# {p.stem}\n\n"
            )
            (dest / f"{p.stem}.md").write_text(intestazione + testo, encoding="utf-8")
            print(f"creata bozza: {p.stem}.md")


if __name__ == "__main__":
    import sys
    K = Conoscenza(sys.argv[1] if len(sys.argv) > 1 else "ia/conoscenza")
    domanda = " ".join(sys.argv[2:]) or "livello italiano cittadinanza"
    print(K.contesto(domanda, k=3))
    if K.da_riverificare:
        print("\nDA RIVERIFICARE:", ", ".join(K.da_riverificare))
