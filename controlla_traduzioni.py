"""
Controlla i file traduzioni/<lingua>.json rispetto all'italiano (il riferimento).

    python controlla_traduzioni.py

Per ogni lingua di LINGUE (app.py) elenca le chiavi mancanti, che sul sito ricadono
sull'italiano, e le chiavi in più che l'italiano non ha (errori di battitura).
Esce con 1 se ci sono chiavi in più o file mancanti.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import LINGUE, PREDEFINITA  # noqa: E402

CARTELLA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'traduzioni')


def carica(codice):
    with open(os.path.join(CARTELLA, f'{codice}.json'), encoding='utf-8') as f:
        return json.load(f)


riferimento = carica(PREDEFINITA)
errori = 0
for codice in LINGUE:
    if codice == PREDEFINITA:
        continue
    try:
        testi = carica(codice)
    except FileNotFoundError:
        print(f'{codice}: FILE MANCANTE')
        errori += 1
        continue
    mancanti = [k for k in riferimento if k not in testi]
    in_piu = [k for k in testi if k not in riferimento]
    stato = 'completo' if not mancanti else f'{len(mancanti)} mancanti (in italiano): {", ".join(mancanti)}'
    print(f'{codice}: {stato}')
    if in_piu:
        print(f'   chiavi in più, non esistono in {PREDEFINITA}: {", ".join(in_piu)}')
        errori += 1

print(f'\n{len(riferimento)} chiavi in {PREDEFINITA}.json')
sys.exit(1 if errori else 0)
