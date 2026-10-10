# kalimamedialab.com, istruzioni per Claude Code

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
- Deploy: servizio Railway collegato a questo repo, branch `master`; ogni push va online.
  Avvio dal `Procfile`: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60`. Python da `runtime.txt`.

## Struttura
- `app.py`: Flask. `LINGUE` (elenco unico delle lingue: nome nella propria lingua, direzione; la prima è la predefinita),
  `t('chiave')` per i testi, pagine `/<lingua>/`, `/` → lingua del cookie `kalima_lingua`, poi Accept-Language,
  poi italiano (302). `sitemap.xml`, `robots.txt`. Feed RSS con cache di 10 minuti.
- `traduzioni/<lingua>.json`: testi con chiavi a punti (`hero.tagline`, `servizi.1.titolo`…). `it.json` è il riferimento:
  le chiavi mancanti in una lingua si mostrano in inglese, e se mancano anche lì in italiano.
  `hero.tagline` = due frasi separate da `<br>`: la prima è il titolo, la seconda il sottotitolo.
- `templates/base.html` (testata, selettore delle lingue in un popover senza JavaScript, piede),
  `index.html` (home), `privacy.html`, `_email.html`.
- `static/css/sito.css`: tutto lo stile. Colori del logo: blu notte `#0A1D49`, ottanio `#00AFB8`, ambra `#FBB516`
  (l'ambra mai come colore di testo piccolo su bianco). Solo proprietà logiche (inline/block): arabo, urdu e farsi
  si specchiano da soli. Caratteri: famiglia Noto (latino, arabo, bengalese, devanagari, etiope, cinese, cirillico).
- `static/loghi/`: `kalima-media-lab.png` (logo, fondo trasparente), `kalima-media-lab-fondo.png` (lo stesso su fondo
  bianco arrotondato: è quello usato nella testata e per la scuola, perché resta visibile anche se il browser scurisce
  la pagina), `icona-512.png` (globo), `favicon-32.png`, `apple-touch-icon.png`, `og-kalima.png` (anteprima social
  1200×630), loghi di Arabita e Banglita. La pagina dichiara `color-scheme: only light` (niente tema scuro forzato).
- `/<lingua>/privacy/`: informativa (`privacy.*`), scritta in it ed en; le altre lingue mostrano l'inglese
  (blocco con lang/dir dell'inglese, pagina noindex). `/privacy` → lingua del visitatore.
- E-mail: mai in chiaro nell'HTML. `email('utente')` nei template e `{email}` nei testi (= info@)
  producono un link che `templates/_email.html` ricompone nel browser.
- `SITO` (canonical, hreflang, sitemap) = `https://www.kalimamedialab.com`: il dominio senza www oggi dà 403
  (record A del DNS non collegato al servizio Railway). Si cambia con la variabile `SITO_URL`.
- `controlla_traduzioni.py`: elenca le chiavi mancanti o in più per ogni lingua.
- Ricadute: una chiave mancante si mostra nella `ricaduta` della lingua (in `LINGUE`; wo → fr), poi in inglese, poi in italiano.
  `hreflang` in `LINGUE` quando diverso dal codice (pt = pt-BR, pubblico Brasile). x-default = `/en/`.
- Pagine dei servizi, tutte da `templates/servizio.html`, elenco in `PAGINE` (app.py): `/ong/` (IA per ONG e terzo settore),
  `/media-bilingue/`, `/materiali-didattici/`, `/comunicazione-multilingue/`. Testi in it, en, fr, es, pt, ar
  (chiavi `ong.*`, `media.*`, `materiali.*`, `comunicazione.*`); le altre lingue mostrano la ricaduta con noindex.
  Per una pagina nuova: una voce in `PAGINE` + le chiavi nei JSON. JSON-LD `Service`; la home ha `Organization`.
  Le schede servizi della home portano a queste pagine.
- Modulo di contatto (`templates/_modulo.html`, nella home e nella pagina ONG): POST `/<lingua>/contatto/` → `/<lingua>/grazie/`; il tema è preselezionato secondo la pagina.
  Anti-spam: campo trappola `sito`, almeno 3 secondi, 5 invii l'ora per IP. Il messaggio non si salva: `contatti.py` in un thread
  chiede a Claude (`claude-opus-5-5`, fallbacks "default") risposta + resoconto, manda la risposta a chi ha scritto e il resoconto
  a `RESOCONTI_A`. Senza chiave o con errore: messaggio fisso tradotto (`email.oggetto`, `email.testo`).
  **`ia/linee_guida.md`** = le linee guida di Marco per le risposte (le regole fisse stanno in `contatti.py`).
  Variabili Railway: `ANTHROPIC_API_KEY`, `RESOCONTI_A`, `MAIL_MITTENTE`, e `RESEND_API_KEY` oppure `SMTP_HOST/PORT/UTENTE/PASSWORD`.

## Rifacimento (piano approvato il 2026-10-10)
1. FATTO: testi in JSON, URL per lingua, cookie, hreflang, canonical, sitemap, robots, privacy.
2. FATTO: grafica nuova (logo del 2026-10-10, nessuna bandiera, scuola con turismo, business, gruppi).
3. FATTO (2026-10-10): 26 lingue; aggiunte de, pl, lv, th, ja, si (singalese per lo Sri Lanka).
4. Da fare: revisione delle traduzioni da madrelingua (wolof; singalese, thai, lettone appena aggiunti);
   tigrino e wolof senza i testi nuovi, ora in inglese; privacy solo it ed en.
5. Lingue nuove: una riga in `LINGUE` + un file JSON (+ la famiglia Noto in `base.html` e `--font` se è un alfabeto nuovo).
6. Dominio senza www: su Hostinger c'è `domains/kalimamedialab.com/public_html/.htaccess` con il 301 verso www;
   funziona quando il record A di `kalimamedialab.com` nel DNS di Hostinger punta al server 147.93.88.185.

## Regole sui testi
- **Mai il trattino lungo (—)** nei testi visibili, in nessuna lingua: al suo posto un punto o una virgola, secondo la frase,
  con la punteggiatura della lingua (virgola araba «،», cinese «，», etiope «፣»; punto cinese «。», danda «।» per hindi
  e bengalese, «።» etiope). Nei titoli delle pagine: « · ».
- Nessun «Lavora con noi»: Marco non cerca collaboratori. Il pulsante giusto è per chi vuole un lavoro fatto da noi
  («Parliamo del tuo progetto», che porta ai contatti).

## Regole
- Leggi un file per intero prima di modificarlo; mostra il diff prima di cambiare file esistenti.
- Un commit per modifica logica, messaggi in italiano.
- Mai `git push` senza conferma di Marco: il push su `master` va in produzione.
- Mai segreti nel repo.
- Non modificare i siti arabita e banglita da qui; se serve cambiare i loro feed RSS, se ne parla prima.
