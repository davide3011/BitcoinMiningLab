# Bitcoin Mining (RPC-Based)

Questo progetto implementa un miner Bitcoin di base che interagisce con un nodo Bitcoin Core tramite chiamate RPC (Remote Procedure Call). È progettato per scopi didattici, per illustrare i concetti fondamentali del mining e il processo di costruzione e validazione dei blocchi.

## Concetti Fondamentali del Mining Bitcoin

Immaginiamo Bitcoin come un grande libro mastro digitale distribuito, chiamato **blockchain**. Questo libro mastro contiene la registrazione di tutte le transazioni avvenute sulla rete Bitcoin.

**1. Transazioni e Blocchi:**
   - Quando qualcuno invia Bitcoin, crea una **transazione**.
   - Queste transazioni vengono raccolte in gruppi chiamati **blocchi**.
   - Ogni nuovo blocco contiene un riferimento (un "hash") al blocco precedente, creando così una catena (la *blockchain*).

**2. Il Ruolo dei Miner:**
   - I **miner** sono partecipanti della rete che competono per aggiungere il prossimo blocco alla catena.
   - Per farlo, devono risolvere un complesso puzzle crittografico.
   - Il loro lavoro è fondamentale per:
     - **Confermare le transazioni:** Includendo le transazioni in un blocco, i miner le rendono ufficiali e irreversibili.
     - **Creare nuovi Bitcoin:** Il miner che risolve per primo il puzzle viene ricompensato con nuovi Bitcoin (la "block reward") e le commissioni delle transazioni incluse nel blocco.
     - **Mantenere la sicurezza della rete:** Il processo di mining rende estremamente difficile e costoso per chiunque tentare di alterare la storia delle transazioni.

**3. Il Puzzle Crittografico (Proof-of-Work):**
   - Il puzzle consiste nel trovare un numero speciale, chiamato **nonce**.
   - Quando il nonce viene combinato con i dati del blocco (transazioni, hash del blocco precedente, timestamp, ecc.) e processato attraverso una funzione crittografica chiamata **SHA-256**, il risultato (l'**hash del blocco**) deve essere inferiore a un certo valore target (la **difficoltà**).
   - Trovare questo nonce richiede una grande potenza di calcolo, poiché l'unico modo è provare miliardi di nonce diversi al secondo (**hashing**).
   - Questo processo è chiamato **Proof-of-Work (PoW)**, perché dimostra che il miner ha speso energia (lavoro computazionale) per trovare la soluzione.

**4. La Difficoltà:**
   - La rete Bitcoin regola automaticamente la **difficoltà** del puzzle circa ogni due settimane (2016 blocchi).
   - L'obiettivo è mantenere il tempo medio di creazione di un nuovo blocco intorno ai 10 minuti, indipendentemente dalla potenza di calcolo totale della rete.
   - Se i blocchi vengono trovati troppo velocemente, la difficoltà aumenta; se vengono trovati troppo lentamente, diminuisce.

**5. Costruzione del Blocco:**
   - Prima di iniziare a cercare il nonce, un miner deve:
     - **Ottenere un template di blocco:** Richiede al nodo Bitcoin le informazioni necessarie (hash del blocco precedente, transazioni in attesa, versione, timestamp attuale, bits di difficoltà).
     - **Creare la transazione Coinbase:** È la prima transazione nel blocco e crea i nuovi Bitcoin per la ricompensa del miner. Include anche un campo per un messaggio personalizzato.
     - **Calcolare il Merkle Root:** È un hash riassuntivo di tutte le transazioni nel blocco, organizzate in una struttura ad albero (Merkle Tree). Garantisce l'integrità delle transazioni.
     - **Assemblare l'Header del Blocco:** Contiene la versione, l'hash del blocco precedente, il Merkle Root, il timestamp, i bits di difficoltà e il campo per il nonce (inizialmente a 0).

**6. Il Processo di Mining:**
   - Il miner prende l'header del blocco assemblato.
   - Inizia a provare diversi valori di **nonce**.
   - Per ogni nonce, calcola l'hash SHA-256 dell'header.
   - Confronta l'hash calcolato con il **target** di difficoltà.
   - Se l'hash è inferiore al target, il miner ha trovato la soluzione! Ha "minato" il blocco.
   - Se l'hash non è inferiore, prova un nuovo nonce e ripete il processo.

**7. Propagazione e Consenso:**
   - Una volta trovato un blocco valido, il miner lo trasmette alla rete Bitcoin.
   - Gli altri nodi verificano la validità del blocco (controllano la PoW, la validità delle transazioni, ecc.).
   - Se il blocco è valido, lo aggiungono alla loro copia della blockchain e iniziano a lavorare sul blocco successivo, usando l'hash del blocco appena trovato come riferimento.
   - Questo processo garantisce il **consenso** distribuito sulla storia delle transazioni.

In sintesi, il mining è il cuore pulsante di Bitcoin: un processo competitivo e decentralizzato che valida le transazioni, crea nuova moneta e protegge l'integrità della rete attraverso la Proof-of-Work.

## Funzionamento del Programma

Lo script `main.py` orchestra il processo di mining interagendo con un nodo Bitcoin Core tramite RPC. Ecco i passaggi principali eseguiti in un ciclo continuo:

1.  **Test Connessione RPC (`test_rpc_connection`)**: All'avvio, verifica che sia possibile stabilire una connessione RPC con il nodo Bitcoin Core configurato in `config.py`.

2.  **Inizio Ciclo di Mining**: Il programma entra in un loop infinito per cercare continuamente nuovi blocchi.

3.  **Connessione RPC per Template (`connect_rpc`)**: Stabilisce una nuova connessione RPC specifica per ottenere i dati del template del blocco.

4.  **Ottenimento Template Blocco (`get_block_template`)**: Chiama il metodo RPC `getblocktemplate` sul nodo Bitcoin. Questo restituisce una struttura dati JSON contenente:
    *   `version`: La versione del blocco.
    *   `previousblockhash`: L'hash del blocco precedente nella catena.
    *   `transactions`: Un elenco di transazioni in attesa da includere nel blocco.
    *   `coinbasevalue`: Il valore della ricompensa del blocco (in satoshi).
    *   `bits`: La rappresentazione compatta della difficoltà target attuale.
    *   `curtime`: Il timestamp attuale secondo il nodo.
    *   Altre informazioni utili.
    Se il template non può essere ottenuto, attende e riprova.

5.  **Gestione Dati Witness (`ensure_witness_data`)**: Per le transazioni SegWit (Segregated Witness), il template iniziale potrebbe non includere tutti i dati witness necessari. Questa funzione effettua chiamate RPC aggiuntive (`getrawtransaction`) per recuperare i dati completi e aggiornare le transazioni nel template.

6.  **Costruzione Transazione Coinbase (`build_coinbase_transaction`)**: Crea la transazione speciale *coinbase*:
    *   Include l'altezza del blocco corrente (`height` dal template).
    *   Imposta l'output per inviare la ricompensa del blocco (`coinbasevalue`) e le eventuali commissioni all'indirizzo del miner specificato in `config.WALLET_ADDRESS` (ottenendo lo `scriptPubKey` tramite `getaddressinfo`).
    *   Aggiunge un messaggio personalizzato (`config.COINBASE_MESSAGE`) nell'input della coinbase.
    *   Restituisce la transazione serializzata in esadecimale (`coinbase_tx`) e il suo ID (`coinbase_txid`).

7.  **Calcolo e Modifica Target (`decode_nbits`)**: 
    *   Decodifica il campo `bits` (formato compatto della difficoltà) dal template per ottenere il target di difficoltà completo (`original_target`) in formato esadecimale a 64 caratteri.
    *   **Solo per `regtest`**: Se la rete è `regtest` (rilevata tramite `getblockchaininfo`), permette di impostare un `DIFFICULTY_FACTOR` in `config.py` per rendere il target artificialmente più difficile (dividendo il target numerico per il fattore). Questo è utile per testare il mining su regtest simulando un ambiente di difficoltà maggiore. Su `testnet` o `mainnet`, il fattore è forzato a 1.0.
    *   Stampa il target originale e quello modificato (se applicabile).

8.  **Calcolo Merkle Root (`calculate_merkle_root`)**: 
    *   Prende il `coinbase_txid` e gli ID di tutte le altre transazioni (`txid`) dal template.
    *   Costruisce un Merkle Tree con questi hash.
    *   Calcola e restituisce la radice dell'albero (Merkle Root), un singolo hash che rappresenta tutte le transazioni nel blocco.

9.  **Costruzione Header Blocco (`build_block_header`)**: 
    *   Assembla l'header del blocco di 80 byte in formato esadecimale, concatenando:
        *   `version` (4 byte, little-endian)
        *   `previousblockhash` (32 byte, hash invertito byte per byte)
        *   `merkle_root` (32 byte, hash invertito byte per byte)
        *   `curtime` (4 byte, little-endian)
        *   `bits` (4 byte, little-endian)
        *   `nonce` (4 byte, little-endian, inizializzato a 0)

10. **Avvio Watchdog (`watchdog_bestblock` in un Thread)**:
    *   Avvia un thread separato che monitora continuamente l'hash del blocco più recente sulla rete (`getbestblockhash`) ogni `CHECK_INTERVAL` secondi.
    *   Se rileva un nuovo blocco (l'hash cambia), imposta un `threading.Event` (`stop_event`). Questo segnala al processo di mining principale di interrompersi, poiché il lavoro attuale è diventato obsoleto.

11. **Mining (`mine_block`)**: 
    *   Questa è la funzione che esegue la Proof-of-Work.
    *   Prende l'header del blocco (`header_hex`) e il target modificato (`modified_target`).
    *   Entra in un ciclo:
        *   Prova un valore di `nonce` (la strategia di incremento/randomizzazione dipende da `config.NONCE_MODE`).
        *   Aggiorna il campo nonce nell'header.
        *   Calcola il doppio hash SHA-256 dell'header aggiornato.
        *   Confronta l'hash risultante (come intero) con il target (come intero).
        *   Se l'hash è inferiore al target, ha trovato una soluzione! Restituisce l'header vincente (`mined_header_hex`), il `nonce` trovato e l'hashrate stimato.
        *   Controlla periodicamente lo `stop_event`. Se è stato impostato dal watchdog, interrompe il mining e restituisce `None` per indicare l'interruzione.

12. **Gestione Interruzione**: 
    *   Dopo il ritorno da `mine_block`, ferma esplicitamente il thread watchdog.
    *   Se `mine_block` ha restituito `None` (quindi è stato interrotto), stampa un messaggio e ricomincia il ciclo dal passo 3 per ottenere un nuovo template aggiornato.

13. **Serializzazione Blocco Completo (`serialize_block`)**: 
    *   Se il mining ha avuto successo (non interrotto), prende l'header vincente (`mined_header_hex`), la transazione coinbase (`coinbase_tx`) e l'elenco delle altre transazioni (`template['transactions']`).
    *   Concatena questi elementi nel formato corretto per creare i dati completi del blocco serializzato in esadecimale, pronto per essere inviato al nodo.

14. **Invio Blocco (`submit_block`)**: 
    *   Stabilisce una nuova connessione RPC.
    *   Chiama il metodo RPC `submitblock` passando i dati del blocco serializzato.
    *   Il nodo Bitcoin Core verificherà il blocco. Se valido, lo aggiungerà alla blockchain e lo propagherà sulla rete.
    *   Stampa il risultato dell'invio (successo o errore).

15. **Pausa e Ripetizione**: Attende brevemente (`time.sleep(1)`) prima di ricominciare il ciclo dal passo 2 per minare il blocco successivo.

16. **Gestione Errori**: Un blocco `try...except` cattura eventuali eccezioni durante il ciclo, le stampa e permette al ciclo di continuare.

## Moduli Ausiliari

Il codice è organizzato in moduli per chiarezza:

*   **`rpc.py`**: Contiene le funzioni per interagire con il nodo Bitcoin Core tramite RPC (connessione, chiamate specifiche come `getblocktemplate`, `submitblock`, `getrawtransaction`, `getbestblockhash`, `getaddressinfo`).
*   **`block_builder.py`**: Contiene le funzioni per costruire le varie parti del blocco (decodifica `nBits`, calcolo Merkle Root, costruzione header, costruzione coinbase, serializzazione blocco, verifica transazioni SegWit).
*   **`miner.py`**: Contiene la funzione `mine_block` che implementa il ciclo di hashing per la Proof-of-Work.
*   **`config.py`**: File di configurazione per i parametri RPC (host, porta, utente, password), l'indirizzo del wallet del miner, il messaggio coinbase, il fattore di difficoltà per regtest e la modalità di ricerca del nonce.
*   **`utils.py`**: Funzioni di utilità generale (es. conversioni esadecimali, hashing SHA-256).

## Guida all'Installazione e all'Uso

### Prerequisiti

*   **Python 3.7+**: Assicurati di avere Python installato.
*   **Bitcoin Core**: È necessario un nodo Bitcoin Core in esecuzione, sincronizzato (o in modalità `regtest` o `testnet`) e configurato per accettare connessioni RPC. Modifica il file `bitcoin.conf` del tuo nodo aggiungendo o verificando queste linee:
    ```
    server=1
    rpcuser=tuo_utente_rpc
    rpcpassword=tua_password_rpc
    rpcallowip=127.0.0.1  # O l'IP da cui eseguirai lo script
    ```
    *Ricorda di usare credenziali robuste.*
*   **Libreria `python-bitcoinrpc`**: Questa libreria facilita le chiamate RPC. Installala con pip:
    ```bash
    pip install python-bitcoinrpc
    ```

### Configurazione (`config.py`)

Il file `config.py` contiene tutte le impostazioni necessarie per il funzionamento del miner. Ecco una guida dettagliata per ogni parametro:

| Parametro | Descrizione | Valori/Note | Esempio |
|-----------|-------------|-------------|---------|
| **Configurazione RPC** |
| `RPC_USER` | Nome utente per l'autenticazione RPC | Deve corrispondere a `rpcuser` in `bitcoin.conf` | `"bitcoinrpc"` |
| `RPC_PASSWORD` | Password per l'autenticazione RPC | Deve corrispondere a `rpcpassword` in `bitcoin.conf`. Usa password forte | `"your_strong_password_here"` |
| `RPC_HOST` | Indirizzo IP del nodo Bitcoin Core | `127.0.0.1` se locale, altrimenti IP del server | `"127.0.0.1"` |
| `RPC_PORT` | Porta per le chiamate RPC | Mainnet: 8332<br>Testnet: 48332<br>Regtest: 18443 | `18443`  |
| **Configurazione Wallet** |
| `WALLET_ADDRESS` | Indirizzo Bitcoin per le ricompense | Generabile con `getnewaddress`.<br>Verifica tipo rete corretto | `"bcrt1q6j8j76uz8xf3qrxzh7ce3mpj8fk5wwkxw4pkxl"` |
| **Personalizzazione Coinbase** |
| `COINBASE_MESSAGE` | Messaggio nel blocco | Max 100 bytes.<br>Codificato in ASCII.<br>Per firme/messaggi storici | `"/Ciao a tutti!/"` |
| **Configurazione Difficoltà** |
| `DIFFICULTY_FACTOR` | Moltiplicatore difficoltà (solo regtest) | ≥ 1.0<br>1.0 = normale<br>2.0 = doppia<br>Forzato a 1.0 su main/testnet | `4.0` |
| **Strategia Mining** |
| `NONCE_MODE` | Metodo ricerca nonce | `'increment'`: Sequenziale<br>`'random'`: Casuale<br>`'mixed'`: Ibrido casuale/sequenziale | `'mixed'` |

### Avvio del Miner

Assicurati che il tuo nodo Bitcoin Core sia in esecuzione e completamente avviato.

Esegui il miner dalla directory del progetto con il comando:

```bash
python main.py
```

Il programma si connetterà al nodo, inizierà a costruire blocchi candidati e avvierà il processo di hashing per trovare un nonce valido. Verranno visualizzati messaggi sullo stato del processo, inclusi i target di difficoltà, le transazioni incluse e l'hashrate.

Il thread watchdog monitorerà la rete. Se un altro miner trova un blocco prima di te, il tuo processo di mining verrà interrotto e riavviato con i dati aggiornati.

Se il tuo miner trova un blocco valido, lo invierà al nodo e visualizzerà un messaggio di conferma o un eventuale errore restituito dal nodo.

L'output del programma mostrerà:
- Informazioni sulla connessione RPC stabilita
- Il target di difficoltà corrente (originale e modificato se in regtest)
- Le transazioni incluse nel blocco candidato
- L'hashrate corrente durante il mining
- Messaggi di stato quando viene trovato un nuovo blocco sulla rete
- Conferma o errori quando si tenta di inviare un blocco minato
- Statistiche periodiche sulle performance del mining

**Nota:** Minare sulla rete principale (mainnet) con questo script è altamente improbabile che porti a trovare un blocco a causa dell'enorme potenza di calcolo richiesta. È consigliato utilizzarlo su `regtest` o `testnet` per scopi didattici e di sperimentazione.

## Licenza

Questo progetto è rilasciato sotto la licenza MIT.
