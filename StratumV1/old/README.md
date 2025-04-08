# Stratum Mining Client

Questo progetto è un client di mining Stratum scritto in Python. Si connette a un pool di mining, riceve job di mining e cerca il nonce corretto per risolvere i blocchi.

**PROGRAMMA IN FASE DI SVILUPPO!** 

## Struttura del progetto

Il progetto è composto dai seguenti file principali:

```start.py```  Avvia il client Stratum e il miner.

```stratum_client.py```  Gestisce la connessione con il pool, la sottoscrizione (mining.subscribe), l'autenticazione (mining.authorize) e la ricezione dei job (mining.notify).

```miner.py``` Legge i job ricevuti, esegue il mining e invia le share trovate al pool.

```conf.json```  File di configurazione contenente i parametri del pool e del miner.

```job.json```  Viene creato durante l'esecuzione del programma e contiene i dettagli dell'ultimo job ricevuto per l'elaborazione del mining.

## Configurazione

Modifica il file conf.json per inserire i dati del pool e del miner:
```bash
{
    "pool_host": "stratum+tcp://your-pool-url.com",
    "pool_port": 3333,
    "username": "your_worker_name",
    "worker": "your_worker",
    "password": "x"
}
```

## Come avviare il mining

Assicurati di avere Python installato.

Avvia il mining eseguendo:

```python start.py```

## Funzionamento del programma

### 1. Connessione al pool

Lo script stratum_client.py si connette al pool e invia le seguenti richieste:

mining.subscribe - Registra il miner presso il pool.

mining.authorize - Autentica il miner con il pool.

mining.notify - Riceve nuovi job di mining.

### 2. Ricezione e gestione dei job

Quando un nuovo job viene ricevuto, i dati vengono salvati in job.json e il miner inizia a calcolare i nonce.

### 3. Calcolo del nonce e invio delle share

Il file miner.py legge job.json, costruisce l'header del blocco e calcola l'hash. Se l'hash è inferiore al target, viene inviato al pool con mining.submit.

## Possibili problemi e soluzioni

Errore di connessione al pool - Controllare pool_host e pool_port in conf.json.

Autenticazione fallita - Verificare username e password in conf.json.

Il miner non invia share - Assicurarsi che miner.py sia in esecuzione e che il target sia configurato correttamente.
