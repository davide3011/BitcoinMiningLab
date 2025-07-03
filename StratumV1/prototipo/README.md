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

- La transazione coinbase viene generata esattamente come viene fatto in ckpool e segue il protocollo bitcoin.

- Introdotta la funzione swap_prevhash per invertire l'endianess con le stesse modalità studiate in ckpool (reverse engeneering) prima di inserirlo nel job.

### Problemi

La funzione 'build_coinbase_transaction' deve essere modificata affinché prende in input gli argomenti dello script-sig


    # <push(height)> OP_0
    # PUSH4(nTimeLE) 
    # PUSH4(bitsLE)
    # PUSH(len(ex1+ex2)) extranonce1 extranonce2
    # PUSH10("ckpool")   PUSHlen(msg)

- heigh viene presa dal template e non cambia: OK
- ntime deve essere passato in input
- bits devone essere passato in input
- ex1+ex gia presenti in input: OK
- pool_tag per ora harcodato: OK per fase di test/prototipazione

