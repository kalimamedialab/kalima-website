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

## Struttura
- `app.py` — Flask. `LINGUE` (elenco unico delle lingue: bandiera, etichetta, direzione; la prima è la predefinita),
  `t('chiave')` per i testi, pagine `/<lingua>/`, `/` → lingua del cookie `kalima_lingua`, poi Accept-Language,
  poi italiano (302). `sitemap.xml`, `robots.txt`. Feed RSS con cache di 10 minuti.
- `traduzioni/<lingua>.json` — testi con chiavi a punti (`hero.tagline`, `servizi.1.titolo`…). `it.json` è il riferimento:
  le chiavi mancanti in una lingua si mostrano in inglese, e se mancano anche lì in italiano.
- `/<lingua>/privacy/` — informativa (`privacy.*`), scritta in it ed en; le altre lingue mostrano l'inglese
  (blocco con lang/dir dell'inglese, pagina noindex). `/privacy` → lingua del visitatore.
- E-mail: mai in chiaro nell'HTML. `email('utente')` nei template e `{email}` nei testi (= info@)
  producono un link che `templates/_email.html` ricompone nel browser.
- `SITO` (canonical, hreflang, sitemap) = `https://www.kalimamedialab.com`: il dominio senza www oggi dà 403
  (record A del DNS non collegato al servizio Railway). Si cambia con la variabile `SITO_URL`.
- `controlla_traduzioni.py` — elenca le chiavi mancanti o in più per ogni lingua.
- `templates/index.html` — la pagina (HTML e CSS); i testi vengono da `t()`.
- `static/loghi/` — loghi PNG.

## Rifacimento in corso (piano approvato il 2026-10-10)
1. FATTO (2026-10-10): testi in `traduzioni/<lingua>.json`, `LINGUE` in `app.py`, URL `/<lingua>/`, cookie,
   hreflang, canonical, sitemap, robots. Da fare: revisione delle traduzioni (wolof, testi accorciati).
2. Grafica nuova: CSS in file, proprietà logiche (RTL senza CSS a parte), font per alfabeto caricati solo per la lingua della pagina.
3. Lingue nuove: una riga in `LINGUE` + un file JSON (+ font se serve).
Lingue: le 20 di oggi.

## Regole
- Leggi un file per intero prima di modificarlo; mostra il diff prima di cambiare file esistenti.
- Un commit per modifica logica, messaggi in italiano.
- Mai `git push` senza conferma di Marco: il push su `master` va in produzione.
- Mai segreti nel repo.
- Non modificare i siti arabita e banglita da qui; se serve cambiare i loro feed RSS, se ne parla prima.
