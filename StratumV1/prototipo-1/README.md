# Server stratum V1

Prototipo in fase di sviluppo...

## Funzionamento

Il programma è in fase di prototipazione, e prevede 3 fasi:
1) creazione del job
2) comunicazione con il miner per inviare il job e ricevere la share
3) ricostruzione del blocco e invio al nodo

La prima fase è orchestrata da "main.py"
La seconda fase è orchestrada da "stratum_miner.py"
La terza fase è orchestrata da "sender.py"

## Note per lo sviluppo

Il modulo sender.py è in grado di ricostruire correttamente il blocco seguendo il protocollo. 
Il programma non funziona correttamente alle volte il blocco viene accettato altre viene rifiutato per high-hash: è presente un'imprecisione nella costruzione del job nel formato in cui vengono inseriti i dati.

### Problemi
- La transazione coinbase deve essere passata il miner come coinb1 e coinb2 nel formato legacy (ad ora viene passata in formato witness).

