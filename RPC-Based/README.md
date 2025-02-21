# Bitcoin Mining (RPC-Based)

Questo repository contiene diversi script Python che implementano un semplice miner Bitcoin per testnet e regtest. L'obiettivo principale di questo progetto rimane didattico, con uno script dettagliato che permette di comprendere a fondo le basi del mining step per step e una versione ottimizzata per esplorare miglioramenti di efficienza.

Questi script sono pensati per chi vuole comprendere il funzionamento del mining in modo chiaro e dettagliato.

## Cosa puoi imparare:

- Come un nodo Bitcoin fornisce un template di blocco per il mining.

- Come vengono costruiti i blocchi, a partire dalla transazione coinbase fino al Merkle Root.

- Il processo di hashing e la ricerca di un nonce valido per soddisfare la difficoltà richiesta.

- L'invio del blocco minato al nodo per la validazione.

- Le differenze tra mining in testnet e regtest per scopi di sviluppo e sperimentazione.

Questo progetto non è pensato per il mining competitivo, ma come base per la comprensione del processo.

## Struttura degli script

Il repository contiene i seguenti file principali:

**```miner_regtest.py```:** Script didattico che permette di comprendere passo per passo ogni fase del processo di mining. Supporta la modifica della difficoltà tramite il parametro difficulty_factor, permettendo di simulare condizioni di mining più impegnative.

**```miner_opt.py```:** Una versione ottimizzata del miner per testare un'implementazione più snella ed efficiente. Può essere utilizzata anche in Testnet, fornendo un ambiente di test più realistico rispetto a Regtest.

**```conf.json```:** File per l'inserimento dei parametri RPC del proprio nodo e l'indirizzo di destinazione della coinbase transaction per ```miner_opt.py```.

## Funzioni principali

Entrambi gli script seguono lo stesso flusso base ma con alcune differenze.
Ecco le fasi principali comuni:

### 1️⃣ Connessione al nodo Bitcoin

La funzione ```test_rpc_connection()``` verifica che la connessione RPC funzioni correttamente e stampa informazioni sulla blockchain.

### 2️⃣ Ottenere il template del blocco

La funzione ```get_block_template()``` richiede un template di blocco contenente transazioni e target di difficoltà.

### 3️⃣ Creazione della transazione coinbase

La funzione ```build_coinbase_transaction(template)``` crea la coinbase transaction che include la ricompensa per il miner.

### 4️⃣ Calcolo del Merkle Root

La funzione ```calculate_merkle_root(coinbase_tx, transactions)``` calcola la radice di Merkle per le transazioni del blocco.

### 5️⃣ Costruzione dell'header del blocco

La funzione ```build_block_header()``` crea l'intestazione del blocco concatenando:
- Versione del blocco
- Hash del blocco precedente
- Merkle Root
- Timestamp
- Bits (difficoltà)
- Nonce

### 6️⃣ Mining del blocco (con scelta del metodo di elaborazione del nonce)

Lo script offre tre diverse modalità per generare il nonce, il valore che viene iterato per trovare un hash valido inferiore al target di difficoltà.
Ogni metodo ha vantaggi e svantaggi in termini di efficienza computazionale e probabilità di successo.

| Metodo                                    | Vantaggi                                                                 | Svantaggi                                                                 |
|-------------------------------------------|-------------------------------------------------------------------------|---------------------------------------------------------------------------|
| **Incrementale (da 0 a 2³² - 1)**         | Esplora tutti i nonce in modo sistematico e sequenziale. Garantisce che nessun valore venga saltato. | Può essere prevedibile e meno efficace se il target è molto basso. Tutti i miner che usano questo metodo in parallelo potrebbero generare collisioni sui nonce. |
| **Casuale (ogni iterazione un nonce randomico)** | Buona distribuzione casuale, utile per ambienti distribuiti e per evitare collisioni tra più miner. | Possibilità di ripetere nonce già testati, riducendo l’efficienza a lungo termine. |
| **Misto (primo nonce casuale, poi incremento)** | Combina il vantaggio della casualità iniziale con la sistematicità dell’incremento. Utile per diversificare l’output in ambienti paralleli. | Se la ricerca inizia in una zona sfavorevole dello spazio dei nonce, potrebbe richiedere più tempo per trovare un hash valido. |

### 7️⃣ Serializzazione del blocco
La funzione ```serialize_block()``` genera la versione completa e validata del blocco, pronta per essere inviata al nodo Bitcoin.
Il blocco include:

- Header serializzato
- Numero totale di transazioni
- Coinbase transaction
- Transazioni della mempool

### 8️⃣ Invio del blocco

Dopo aver trovato un nonce valido, lo script invia il blocco al nodo Bitcoin con ```submit_block()```.

## Prerequisiti

### 1. Nodo Bitcoin

Assicurati di avere un nodo Bitcoin in esecuzione con il supporto per le chiamate RPC. Configura il file bitcoin.conf come segue:

#### Esempio di bitcoin.conf
```
regtest=1  # Se vuoi eseguire in regtest, altrimenti commenta questa linea
testnet4=1  # Se vuoi eseguire in testnet, altrimenti commenta questa linea
mainnet=1  # Se vuoi eseguire in mainnet, altrimenti commenta questa linea

server=1
rpcuser=tuo_utente
rpcpassword=tua_password
rpcallowip=127.0.0.1  #  192.168.1.x altrimenti
rpcport=8332
```

Avvia il nodo e aspetta che si configuri completamente.

### 2. Dipendenze Python

Installa i moduli richiesti eseguendo:
```bash
pip install -r requirements.txt
```
## Configurazione

Lo script miner_regtest.py e miner_opt.py utilizzano lo stesso file di configurazione, conf.json, per impostare i parametri di connessione RPC, l'indirizzo per ricevere la ricompensa del blocco e, nel caso di Regtest, la difficoltà personalizzata.

Nota: Il parametro difficulty_factor viene utilizzato solo in Regtest per simulare ambienti più difficili. Se esegui il miner su Testnet con miner_opt.py, questo parametro verrà ignorato.

Per eseguire miner_regtest.py o miner_opt.py, è necessario modificare il file ```conf.json```:

```bash
{
    "rpcuser": "tuo_utente",
    "rpcpassword": "tua_password",
    "rpcport": 8332,
    "rpcaddress": "indirizzo_nodo",
    "wallet_address": "indirizzo_bitcoin",
    "difficulty_factor": 2.0,
    "nonce_mode": "mixed"
}
```

| Parametro          | Descrizione                                                                                      |
|--------------------|------------------------------------------------------------------------------------------------|
| **rpcuser**        | Nome utente RPC configurato nel file `bitcoin.conf`.                                            |
| **rpcpassword**    | Password RPC configurata nel file `bitcoin.conf`.                                               |
| **rpcport**        | Porta per la connessione RPC (modificarla in base alla configurazione del nodo).                |
| **rpcaddress**     | Indirizzo del nodo Bitcoin RPC (es. `127.0.0.1` per connessioni locali).                        |
| **wallet_address** | Indirizzo Bitcoin in cui verrà inviata la ricompensa della **coinbase transaction**.            |
| **difficulty_factor** | Modifica la difficoltà del mining in **Regtest** moltiplicando il target originale (**⚠️ Ignorato in Testnet**). |
| **nonce_mode**     | Metodo di elaborazione del nonce: `"incremental"`, `"random"` o `"mixed"` (vedi descrizione sopra). |


## Esecuzione degli script

Per avviare il miner con debug attivato:

```
python miner_regtest.py
```

Per avviare la versione ottimizzata senza debug, dopo aver modificato il file ```conf.json```:

```
python miner_opt.py
```

## Nota

Questi script possono essere utilizzati sia per testnet che per regtest, a seconda della configurazione del nodo. Per implementare un miner più efficiente, considera l'uso del protocollo Stratum e hardware dedicato.

## Licenza

Questo progetto è open-source e disponibile sotto la licenza MIT.
