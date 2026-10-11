# Base di conoscenza di Kalima: come funziona

Questa cartella contiene le informazioni che il risponditore può condividere. Le linee guida (`linee_guida.md`) dicono COME rispondere. Questa cartella dice COSA si sa.

## Regole della cartella

1. Ogni file ha in testa una scheda: ambito, data di verifica, fonti, limiti.
2. Un fatto entra solo se ha una fonte ufficiale o una fonte che Kalima conosce direttamente (materiale ricevuto da un'organizzazione, esperienza di insegnamento).
3. Ogni file va riverificato almeno ogni sei mesi. La data di verifica è nella scheda.
4. Ciò che non è verificato si scrive come «da verificare» oppure non si scrive.
5. Il risponditore condivide le informazioni generali. Non valuta mai il caso personale di chi scrive.

## Formula standard di verifica

Ogni risposta che riporta un fatto normativo, procedurale o di finanziamento termina con l'idea che le informazioni vanno controllate presso l'ente competente prima di decidere. Esempi di formula:
- «Le norme e le procedure cambiano: prima di decidere, controlla sempre con l'ente competente.»
- «Questa è un'informazione generale: per il tuo caso conferma con l'ente che rilascia il documento.»

## Come aggiungere nuovi materiali (PDF, Word, appunti)

1. Metti il file originale nella cartella `fonti_originali/` (non viene letto dal risponditore).
2. Crea un file `.md` in questa cartella con la scheda in testa (vedi il modello sotto) e il contenuto riassunto con parole proprie.
3. Per materiali ricevuti da altre organizzazioni: chiedi il permesso di usarne il contenuto, togli nomi di persone e dati riservati, indica nella scheda che la fonte è «materiale ricevuto da un'organizzazione partner» e la data.
4. Mai copiare testi protetti da diritto d'autore per intero: si riassume e si indica la fonte.
5. Il modulo `conoscenza.py` converte e legge PDF e Word in automatico, ma un riassunto scritto a mano è sempre più affidabile.

## Modello di scheda

```
---
titolo: ...
ambito: ...
verificato: AAAA-MM-GG
prossima_verifica: AAAA-MM-GG
fonti: elenco di enti e indirizzi
affidabilita: ufficiale | secondaria | esperienza diretta
limiti: cosa il file NON copre
---
```

## Elenco dei file

- 01 Certificazioni di italiano L2 e enti certificatori
- 02 Requisiti linguistici per soggiorno e cittadinanza
- 03 Cittadini UE e non UE: differenze che contano per la lingua
- 04 Professioni sanitarie e lingua italiana
- 05 Scuola pubblica, CPIA e percorsi di formazione
- 06 Didattica dell'italiano L2
- 07 ONG: enti finanziatori e fonti di bandi
- 08 Quadro normativo e standard etici per le organizzazioni
- 09 Come si legge e si prepara un bando
- 10 Formazione e risorse gratuite per associazioni
