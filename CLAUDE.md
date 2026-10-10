# kalimamedialab.com — istruzioni per Claude Code

## Il progetto
Sito pubblico di Kalima Media Lab: una pagina che presenta Arabita, Banglita, la scuola e i servizi.
Proprietario: Marco. Lavoriamo in italiano.

## Dov'è cosa
- Repo: `github.com/kalimamedialab/kalima-website`, branch `master`.
- In locale è clonato dentro il monorepo in `C:\dev\kalima\siti\kalima\website_pub\`, ma è un **repo git a sé**:
  il monorepo lo ignora. I commit di questo sito si fanno qui dentro.
- Non dipende da niente del monorepo (`shared/`, `database.py`, ecc.) e non ha database.
  L'unico legame con gli altri siti sono i feed RSS letti via HTTP:
  `https://arabita.news/rss.xml` e `https://banglita.news/rss.xml` (titoli «IT · AR/BN»).
- Deploy: servizio Railway collegato a questo repo. Avvio dal `Procfile`:
  `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60`. Python da `runtime.txt`.

## Struttura (oggi)
- `app.py` — Flask: route `/`, lettura dei due feed RSS.
- `templates/index.html` — tutta la pagina: HTML, CSS e JS. Le 20 lingue sono nell'oggetto JS `T`.
- `static/loghi/` — loghi PNG.

## Rifacimento in corso (piano approvato il 2026-10-10)
1. Testi in `traduzioni/<lingua>.json` (italiano = riferimento), elenco unico delle lingue `LINGUE` in `app.py`,
   URL per lingua `/<lingua>/` generate dal server, cookie `kalima_lingua`, hreflang, canonical, sitemap, robots.
2. Grafica nuova: CSS in file, proprietà logiche (RTL senza CSS a parte), font per alfabeto caricati solo per la lingua della pagina.
3. Lingue nuove: una riga in `LINGUE` + un file JSON (+ font se serve).
Lingue: le 20 di oggi.

## Regole
- Leggi un file per intero prima di modificarlo; mostra il diff prima di cambiare file esistenti.
- Un commit per modifica logica, messaggi in italiano.
- Mai `git push` senza conferma di Marco: il push su `master` va in produzione.
- Mai segreti nel repo.
- Non modificare i siti arabita e banglita da qui; se serve cambiare i loro feed RSS, se ne parla prima.
