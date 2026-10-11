"""
archivio.py - archivio dei messaggi del modulo di contatto, da studiare in seguito.

Cosa conserva
- sempre: la classificazione (tipo di mittente, tema, lingua, priorità, scadenza, lacune di conoscenza...)
  e una sintesi senza nomi;
- per un periodo limitato: il testo originale e la risposta inviata (poi vengono cancellati da `pulisci()`);
- l'indirizzo email NON viene salvato: solo un'impronta (hash con la chiave segreta ARCHIVIO_CHIAVE, che sta solo su Railway), utile per riconoscere chi
  riscrive e per cancellare i dati se qualcuno lo chiede.

Database: PostgreSQL se esiste ARCHIVIO_DATABASE_URL (o, in mancanza, DATABASE_URL), altrimenti un file SQLite locale.
La tabella si chiama `contatti_archivio`, per non scontrarsi con tabelle già presenti nel database del sito.
Per PostgreSQL serve `pip install psycopg2-binary`.

Uso minimo in contatti.py:
    from archivio import Archivio
    A = Archivio()                                   # una volta all'avvio
    A.registra(lingua="fr", tipo_mittente="organizzazione non profit", tema="bandi_finanziatori",
               priorita="alta", scadenza_dichiarata="30 novembre", richiesta_sintesi="aiuto per un bando",
               email=email, testo_originale=testo, risposta=risposta)
    A.pulisci()                                      # una volta al giorno
    print(A.report())                                # per studiare
"""
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import threading
from datetime import datetime, timedelta, timezone

CAMPI = ["lingua", "tipo_mittente", "tema", "priorita", "motivo_priorita", "scadenza_dichiarata", "ambito",
         "richiesta_sintesi", "schede_usate", "lacuna_conoscenza", "spam", "manipolazione", "urgenza", "ostilita"]


class Archivio:
    def __init__(self, percorso_sqlite="archivio_messaggi.sqlite3"):
        self.url = os.environ.get("ARCHIVIO_DATABASE_URL") or os.environ.get("DATABASE_URL")
        self._lock = threading.Lock()  # contatti.py lavora in più thread sulla stessa connessione
        chiave = os.environ.get("ARCHIVIO_CHIAVE", "")
        if len(chiave) >= 16:
            self.chiave = chiave.encode()
            print("[archivio] chiave configurata")
        else:
            self.chiave = None
            print("[archivio] ATTENZIONE: ARCHIVIO_CHIAVE mancante o troppo corta (meno di 16 caratteri): "
                  "le email non vengono registrate nemmeno come impronta")
        if self.url:
            import psycopg2  # type: ignore
            self.con = psycopg2.connect(self.url)
            self.ph = "%s"
            tipo_id = "SERIAL PRIMARY KEY"
        else:
            self.con = sqlite3.connect(percorso_sqlite, check_same_thread=False)
            self.ph = "?"
            tipo_id = "INTEGER PRIMARY KEY AUTOINCREMENT"
        self._esegui(f"""CREATE TABLE IF NOT EXISTS contatti_archivio (
            id {tipo_id}, ricevuto_il TEXT, {", ".join(c + " TEXT" for c in CAMPI)},
            email_hash TEXT, testo_originale TEXT, risposta_inviata TEXT, elimina_dopo TEXT,
            stato TEXT, token TEXT, scade_il TEXT, contesto_json TEXT)""")

    def _esegui(self, sql, params=()):
        with self._lock:
            try:
                cur = self.con.cursor()
                cur.execute(sql, params)
                self.con.commit()
                return cur
            except Exception:
                try:
                    self.con.rollback()
                except Exception:
                    pass
                raise

    def _hash(self, email):
        if not email or not self.chiave:
            return None
        return hmac.new(self.chiave, email.strip().lower().encode(), hashlib.sha256).hexdigest()

    def registra(self, email=None, testo_originale=None, risposta=None, conserva_giorni=365,
                 stato="completato", token=None, attesa_giorni=None, contesto=None, **campi):
        """Salva una riga. stato: completato | in_attesa | scaduto | ignorato.
        Per i messaggi ignorati (spam, fornitori) passa testo_originale=None: resta solo la classificazione."""
        adesso = datetime.now(timezone.utc)
        valori = [str(campi.get(c, "") or "") for c in CAMPI]
        scade = (adesso + timedelta(days=attesa_giorni)).isoformat() if attesa_giorni else None
        sql = (f"INSERT INTO contatti_archivio (ricevuto_il, {', '.join(CAMPI)}, email_hash, testo_originale, risposta_inviata, "
               f"elimina_dopo, stato, token, scade_il, contesto_json) VALUES ({', '.join([self.ph] * (len(CAMPI) + 9))})")
        self._esegui(sql, [adesso.isoformat(), *valori, self._hash(email), testo_originale, risposta,
                           (adesso + timedelta(days=conserva_giorni)).isoformat(), stato, token, scade,
                           json.dumps(contesto) if contesto else None])

    def in_attesa(self, email=None, testo_originale=None, risposta=None, attesa_giorni=7, contesto=None, **campi):
        """Messaggio troppo vago: risposto con 1-2 domande, resoconto NON ancora inviato.
        Restituisce un token da mettere nel link/indirizzo di risposta."""
        token = secrets.token_urlsafe(16)
        self.registra(email=email, testo_originale=testo_originale, risposta=risposta, stato="in_attesa",
                      token=token, attesa_giorni=attesa_giorni, contesto=contesto, **campi)
        return token

    def riprendi(self, token, testo_aggiuntivo):
        """Chi aveva ricevuto le domande risponde. Restituisce (testo completo, contesto) da rimandare al modello
        grande, oppure None se il token non è valido o è scaduto. Dopo la lettura il testo e il contesto
        (nome, email, ecc.) vengono cancellati dall'archivio: restano solo i campi di classificazione."""
        riga = self._esegui(f"SELECT id, testo_originale, contesto_json FROM contatti_archivio WHERE token = {self.ph} "
                            f"AND stato = 'in_attesa' AND scade_il >= {self.ph}",
                            (token, datetime.now(timezone.utc).isoformat())).fetchone()
        if not riga:
            return None
        self._esegui(f"UPDATE contatti_archivio SET stato = 'completato', testo_originale = NULL, contesto_json = NULL, "
                     f"token = NULL WHERE id = {self.ph}", (riga[0],))
        completo = f"{riga[1] or ''}\n\nRISPOSTA ALLE DOMANDE DI APPROFONDIMENTO:\n{testo_aggiuntivo}"
        return completo, (json.loads(riga[2]) if riga[2] else {})

    def chiudi_scaduti(self):
        """Messaggi vaghi senza risposta oltre il termine: nessun resoconto, restano solo nel report settimanale.
        Restituisce quanti ne ha chiusi."""
        cur = self._esegui(f"UPDATE contatti_archivio SET stato = 'scaduto', testo_originale = NULL, contesto_json = NULL, "
                           f"token = NULL WHERE stato = 'in_attesa' AND scade_il < {self.ph}",
                           (datetime.now(timezone.utc).isoformat(),))
        return cur.rowcount

    def pulisci(self):
        """Cancella testo originale e risposta quando scade il periodo di conservazione. Resta la classificazione."""
        adesso = datetime.now(timezone.utc).isoformat()
        self._esegui(f"UPDATE contatti_archivio SET testo_originale = NULL, risposta_inviata = NULL "
                     f"WHERE elimina_dopo < {self.ph} AND (testo_originale IS NOT NULL OR risposta_inviata IS NOT NULL)", (adesso,))

    def cancella_per_email(self, email):
        """Per richieste di cancellazione dati: elimina le righe collegate a quell'indirizzo."""
        impronta = self._hash(email)
        if not impronta:
            print("[archivio] impossibile cancellare per email: manca la chiave o l'indirizzo")
            return 0
        return self._esegui(f"DELETE FROM contatti_archivio WHERE email_hash = {self.ph}", (impronta,)).rowcount

    def elenco(self, tema=None, stato=None, giorni=7):
        """Righe recenti (data, tema, lingua, sintesi): per il digest, per esempio le candidature della settimana."""
        sql = "SELECT ricevuto_il, tema, lingua, richiesta_sintesi, stato FROM contatti_archivio WHERE ricevuto_il >= " + self.ph
        params = [(datetime.now(timezone.utc) - timedelta(days=giorni)).isoformat()]
        if tema:
            sql += f" AND tema = {self.ph}"
            params.append(tema)
        if stato:
            sql += f" AND stato = {self.ph}"
            params.append(stato)
        return self._esegui(sql + " ORDER BY ricevuto_il DESC", params).fetchall()

    def _conta(self, colonna, giorni=None):
        sql = f"SELECT {colonna}, COUNT(*) FROM contatti_archivio"
        params = []
        if giorni:
            sql += f" WHERE ricevuto_il >= {self.ph}"
            params.append((datetime.now(timezone.utc) - timedelta(days=giorni)).isoformat())
        sql += f" GROUP BY {colonna} ORDER BY COUNT(*) DESC"
        return self._esegui(sql, params).fetchall()

    def report(self, giorni=None):
        """Riepilogo da leggere: quanti messaggi per tema, lingua, tipo, priorità e quali lacune di conoscenza."""
        out = []
        for col in ("stato", "tema", "lingua", "tipo_mittente", "priorita"):
            out.append(f"{col}: " + ", ".join(f"{v or '(vuoto)'} {n}" for v, n in self._conta(col, giorni)))
        lacune = self._esegui("SELECT lacuna_conoscenza, COUNT(*) FROM contatti_archivio WHERE lacuna_conoscenza <> '' "
                              "GROUP BY lacuna_conoscenza ORDER BY COUNT(*) DESC").fetchall()
        out.append("lacune di conoscenza: " + (", ".join(f"{v} ({n})" for v, n in lacune) or "nessuna"))
        return "\n".join(out)


if __name__ == "__main__":
    import tempfile
    os.environ.setdefault("ARCHIVIO_CHIAVE", "chiave-di-prova-solo-per-il-test")
    d = os.path.join(tempfile.mkdtemp(), "t.sqlite3")
    A = Archivio(d)
    A.registra(lingua="fr", tipo_mittente="associazione", tema="bandi_finanziatori", priorita="alta",
               scadenza_dichiarata="30 novembre", lacuna_conoscenza="finanziatori nazionali francesi",
               email="ong@example.org", testo_originale="testo", risposta="risposta", conserva_giorni=-1)
    A.registra(tema="spam", stato="ignorato", lingua="en")
    t = A.in_attesa(email="x@y.it", testo_originale="Vorrei informazioni", risposta="Per chi serve?", lingua="it",
                    contesto={"nome": "Anna", "email": "x@y.it"})
    print("riprendi:", A.riprendi(t, "Per un gruppo di 10 persone, livello A2"))
    print("riprendi di nuovo:", A.riprendi(t, "altro"))
    A.in_attesa(email="z@y.it", testo_originale="Ciao", attesa_giorni=-1, contesto={"nome": "Z"})
    print("scaduti chiusi:", A.chiudi_scaduti())
    A.pulisci()
    print(A.report())
    print(A.elenco(tema="spam"))
