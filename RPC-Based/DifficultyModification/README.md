# Bitcoin Mining (RPC-Based)

Questo progetto è un semplice miner Bitcoin scritto interamente in Python e suddiviso in moduli. È pensato per scopi didattici e di test in ambiente **regtest**.

Il miner permette di modificare la difficoltà mediante il parametro ```DIFFICULTY_FACTOR``` e offre tre modalità differenti per l'elaborazione del nonce (incremental, random e mixed), per facilitare esperimenti e comprensione del processo di mining.

**Attenzione**: Questo miner è concepito esclusivamente per scopi di test in ambiente Regtest e non è adatto al mining competitivo in mainnet o testnet.

## Cosa puoi imparare:

- Come un nodo Bitcoin fornisce un template di blocco per il mining.

- Come vengono costruiti i blocchi, a partire dalla transazione coinbase fino al Merkle Root.

- Il processo di hashing e la ricerca di un nonce valido per soddisfare la difficoltà richiesta.

- L'invio del blocco minato al nodo per la validazione.

**Nota**: Questo progetto è concepito esclusivamente come base didattica per comprendere i meccanismi sottostanti al mining Bitcoin e non è destinato al mining competitivo in ambienti di produzione.

## Struttura del Progetto

Il progetto è organizzato in moduli per separare chiaramente le responsabilità:

- **```config.py```**: Contiene tutte le impostazioni di configurazione: parametri RPC, indirizzo del wallet del miner, fattore di difficoltà e la modalità di calcolo del nonce (NONCE_MODE).

- **```rpc.py```**: Gestisce le connessioni RPC al nodo Bitcoin. Include funzioni per:
    - Connettersi al nodo (connect_rpc())
    - Testare la connessione (test_rpc_connection())
    - Ottenere il template del blocco (get_block_template())
    - Aggiornare le transazioni del template (aggiungendo i dati witness) tramite ensure_witness_data()
    - Inviare il blocco minato (submit_block())

- **```block_builder.py```**: Contiene tutte le funzioni per la costruzione e la serializzazione del blocco:
    - Funzioni di hashing (es. double_sha256())
    - Funzioni per la decodifica di nBits (decode_nbits()) e la codifica VarInt (encode_varint())
    - Funzioni per codificare l’altezza del blocco nella coinbase (tx_encode_coinbase_height())
    - Costruzione della coinbase transaction: ora la funzione build_coinbase_transaction(template, miner_script_pubkey) riceve lo scriptPubKey del miner come parametro
    - Calcolo del Merkle Root (calculate_merkle_root())
    - Costruzione dell'header del blocco (build_block_header())
    - Serializzazione del blocco completo (serialize_block())

- **```miner.py```**: Implementa la logica di mining, con la funzione mine_block(header_hex, target_hex, nonce_mode) che esegue la ricerca del nonce valido. La modalità di calcolo del nonce viene determinata dal parametro nonce_mode, che può assumere i seguenti valori:
    - incremental: il miner inizia da 0 e incrementa di 1 ogni iterazione. Questo metodo garantisce la copertura completa dello spazio dei nonce, ma può essere lento se il target è molto basso.
    - random: ad ogni iterazione viene generato un nonce casuale. Questo approccio riduce la probabilità di collisioni se ci sono più miner, ma potrebbe ripetere valori già testati.
    - mixed: il miner sceglie un nonce casuale iniziale e poi incrementa in modo sequenziale. Combina i vantaggi dei due metodi precedenti.

- **```main.py```**: È lo script principale che coordina l'intero processo di mining. Il main esegue un ciclo continuo che:
    1. Verifica la connessione RPC.
    2. Richiede un template del blocco dal nodo Bitcoin.
    3. Aggiorna le transazioni del template per includere i dati witness.
    4. Ottiene lo scriptPubKey del miner e costruisce la coinbase transaction.
    5. Modifica il target di difficoltà secondo il parametro DIFFICULTY_FACTOR.
    6. Calcola il Merkle Root.
    7. Costruisce l'header del blocco.
    8. Esegue il mining per trovare il nonce valido, utilizzando la modalità impostata in NONCE_MODE.
    9. Serializza il blocco completo.
    10. Invia il blocco al nodo Bitcoin tramite una nuova connessione RPC.

## Modalità di Calcolo del Nonce (nonce_mode)

Il parametro ```NONCE_MODE``` nel file di configurazione controlla il metodo usato per iterare il nonce durante il mining. Le opzioni disponibili sono:

- **incremental**: Il miner parte da 0 e incrementa il nonce di 1 ad ogni iterazione. Questo metodo garantisce una copertura completa dello spazio dei nonce.

- **random**: Ad ogni iterazione viene generato un nonce casuale. Questo approccio può evitare ripetizioni, ma potrebbe ripetere alcuni valori già testati.

- **mixed**: Il miner sceglie inizialmente un valore casuale e poi procede incrementando sistematicamente. Questa modalità combina i vantaggi degli approcci casuale e incrementale.

| Metodo | Vantaggi | Svantaggi |
|-|-|-|
| **Incrementale (da 0 a 2³² - 1)** | Esplora tutti i nonce in modo sistematico e sequenziale. Garantisce che nessun valore venga saltato. | Può essere prevedibile e meno efficace se il target è molto basso. Tutti i miner che usano questo metodo in parallelo potrebbero generare collisioni sui nonce. |
| **Casuale (ogni iterazione un nonce randomico)** | Buona distribuzione casuale, utile per ambienti distribuiti e per evitare collisioni tra più miner. | Possibilità di ripetere nonce già testati, riducendo l’efficienza a lungo termine. |
| **Misto (primo nonce casuale, poi incremento)** | Combina il vantaggio della casualità iniziale con la sistematicità dell’incremento. Utile per diversificare l’output in ambienti paralleli. | Se la ricerca inizia in una zona sfavorevole dello spazio dei nonce, potrebbe richiedere più tempo per trovare un hash valido. |

## Prerequisiti

### 1. Nodo Bitcoin

Assicurati di avere un nodo Bitcoin in esecuzione con il supporto per le chiamate RPC. Configura il file bitcoin.conf come segue:

#### Esempio di bitcoin.conf
```
regtest=1
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

### 3. Configurazione

Tutte le impostazioni sono gestite tramite config.py:

| Parametro | Descrizione |
|-|-|
| **RPC_USER**         | Nome utente per l'autenticazione RPC, come configurato in bitcoin.conf. |
| **RPC_PASSWORD** | Password RPC. |
| **RPC_HOST** | Indirizzo IP del nodo Bitcoin. |
| **RPC_PORT** | Porta per la connessione RPC. |
| **WALLET_ADDRESS** | Indirizzo del wallet del miner per la coinbase transaction. |
| **RPC_PASSWORD** | Password RPC. |
| **DIFFICULTY_FACTOR** | Fattore per modificare il target di difficoltà in regtest, utile per simulare condizioni più impegnative. |
| **NONCE_MODE** | Modalità per iterare il nonce: "incremental", "random" o "mixed". |

### 4. Esecuzione
Per avviare il miner in ambiente regtest, esegui:

```bash
python main.py
```

Il programma esegue un ciclo continuo che, ad ogni iterazione, richiede un nuovo template, esegue il mining e invia il blocco minato al nodo Bitcoin. In questo modo, il miner continua automaticamente a lavorare su blocchi successivi.

## Licenza

Questo progetto è open-source e disponibile sotto la licenza MIT.