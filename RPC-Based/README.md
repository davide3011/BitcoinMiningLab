# Bitcoin Mining (RPC-Based)

Questo progetto è un semplice miner Bitcoin scritto interamente in Python e suddiviso in moduli. È pensato per scopi didattici e di test in ambiente **regtest**.

## Introduzione al Mining Bitcoin

Il mining è il processo attraverso il quale nuove transazioni vengono confermate e aggiunte alla blockchain Bitcoin.
I miner competono per risolvere un problema matematico complesso (proof-of-work) e il vincitore ottiene il diritto di aggiungere un nuovo blocco alla catena, ricevendo in cambio una ricompensa in bitcoin.

## Architettura del Progetto

Il miner è strutturato in moduli separati, ognuno con una responsabilità specifica:

- `main.py`: Coordina l'intero processo di mining
- `config.py`: Contiene le configurazioni del miner
- `rpc.py`: Gestisce la comunicazione con il nodo Bitcoin
- `block_builder.py`: Costruisce e serializza il blocco
- `miner.py`: Implementa l'algoritmo di mining (proof-of-work)

## Il Processo di Mining Passo per Passo

### 1. Connessione RPC al Nodo Bitcoin

Il mining inizia stabilendo una connessione con un nodo Bitcoin tramite il protocollo RPC (Remote Procedure Call).
Questo permette al miner di comunicare con la rete Bitcoin per ottenere informazioni aggiornate e inviare blocchi minati.

```python
def connect_rpc():
    return AuthServiceProxy(f"http://{config.RPC_USER}:{config.RPC_PASSWORD}@{config.RPC_HOST}:{config.RPC_PORT}")
```

### 2. Richiesta del Block Template (getblocktemplate)

Il miner richiede un "template" del blocco tramite la chiamata RPC `getblocktemplate`.
Questa chiamata, definita nel [BIP 22](https://github.com/bitcoin/bips/blob/master/bip-0022.mediawiki) e aggiornata nel [BIP 23](https://github.com/bitcoin/bips/blob/master/bip-0023.mediawiki), 
fornisce tutte le informazioni necessarie per costruire un blocco valido:

- Hash del blocco precedente
- Elenco delle transazioni da includere
- Target di difficoltà
- Timestamp corrente
- Valore della ricompensa (coinbase)
- Altezza del blocco

```python
def get_block_template(rpc):
    return rpc.getblocktemplate({"rules": ["segwit"]})
```

Specificando `"rules": ["segwit"]`, richiediamo un template compatibile con Segregated Witness ([BIP 141](https://github.com/bitcoin/bips/blob/master/bip-0141.mediawiki)), 
che permette di includere transazioni SegWit nel blocco.

### 3. Costruzione della Transazione Coinbase

La transazione coinbase è la prima transazione in ogni blocco e ha caratteristiche speciali:

- Non ha input reali (usa un input fittizio con hash tutto zero)
- Crea nuovi bitcoin come ricompensa per il miner
- Può contenere dati arbitrari nello scriptSig

Secondo il [BIP 34](https://github.com/bitcoin/bips/blob/master/bip-0034.mediawiki), la transazione coinbase deve includere l'altezza del blocco come primo elemento dello scriptSig:

```python
def tx_encode_coinbase_height(height):
    height_bytes = height.to_bytes((height.bit_length() + 7) // 8, 'little')
    return f"{len(height_bytes):02x}" + height_bytes.hex()
```

Inoltre, il nostro miner permette di includere un messaggio personalizzato nella transazione coinbase:

```python
if coinbase_message:
    message_bytes = coinbase_message.encode('utf-8')
    script_sig_hex += "6a" + f"{len(message_bytes):02x}" + message_bytes.hex()
```

La transazione coinbase include anche un output che assegna la ricompensa all'indirizzo del miner e, se necessario, un output per il witness commitment (per supportare SegWit).

### 4. Calcolo del Merkle Root

Il Merkle Root è un hash che riassume tutte le transazioni del blocco in un unico valore di 32 byte. Viene calcolato costruendo un albero binario (Merkle Tree) dove:

1. Le foglie sono gli hash delle transazioni
2. I nodi interni sono gli hash della concatenazione dei loro figli
3. La radice dell'albero è il Merkle Root

```python
def calculate_merkle_root(coinbase_tx, transactions):
    tx_hashes = [coinbase_hash] + [tx["hash"] for tx in transactions]
    while len(tx_hashes) > 1:
        if len(tx_hashes) % 2 == 1:
            tx_hashes.append(tx_hashes[-1])  # Padding se dispari
        tx_hashes = [double_sha256(tx_hashes[i] + tx_hashes[i + 1]) for i in range(0, len(tx_hashes), 2)]
    return tx_hashes[0]
```

Se il numero di nodi a un livello è dispari, l'ultimo nodo viene duplicato. 
Questo garantisce che ogni blocco abbia un Merkle Root unico e permette di verificare l'appartenenza di una transazione al blocco senza scaricare tutte le transazioni (SPV - Simplified Payment Verification).

### 5. Costruzione dell'Header del Blocco

L'header del blocco è composto da 6 campi per un totale di 80 byte:

1. **Version** (4 byte): Versione del protocollo
2. **Previous Block Hash** (32 byte): Hash del blocco precedente
3. **Merkle Root** (32 byte): Hash che riassume tutte le transazioni
4. **Timestamp** (4 byte): Ora di creazione del blocco (secondi da epoch Unix)
5. **Bits** (4 byte): Difficoltà target in formato compatto
6. **Nonce** (4 byte): Valore modificato durante il mining per trovare un hash valido

```python
def build_block_header(version, prev_hash, merkle_root, timestamp, bits, nonce):
    header = (
        struct.pack("<I", version) +               # Version (4 byte, little-endian)
        unhexlify(prev_hash)[::-1] +               # Previous Block Hash (32 byte, invertito)
        unhexlify(merkle_root)[::-1] +             # Merkle Root (32 byte, invertito)
        struct.pack("<I", timestamp) +             # Timestamp (4 byte, little-endian)
        unhexlify(bits)[::-1] +                    # Bits/Target (4 byte, invertito)
        struct.pack("<I", nonce)                   # Nonce (4 byte, little-endian)
    )
    return hexlify(header).decode()
```

### 6. Decodifica del Target di Difficoltà

In Bitcoin, la difficoltà è codificata nel campo 'bits' dell'header del blocco. Il formato è compatto: i primi 8 bit rappresentano l'esponente, i restanti 24 bit rappresentano la mantissa. Questa funzione converte questo formato compatto nel target effettivo:

```python
def decode_nbits(nBits: int) -> str:
    exponent = (nBits >> 24) & 0xff
    significand = nBits & 0x007fffff
    return f"{(significand << (8 * (exponent - 3))):064x}"
```

Il miner permette di modificare la difficoltà mediante il parametro `DIFFICULTY_FACTOR` nel file `config.py`. Questo è utile per scopi didattici in ambiente regtest, 
dove è possibile rendere il mining più facile o più difficile.

### 7. Processo di Mining (Proof-of-Work)

Il mining è il processo di ricerca di un nonce che, aggiunto all'header del blocco, produce un hash inferiore al target di difficoltà. 
Questo processo richiede molti tentativi e garantisce la sicurezza della blockchain.

Il nostro miner offre tre modalità differenti per l'elaborazione del nonce:

- **Incremental**: Il nonce viene incrementato sequenzialmente da 0 a 2^32-1
- **Random**: Ad ogni iterazione viene scelto un nonce casuale
- **Mixed**: Inizia con un nonce casuale e poi procede incrementalmente

```python
def mine_block(header_hex, target_hex, nonce_mode="incremental"):
    target = int(target_hex, 16)
    
    # Inizializza il nonce in base alla modalità selezionata
    if nonce_mode == "incremental":
        nonce = 0
    elif nonce_mode == "random" or nonce_mode == "mixed":
        nonce = random.randint(0, 0xFFFFFFFF)
    
    # Loop principale di mining
    while True:
        full_header = base_header + struct.pack("<I", nonce)
        block_hash = double_sha256(full_header)
        
        # Verifica se l'hash trovato è valido (inferiore al target)
        if int.from_bytes(block_hash, 'little') < target:
            return hexlify(full_header).decode(), nonce, hashrate
        
        # Aggiorna il nonce per il prossimo tentativo
        if nonce_mode == "incremental" or nonce_mode == "mixed":
            nonce = (nonce + 1) % 0x100000000
        elif nonce_mode == "random":
            nonce = random.randint(0, 0xFFFFFFFF)
```

Durante il mining, il timestamp viene periodicamente aggiornato per mantenere il blocco "fresco". Inoltre, vengono calcolate e visualizzate statistiche come l'hashrate (hash al secondo).

### 8. Serializzazione del Blocco

Una volta trovato un nonce valido, il blocco completo viene serializzato nel formato richiesto dal protocollo Bitcoin:

```python
def serialize_block(header_hex, coinbase_tx, transactions):
    num_tx = len(transactions) + 1  # +1 per includere la coinbase
    num_tx_hex = encode_varint(num_tx)
    transactions_hex = "".join(tx["data"] for tx in transactions)
    block_hex = header_hex + num_tx_hex + coinbase_tx + transactions_hex
    return block_hex
```

Un blocco Bitcoin completo è composto da:
1. Block Header (80 byte)
2. Transaction Counter (numero di transazioni in formato VarInt)
3. Transactions (tutte le transazioni serializzate, iniziando con la coinbase)

### 9. Invio del Blocco alla Rete

Infine, il blocco minato viene inviato al nodo Bitcoin tramite la chiamata RPC `submitblock`:

```python
def submit_block(rpc, serialized_block):
    result = rpc.submitblock(serialized_block)
    if result is None:
        print("\nBlocco accettato nella blockchain!")
    else:
        print(f"\nErrore nell'invio del blocco: {result}")
```

Se il blocco è valido e contiene un proof-of-work sufficiente, il nodo lo accetterà e lo propagherà agli altri nodi della rete.

## Personalizzazione del Miner

Il miner permette diverse personalizzazioni tramite il file `config.py`:

- **DIFFICULTY_FACTOR**: Modifica la difficoltà di mining (solo in regtest)
- **NONCE_MODE**: Cambia la strategia di ricerca del nonce ("incremental", "random" o "mixed")
- **COINBASE_MESSAGE**: Personalizza il messaggio nella transazione coinbase
- **TIMESTAMP_UPDATE_INTERVAL**: Imposta l'intervallo di aggiornamento del timestamp durante il mining

## Avvertenze

**Attenzione**: Questo miner è concepito esclusivamente per scopi di test in ambiente Regtest o Testnet e non è adatto al mining competitivo in mainnet. 
Il mining su mainnet richiede hardware specializzato (ASIC) e non è economicamente sostenibile con hardware generico.

## Guida all'Installazione e all'Uso

### Prerequisiti

- Python 3.7 o superiore
- Bitcoin Core (versione 0.21.0 o superiore)
- Connessione a Internet (per scaricare le dipendenze)

### 1. Installazione di Bitcoin Core

1. Scarica Bitcoin Core dal [sito ufficiale](https://bitcoincore.org/en/download/) o da [GitHub](https://github.com/bitcoin/bitcoin/releases)
2. Installa Bitcoin Core seguendo le istruzioni per il tuo sistema operativo
3. Crea una directory per i dati di Bitcoin (ad esempio `~/.bitcoin` su Linux/Mac o `C:\Users\Username\AppData\Roaming\Bitcoin` su Windows)

### 2. Configurazione di Bitcoin Core

Crea un file `bitcoin.conf` nella directory dei dati di Bitcoin con il seguente contenuto:

```
# Abilita la modalità regtest (ambiente di test locale)
regtest=1

# Abilita il server RPC
server=1
rpcallowip=127.0.0.1

# Credenziali RPC (cambia questi valori!)
rpcuser=tuousername
rpcpassword=tuapassword

# Porta RPC (default per regtest: 18443)
rpcport=18443

# Abilita il mining con CPU
gen=0

# Abilita l'indicizzazione delle transazioni
txindex=1
```

### 3. Avvio di Bitcoin Core in modalità regtest

- **Windows**: Avvia Bitcoin Core con il parametro `-regtest`
- **Linux/Mac**: Esegui `bitcoind -regtest` da terminale

Puoi verificare che il nodo sia in esecuzione con il comando:
```
bitcoin-cli -regtest getblockchaininfo
```

### 4. Configurazione del Miner

1. Clona o scarica questo repository
2. Installa le dipendenze Python:
   ```
   pip install -r requirements.txt
   ```
3. Modifica il file `config.py` con i tuoi parametri:

```python
# Configurazione RPC
RPC_USER = "tuousername"                # Username per l'autenticazione RPC
RPC_PASSWORD = "tuapassword"            # Password per l'autenticazione RPC
RPC_HOST = "127.0.0.1"                  # Indirizzo IP del nodo
RPC_PORT = 18443                        # Porta RPC del nodo (default per regtest)

# Configurazione Wallet
WALLET_ADDRESS = "tuoindirizzo"         # Indirizzo del wallet del miner

# Parametri Mining
DIFFICULTY_FACTOR = 100000000           # Fattore per modificare la difficoltà
NONCE_MODE = "mixed"                    # Modalità di aggiornamento del nonce
TIMESTAMP_UPDATE_INTERVAL = 30          # Intervallo aggiornamento timestamp

# Messaggio Coinbase
COINBASE_MESSAGE = "/Il tuo messaggio/" # Messaggio personalizzato
```

### 5. Generazione di un Indirizzo per Ricevere la Ricompensa

Per ottenere un indirizzo dove ricevere le ricompense del mining:

```
bitcoin-cli -regtest getnewaddress "Mining Rewards" bech32
```

Copia l'indirizzo generato nel campo `WALLET_ADDRESS` del file `config.py`.

### 6. Avvio del Miner

Esegui il miner con il comando:

```
python main.py
```

Il programma si connetterà al nodo Bitcoin, costruirà un blocco e inizierà il processo di mining. Una volta trovato un blocco valido, lo invierà al nodo e visualizzerà un messaggio di conferma.

### 7. Verifica del Blocco Minato

Puoi verificare che il blocco sia stato aggiunto alla blockchain con:

```
bitcoin-cli -regtest getblockcount
bitcoin-cli -regtest getblockhash <numero_blocco>
bitcoin-cli -regtest getblock <hash_blocco>
```

### 8. Verifica del Saldo

Per verificare che la ricompensa sia stata accreditata al tuo indirizzo:

```
bitcoin-cli -regtest getbalance
```

Nota: i blocchi minati devono maturare (100 conferme) prima che la ricompensa possa essere spesa.

## Risoluzione dei Problemi

- **Errore di connessione RPC**: Verifica che Bitcoin Core sia in esecuzione e che le credenziali RPC nel file `config.py` corrispondano a quelle nel file `bitcoin.conf`
- **Mining troppo lento**: Diminuisci il valore di `DIFFICULTY_FACTOR` nel file `config.py` per rendere il mining più facile (solo in ambiente regtest)

## Riferimenti

- [BIP 22: getblocktemplate](https://github.com/bitcoin/bips/blob/master/bip-0022.mediawiki)
- [BIP 23: getblocktemplate - Pooled Mining](https://github.com/bitcoin/bips/blob/master/bip-0023.mediawiki)
- [BIP 34: Block v2, Height in Coinbase](https://github.com/bitcoin/bips/blob/master/bip-0034.mediawiki)
- [BIP 141: Segregated Witness](https://github.com/bitcoin/bips/blob/master/bip-0141.mediawiki)
- [Bitcoin Developer Reference](https://developer.bitcoin.org/reference/)
- [Bitcoin Core Documentation](https://bitcoin.org/en/bitcoin-core/)
- [Bitcoin Core RPC Commands](https://developer.bitcoin.org/reference/rpc/)

## Licenza

Distribuito sotto la licenza MIT.


