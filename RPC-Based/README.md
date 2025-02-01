# Bitcoin Mining (RPC-Based)

Questo repository contiene uno script Python che implementa un miner di Bitcoin per testnet o regtest. L'obiettivo principale di questo progetto è didattico: vuole mostrare le basi del mining di Bitcoin su un nodo completo, senza l'uso di pool o hardware specializzato.

## 🎯 Scopo del progetto
Questo script è pensato per chi vuole comprendere il funzionamento del mining in modo chiaro e dettagliato. 

### 🔹 Cosa puoi imparare:
- Come un nodo Bitcoin fornisce un template di blocco per il mining.
- Come vengono costruiti i blocchi, a partire dalla transazione coinbase fino al Merkle Root.
- Il processo di hashing e la ricerca di un nonce valido per soddisfare la difficoltà richiesta.
- L'invio del blocco minato al nodo per la validazione.
- Le differenze tra mining in testnet e regtest per scopi di sviluppo e sperimentazione.

Questo progetto è utile per chiunque voglia approfondire il protocollo Bitcoin e il ruolo del mining nella sicurezza della rete. Non è pensato per il mining competitivo, ma come base per la comprensione del processo.

## 📌 Funzionalità principali
- Connessione al nodo Bitcoin tramite RPC
- Richiesta di un template di blocco con regole SegWit
- Creazione della coinbase transaction
- Calcolo del Merkle Root
- Costruzione dell'header del blocco
- Ricerca di un nonce valido per soddisfare la difficoltà del blocco
- Invio del blocco minato al nodo Bitcoin

## 🚀 Prerequisiti

### 1. Nodo Bitcoin
Assicurati di avere un nodo Bitcoin in esecuzione con il supporto per le chiamate RPC. Configura il file `bitcoin.conf` come segue:

#### 📄 Esempio di bitcoin.conf
```bash
regtest=1  # Se vuoi eseguire in regtest, altrimenti commenta questa linea
testnet4=1  # Se vuoi eseguire in testnet, altrimenti commenta questa linea
mainnet=1  #Se vuoi eseguire in mainnet, altrimenti commenta questa riga

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
pip install python-bitcoinrpc
```

## 🔧 Configurazione
Il file `miner.py` contiene i parametri di connessione RPC:
```python
RPC_USER = "tuo_utente"
RPC_PASSWORD = "tua_password"
RPC_HOST = "indirizzo_nodo"
RPC_PORT = "8332"
```
Modifica queste variabili in base alla configurazione del tuo nodo.

Inoltre, specifica l'indirizzo Bitcoin del miner per ricevere la ricompensa:
```python
MINER_ADDRESS = "indirizzo_bitcoin"
```

## 🏗️ Struttura dello script
Lo script è suddiviso nelle seguenti fasi:

### 1️⃣ Connessione al nodo Bitcoin
La funzione `test_rpc_connection()` verifica che la connessione RPC funzioni correttamente e stampa informazioni sulla blockchain.

### 2️⃣ Ottenere il template del blocco
La funzione `get_block_template()` richiede un template di blocco contenente transazioni e target di difficoltà.

### 3️⃣ Creazione della transazione coinbase
La funzione `build_coinbase_transaction(template)` crea la coinbase transaction che include la ricompensa per il miner.

### 4️⃣ Calcolo del Merkle Root
La funzione `calculate_merkle_root(coinbase_tx, transactions)` calcola la radice di Merkle per le transazioni del blocco.

### 5️⃣ Costruzione dell'header del blocco
La funzione `build_block_header()` crea l'intestazione del blocco concatenando versione, hash del blocco precedente, Merkle Root, timestamp, bits e nonce.

### 6️⃣ Mining del blocco
La funzione `mine_block(header_hex, target_hex)` trova un nonce che genera un hash inferiore al target richiesto dalla rete.

### 7️⃣ Invio del blocco
Dopo aver trovato un nonce valido, lo script:
1. Verifica la validità dell'header con `submit_block_header()`.
2. Serializza l'intero blocco con `serialize_block()`.
3. Invia il blocco al nodo Bitcoin con `submit_block()`.

## 📜 Esecuzione dello script
Per avviare il mining, esegui:
```bash
python miner.py
```
Se il mining ha successo, il blocco verrà inviato al nodo Bitcoin.

## 📌 Nota
Questo script può essere utilizzato sia per testnet che per regtest, a seconda della configurazione del nodo. Per implementare un miner più efficiente, considera l'uso del protocollo Stratum e hardware dedicato.

## 📜 Licenza
Questo progetto è open-source e disponibile sotto la licenza MIT.
