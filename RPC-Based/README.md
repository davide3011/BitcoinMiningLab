# Bitcoin Mining (RPC-Based)

Questo repository contiene diversi script Python che implementano un miner di Bitcoin per testnet o regtest. L'obiettivo principale di questo progetto rimane didattico, con uno script dettagliato che permette di comprendere le basi del mining, e versioni ottimizzate per esplorare miglioramenti di efficienza.

## 🎯 Scopo del progetto

Questi script sono pensati per chi vuole comprendere il funzionamento del mining in modo chiaro e dettagliato.

## 🔹 Cosa puoi imparare:

- Come un nodo Bitcoin fornisce un template di blocco per il mining.

- Come vengono costruiti i blocchi, a partire dalla transazione coinbase fino al Merkle Root.

- Il processo di hashing e la ricerca di un nonce valido per soddisfare la difficoltà richiesta.

- L'invio del blocco minato al nodo per la validazione.

- Le differenze tra mining in testnet e regtest per scopi di sviluppo e sperimentazione.

Questo progetto è utile per chiunque voglia approfondire il protocollo Bitcoin e il ruolo del mining nella sicurezza della rete. Non è pensato per il mining competitivo, ma come base per la comprensione del processo.

## 📌 Struttura degli script

Il repository contiene i seguenti file principali:

**miner_debug.py:** Script didattico che permette di comprendere passo per passo ogni fase del processo di mining. Contiene numerosi punti di debug utili per studiare il flusso del programma e analizzare i dati intermedi.

**miner_opt.py:** Una versione ottimizzata del miner, senza i punti di debug, per testare un'implementazione più snella ed efficiente.

## 🏗️ Funzioni principali

Entrambi gli script seguono lo stesso flusso base ma con differenze in termini di ottimizzazione e debug.
Ecco le fasi principali comuni:

### 1️⃣ Connessione al nodo Bitcoin

La funzione test_rpc_connection() verifica che la connessione RPC funzioni correttamente e stampa informazioni sulla blockchain.

### 2️⃣ Ottenere il template del blocco

La funzione get_block_template() richiede un template di blocco contenente transazioni e target di difficoltà.

### 3️⃣ Creazione della transazione coinbase

La funzione build_coinbase_transaction(template) crea la coinbase transaction che include la ricompensa per il miner.

### 4️⃣ Calcolo del Merkle Root

La funzione calculate_merkle_root(coinbase_tx, transactions) calcola la radice di Merkle per le transazioni del blocco.

### 5️⃣ Costruzione dell'header del blocco

La funzione build_block_header() crea l'intestazione del blocco concatenando versione, hash del blocco precedente, Merkle Root, timestamp, bits e nonce.

### 6️⃣ Mining del blocco (con scelta del metodo di elaborazione del nonce)

Nella versione ottimizzata è possibile scegliere tra due modalità per elaborare i nonce:

#### Progressiva 
Esplora i nonce in maniera incrementale, partendo da zero e avanzando di 1 fino al valore massimo possibile.

Per questa versione rimuovere la funzione ```def mine_block(header_hex, target_hex):``` e sostituisci la seguente funzione:

```bash
def mine_block(header_hex, target_hex):
    """Esegue il mining cercando un nonce che soddisfi l'hash < target."""
    print("\n=== STEP 7: Inizio del Mining ===")
    print("\n?? Iniziando il mining...")

    nonce = 0
    target = int(target_hex, 16)
    base_header = unhexlify(header_hex[:152])  # Converti solo la parte fissa dell'header una volta

    while nonce <= 0xFFFFFFFF:
        # Aggiorna i 4 byte finali del nonce
        full_header = base_header + struct.pack("<I", nonce)
        block_hash = double_sha256(full_header)[::-1].hex()

        if nonce % 100000 == 0:
            print(f"?? Nonce: {nonce} | Hash: {block_hash}")

        if int(block_hash, 16) < target:
            print(f"\n? Blocco trovato! ??")
            print(f"?? Nonce valido: {nonce}")
            print(f"?? Hash del blocco: {block_hash}")
            return hexlify(full_header).decode(), nonce

        nonce += 1

    print("\n? Non è stato trovato un hash valido.")
    return None, None
```

#### Casuale
Seleziona i nonce casualmente ad ogni iterazione, utile per simulare un approccio distribuito.

Per questa versione rimuovere la funzione ```def mine_block(header_hex, target_hex):``` e sostituisci la seguente funzione:

```bash
import random

def mine_block(header_hex, target_hex):
    """Esegue il mining cercando un nonce casuale e stampa il progresso ogni 100.000 tentativi."""
    print("\n=== STEP 7: Inizio del Mining ===")
    print("\n?? Iniziando il mining con nonce randomico...")

    target = int(target_hex, 16)
    base_header = unhexlify(header_hex[:152])  # Converti solo la parte fissa dell'header una volta
    attempts = 0  # Contatore tentativi

    while True:
        # Genera un nonce casuale tra 0 e 2^32 - 1
        nonce = random.randint(0, 0xFFFFFFFF)

        # Aggiorna i 4 byte finali del nonce
        full_header = base_header + struct.pack("<I", nonce)
        block_hash = double_sha256(full_header)[::-1].hex()

        # Aggiorna il contatore dei tentativi
        attempts += 1

        # Stampa i progressi ogni 100.000 tentativi
        if attempts % 100000 == 0:
            print(f"?? Tentativi: {attempts:,} | Ultimo nonce testato: {nonce} | Hash: {block_hash}")

        # Controlla se il nonce trovato è valido
        if int(block_hash, 16) < target:
            print(f"\n? Blocco trovato! ??")
            print(f"?? Nonce valido: {nonce}")
            print(f"?? Hash del blocco: {block_hash}")
            print(f"?? Tentativi totali: {attempts:,}")
            return hexlify(full_header).decode(), nonce
```

### 7️⃣ Invio del blocco

Dopo aver trovato un nonce valido, lo script:

Verifica la validità dell'header con ```submit_block_header()```.

Serializza l'intero blocco con ```serialize_block()```.

Invia il blocco al nodo Bitcoin con ```submit_block()```.

## 🚀 Prerequisiti

### 1. Nodo Bitcoin

Assicurati di avere un nodo Bitcoin in esecuzione con il supporto per le chiamate RPC. Configura il file bitcoin.conf come segue:

#### 📄 Esempio di bitcoin.conf
```
regtest=1  # Se vuoi eseguire in regtest, altrimenti commenta questa linea
testnet4=1  # Se vuoi eseguire in testnet, altrimenti commenta questa linea
mainnet=1  # Se vuoi eseguire in mainnet, altrimenti commenta questa riga

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
## 🔧 Configurazione

Entrambi gli script contengono i parametri di connessione RPC:
```
RPC_USER = "tuo_utente"
RPC_PASSWORD = "tua_password"
RPC_HOST = "indirizzo_nodo"
RPC_PORT = "port"
```
Modifica queste variabili in base alla configurazione del tuo nodo.

Inoltre, specifica l'indirizzo Bitcoin del miner per ricevere la ricompensa:

```
MINER_ADDRESS = "indirizzo_bitcoin"
```

## 📜 Esecuzione degli script

Per avviare il miner con debug attivato:

```
python miner_debug.py
```

Per avviare la versione ottimizzata senza debug:

```
python miner_opt.py
```

## 📌 Nota

Questi script possono essere utilizzati sia per testnet che per regtest, a seconda della configurazione del nodo. Per implementare un miner più efficiente, considera l'uso del protocollo Stratum e hardware dedicato.

## 📜 Licenza

Questo progetto è open-source e disponibile sotto la licenza MIT.
