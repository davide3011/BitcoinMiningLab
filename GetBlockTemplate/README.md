# Bitcoin Mining (GetBlockTemplate)

Questo progetto implementa un sistema completo di mining Bitcoin educativo che utilizza il protocollo **GetBlockTemplate** per interagire con un nodo Bitcoin Core tramite chiamate RPC (Remote Procedure Call). Il programma è progettato specificamente per scopi didattici e di apprendimento, offrendo una comprensione approfondita dei meccanismi interni del mining di Bitcoin, dalla costruzione dei blocchi al processo di Proof-of-Work.

## Caratteristiche Principali

- **Implementazione completa del protocollo Stratum v1** per la comunicazione mining
- **Supporto multi-processo** per il mining parallelo
- **Gestione avanzata delle transazioni SegWit** e legacy
- **Costruzione dinamica della transazione coinbase** con extranonce personalizzabili
- **Calcolo ottimizzato del Merkle Root** per blocchi con molte transazioni
- **Sistema di watchdog** per il rilevamento di nuovi blocchi sulla rete
- **Configurazione flessibile della difficoltà** per ambienti di test
- **Logging dettagliato** e metriche di performance in tempo reale

## Funzionamento Teorico del Mining di Bitcoin

Il mining di Bitcoin è il processo attraverso il quale nuove transazioni vengono verificate e aggiunte a un registro pubblico distribuito chiamato blockchain. È anche il meccanismo attraverso il quale vengono creati nuovi bitcoin.

I miner competono per risolvere un complesso problema matematico basato su una funzione di hash crittografica (SHA-256 nel caso di Bitcoin). Il primo miner che trova una soluzione valida, chiamata "proof-of-work" (PoW), ha il diritto di aggiungere un nuovo blocco di transazioni alla blockchain e viene ricompensato con una certa quantità di bitcoin (la "ricompensa del blocco") più le commissioni di transazione incluse nel blocco.

Il processo di mining coinvolge i seguenti passaggi chiave:

1.  **Raccolta delle Transazioni**: I miner raccolgono le transazioni in sospeso dalla rete Bitcoin.
2.  **Costruzione del Blocco Candidato**: I miner creano un "blocco candidato" che include:
    *   Un riferimento (hash) al blocco precedente nella blockchain.
    *   Un insieme di transazioni valide (inclusa una speciale transazione "coinbase" che assegna la ricompensa del blocco al miner).
    *   Un timestamp.
    *   Un valore di "difficoltà target" che determina quanto deve essere difficile trovare la soluzione PoW.
    *   Un campo "nonce" (number used once), un numero che i miner modificano ripetutamente.
3.  **Ricerca del Nonce (Proof-of-Work)**: Questo è il cuore del processo di mining. I miner modificano il valore del nonce nell'header del blocco candidato e calcolano l'hash SHA-256 dell'header. L'obiettivo è trovare un nonce tale per cui l'hash risultante sia inferiore al target di difficoltà. Poiché le funzioni di hash sono imprevedibili, questo processo richiede una grande quantità di tentativi (calcoli di hash).
4.  **Validazione e Propagazione del Blocco**: Una volta che un miner trova un nonce valido, trasmette il blocco alla rete Bitcoin. Gli altri nodi verificano la validità del blocco (correttezza delle transazioni, validità del PoW, ecc.). Se il blocco è valido, viene aggiunto alla loro copia della blockchain e il miner riceve la ricompensa.
5.  **Aggiustamento della Difficoltà**: La difficoltà di mining viene aggiustata circa ogni 2016 blocchi (circa due settimane) per garantire che, in media, venga trovato un nuovo blocco ogni 10 minuti, indipendentemente dalla potenza di calcolo totale della rete.

## Architettura del Sistema

Questo sistema di mining educativo è strutturato in modo modulare per facilitare la comprensione dei diversi aspetti del mining Bitcoin. Il programma simula un ambiente di mining reale, interagendo con un nodo Bitcoin Core locale (tipicamente in modalità `regtest` o `testnet` per scopi di sviluppo e test).

### Struttura Modulare

Il progetto è organizzato in moduli specializzati, ognuno responsabile di un aspetto specifico del processo di mining:

- **`launcher.py`**: Orchestratore principale e gestore multi-processo
- **`main.py`**: Logica core del mining per singolo worker
- **`miner.py`**: Implementazione dell'algoritmo Proof-of-Work
- **`block_builder.py`**: Costruzione e serializzazione dei blocchi Bitcoin
- **`rpc.py`**: Interfaccia di comunicazione con Bitcoin Core
- **`utils.py`**: Funzioni crittografiche e di utilità
- **`config.py`**: Configurazione centralizzata del sistema

### Flusso di Esecuzione

L'esecuzione del programma segue un pattern coordinato che rispecchia il funzionamento di un mining pool reale:

Ecco una descrizione dettagliata dei principali componenti e del flusso di lavoro:

1.  **`launcher.py` (Punto di Ingresso e Supervisore)**:
    *   È lo script principale da eseguire per avviare il miner.
    *   Utilizza il modulo `multiprocessing` per creare e gestire un pool di processi worker (`_worker` function).
    *   Ogni worker esegue una propria istanza del processo di mining (basato su `main.py`).
    *   `launcher.py` definisce dei pattern (espressioni regolari) per interpretare i log prodotti dai worker, estraendo informazioni come l'hashrate, i tentativi e la notifica di blocchi trovati.
    *   La funzione `_aggregate` raccoglie le metriche dai worker (tramite una coda `mp.Queue`) e stampa uno stato aggregato dell'attività di mining.
    *   Quando un worker trova un blocco e questo viene sottomesso con successo, `launcher.py` riavvia tutti i worker per iniziare un nuovo ciclo di mining con un template di blocco aggiornato.
    *   Gestisce la distribuzione di `extranonce2` univoci a ciascun worker. L'`extranonce` è una porzione di dati aggiuntiva che i miner possono variare nella transazione coinbase per aumentare lo spazio di ricerca del nonce, specialmente in ambienti di mining parallelo.

2.  **`main.py` (Logica Principale del Singolo Worker)**:
    *   Questo script contiene la logica di un singolo processo di mining.
    *   **Connessione RPC**: Inizia stabilendo una connessione RPC con il nodo Bitcoin Core utilizzando le credenziali definite in `config.py` (funzione `connect_rpc` da `rpc.py`).
    *   **Ottenimento del Template del Blocco**: Richiede un template di blocco al nodo (`get_block_template` da `rpc.py`). Questo template contiene le transazioni da includere, l'hash del blocco precedente, la difficoltà, ecc.
    *   **Costruzione della Transazione Coinbase**: Crea la transazione coinbase (`build_coinbase_transaction` da `block_builder.py`). Questa transazione speciale:
        *   Include la ricompensa del blocco e le commissioni.
        *   Assegna la ricompensa all'indirizzo del miner specificato in `config.py`.
        *   Include l'altezza del blocco (BIP34).
        *   Può includere un messaggio personalizzato (`COINBASE_MESSAGE` da `config.py`).
        *   Incorpora `EXTRANONCE1` (fisso) e `EXTRANONCE2` (variabile per worker, fornito da `launcher.py`).
    *   **Modifica del Target di Difficoltà**: La funzione `modifica_target` permette di aggiustare la difficoltà di mining. Su `regtest`, può essere impostato un `DIFFICULTY_FACTOR` in `config.py` per rendere il mining più facile o difficile. Su `testnet` o `mainnet`, il fattore è forzato a 1 (usa la difficoltà della rete).
    *   **Calcolo del Merkle Root**: Calcola il Merkle root di tutte le transazioni nel blocco (inclusa la coinbase) (`calculate_merkle_root` da `block_builder.py`). Il Merkle root è un hash che riassume tutte le transazioni in modo efficiente.
    *   **Costruzione dell'Header del Blocco**: Assembla l'header del blocco (`build_block_header` da `block_builder.py`) utilizzando la versione del blocco, l'hash del blocco precedente, il Merkle root, il timestamp, il campo `bits` (difficoltà compatta) e un nonce iniziale (solitamente 0).
    *   **Watchdog per Nuovi Blocchi**: Avvia un thread `watchdog_bestblock` che controlla periodicamente se un nuovo blocco è stato trovato sulla rete. Se sì, segnala al processo di mining di fermarsi e ricominciare con un template aggiornato, per evitare di minare su una catena obsoleta.
    *   **Processo di Mining (Proof-of-Work)**: Chiama la funzione `mine_block` da `miner.py` per iniziare la ricerca del nonce.
    *   **Serializzazione del Blocco**: Se viene trovato un nonce valido, il blocco completo (header + transazioni) viene serializzato in formato esadecimale (`serialize_block` da `block_builder.py`).
    *   **Invio del Blocco**: Il blocco serializzato viene inviato al nodo Bitcoin Core per la validazione (`submit_block` da `rpc.py`). Se il nodo accetta il blocco, questo viene aggiunto alla blockchain.
    *   Il ciclo si ripete per minare il blocco successivo.

3.  **`miner.py` (Algoritmo di Mining - Proof-of-Work)**:
    *   Contiene la funzione `mine_block` che implementa l'algoritmo di ricerca del nonce.
    *   **Preparazione**: Decodifica l'header del blocco (senza il nonce) e il target di difficoltà.
    *   **Ottimizzazione Midstate**: Precalcola una parte dell'hash SHA-256 (`_midstate`) sull'header del blocco (escluso il nonce e gli ultimi 4 byte del timestamp, se l'aggiornamento del timestamp è attivo). Questo ottimizza il processo di hashing poiché questa parte dell'header non cambia ad ogni tentativo di nonce.
    *   **Iterazione sul Nonce**: Entra in un ciclo in cui:
        *   Modifica il valore del nonce nell'header. Le modalità di scelta del nonce (`NONCE_MODE` in `config.py`) possono essere:
            *   `incremental`: Il nonce viene incrementato linearmente.
            *   `random`: Il nonce viene scelto casualmente ad ogni iterazione (o batch).
            *   `mixed`: Il nonce iniziale è casuale, poi viene incrementato.
        *   **Aggiornamento Timestamp (Opzionale)**: Se `TIMESTAMP_UPDATE_INTERVAL` in `config.py` è impostato, il timestamp nell'header del blocco viene aggiornato periodicamente. Questo è utile perché il timestamp è uno dei campi che, se modificato, cambia l'hash dell'header, offrendo un ulteriore spazio di ricerca se tutti i nonce sono stati provati per un dato timestamp.
        *   **Calcolo dell'Hash**: Calcola il doppio SHA-256 dell'header del blocco completo (con il nonce corrente).
        *   **Confronto con il Target**: Confronta l'hash risultante (interpretato come un numero intero) con il target di difficoltà. Se l'hash è inferiore al target, un nonce valido è stato trovato.
        *   **Logging**: Stampa periodicamente l'hashrate corrente e il numero di tentativi.
        *   **Interruzione**: Controlla l'evento `stop_event`. Se è settato (ad esempio, dal watchdog di `main.py` perché è stato trovato un nuovo blocco sulla rete), il mining si interrompe.
    *   **Restituzione**: Se viene trovato un nonce valido, restituisce l'header completo del blocco (con il nonce vincente), il nonce stesso e l'hashrate medio.

4.  **`block_builder.py` (Costruzione dei Blocchi)**:
    *   Fornisce funzioni specializzate per costruire le varie parti di un blocco Bitcoin:
        *   `tx_encode_coinbase_height`: Codifica l'altezza del blocco per la transazione coinbase (BIP34).
        *   `is_segwit_tx`: Verifica se una transazione è in formato SegWit.
        *   `build_coinbase_transaction`: Costruisce la transazione coinbase completa.
        *   `calculate_merkle_root`: Calcola il Merkle root delle transazioni.
        *   `build_block_header`: Assembla l'header del blocco.
        *   `serialize_block`: Serializza l'intero blocco (header + transazioni) nel formato di rete.

5.  **`utils.py` (Funzioni di Utilità Comuni)**:
    *   Modulo centralizzato contenente funzioni di utilità condivise tra i vari componenti:
        *   `double_sha256`: Calcola il doppio hash SHA-256.
        *   `encode_varint` / `decode_varint`: Codifica/decodifica numeri interi nel formato VarInt di Bitcoin.
        *   `decode_nbits`: Converte il campo `bits` (difficoltà compatta) nel target di difficoltà a 256 bit.
        *   `calculate_target`: Calcola e modifica il target di difficoltà in base alla rete e al fattore configurato.

6.  **`rpc.py` (Interazione con Bitcoin Core)**:
    *   Contiene funzioni per interagire con il nodo Bitcoin Core tramite RPC:
        *   `connect_rpc`: Stabilisce la connessione.
        *   `test_rpc_connection`: Verifica la connessione.
        *   `get_best_block_hash`: Ottiene l'hash del blocco più recente.
        *   `get_block_template`: Richiede un template di blocco.
        *   `submit_block`: Invia un blocco minato al nodo.

7.  **`config.py` (Configurazione)**:
    *   Contiene i parametri di configurazione del miner:
        *   Credenziali RPC (`RPC_USER`, `RPC_PASSWORD`, `RPC_HOST`, `RPC_PORT`).
        *   Indirizzo del wallet del miner (`WALLET_ADDRESS`) a cui inviare la ricompensa.
        *   `DIFFICULTY_FACTOR`: Per regolare la difficoltà in `regtest`.
        *   `NONCE_MODE`: Strategia di ricerca del nonce.
        *   `TIMESTAMP_UPDATE_INTERVAL`: Frequenza di aggiornamento del timestamp nell'header durante il mining.
        *   `COINBASE_MESSAGE`: Messaggio personalizzato da includere nella transazione coinbase.

### Algoritmo del Programma (Semplificato)

1.  **Avvio (`launcher.py`)**: Lancia N processi worker.
2.  **Ogni Worker (`main.py`)**:
    a.  Si connette al nodo Bitcoin.
    b.  Richiede un `block_template`.
    c.  Costruisce la `coinbase_transaction` (con `extranonce2` univoco).
    d.  Calcola il `merkle_root`.
    e.  Costruisce l'`block_header` (con nonce iniziale).
    f.  Avvia il `watchdog_bestblock`.
    g.  Chiama `mine_block` (`miner.py`) passando l'header e il target.
3.  **Mining (`miner.py`)**:
    a.  Ciclo infinito (o fino a `stop_event`):
        i.  Prepara l'header con il nonce corrente.
        ii. Aggiorna il timestamp nell'header (se configurato e intervallo trascorso).
        iii. Calcola `hash = double_sha256(header)`.
        iv. Se `hash < target_difficulty`, blocco trovato! Restituisce header, nonce, hashrate.
        v.  Incrementa/cambia il nonce.
4.  **Worker (`main.py`) dopo `mine_block`**:
    a.  Se `mine_block` è stato interrotto (nuovo blocco sulla rete), ricomincia dal punto 2b.
    b.  Altrimenti (blocco trovato dal worker):
        i.  Serializza il blocco completo.
        ii. Invia il blocco al nodo Bitcoin (`submit_block`).
5.  **Supervisore (`launcher.py`)**: Monitora i messaggi dai worker. Se un blocco è stato inviato con successo, termina e riavvia tutti i worker per il ciclo successivo.

## Come si Usa

1.  **Prerequisiti**:
    *   Python 3.x installato.
    *   Un nodo Bitcoin Core in esecuzione e completamente sincronizzato (o in modalità `regtest` o `testnet`).
    *   La libreria `python-bitcoinrpc` installata. Puoi installarla con pip:
        ```bash
        pip install python-bitcoinrpc
        ```
        Assicurati che sia presente nel file `requirements.txt` se intendi usare un ambiente virtuale.

2.  **Configurazione (`config.py`)**:
    *   Apri il file `config.py`.
    *   Imposta `RPC_USER`, `RPC_PASSWORD`, `RPC_HOST` e `RPC_PORT` in modo che corrispondano alla configurazione RPC del tuo nodo Bitcoin Core. Queste informazioni si trovano solitamente nel file `bitcoin.conf` del tuo nodo.
        *   Per `regtest` o `testnet`, `RPC_PORT` è spesso `18443` o `18332` rispettivamente.
    *   Imposta `WALLET_ADDRESS` con un indirizzo valido del tuo wallet Bitcoin (generato dal tuo nodo) a cui verranno inviate le ricompense del mining.
    *   (Opzionale) Modifica `DIFFICULTY_FACTOR` se stai usando `regtest` e vuoi rendere il mining più facile (valori < 1, es. 0.01) o più difficile (valori > 1). Un valore di `0` usa la difficoltà di rete.
    *   (Opzionale) Scegli `NONCE_MODE` tra `incremental`, `random`, o `mixed`.
    *   (Opzionale) Imposta `TIMESTAMP_UPDATE_INTERVAL` (in secondi) se vuoi che il timestamp nell'header venga aggiornato durante il mining. `0` o `None` per disabilitare.
    *   (Opzionale) Personalizza `COINBASE_MESSAGE`.

3.  **Avvio del Miner**:
    *   Apri un terminale o prompt dei comandi.
    *   Naviga nella directory del progetto.
    *   Esegui il `launcher.py`:
        ```bash
        python launcher.py
        ```
    *   Il `launcher.py` accetta alcuni argomenti da riga di comando:
        *   `-n` o `--num-processes`: Numero di processi worker da avviare (default: numero di CPU).
        *   `--extranonce2-base`: Valore esadecimale di base per `extranonce2` (default: "00000000"). Ogni worker userà `base + indice_worker`.

        Esempio per avviare con 4 processi worker:
        ```bash
        python launcher.py -n 4
        ```

4.  **Monitoraggio**:
    *   Il `launcher.py` stamperà nel terminale l'hashrate aggregato e il numero totale di tentativi.
    *   Quando un worker trova un blocco, verranno visualizzati i dettagli e l'esito dell'invio al nodo.
    *   I singoli worker (tramite `main.py` e `miner.py`) producono log più dettagliati che vengono catturati e parzialmente interpretati dal `launcher.py`.

5.  **Interruzione**:
    *   Per fermare il miner, puoi premere `Ctrl+C` nel terminale dove `launcher.py` è in esecuzione.

## Aspetti Didattici e Educativi

### Cosa Imparerai

Questo progetto offre un'esperienza pratica completa sui seguenti concetti fondamentali:

1. **Protocollo GetBlockTemplate**: Comprensione del protocollo standard utilizzato dai mining pool per distribuire il lavoro ai miner
2. **Costruzione dei Blocchi Bitcoin**: Processo step-by-step di assemblaggio di un blocco valido
3. **Transazioni Coinbase**: Creazione e gestione della transazione speciale che assegna la ricompensa del mining
4. **Merkle Tree**: Implementazione pratica dell'algoritmo per il calcolo del Merkle Root
5. **Proof-of-Work**: Algoritmo di consenso e ricerca del nonce valido
6. **Gestione SegWit**: Supporto per transazioni Segregated Witness
7. **Mining Parallelo**: Coordinamento di processi multipli per ottimizzare la ricerca
8. **Comunicazione RPC**: Interazione diretta con un nodo Bitcoin Core

### Esperimenti Didattici Suggeriti

1. **Modifica della Difficoltà**: Sperimenta con diversi valori di `DIFFICULTY_FACTOR` per osservare l'impatto sui tempi di mining
2. **Analisi delle Performance**: Confronta l'hashrate con diversi numeri di processi worker
3. **Studio delle Transazioni**: Esamina come diverse tipologie di transazioni influenzano la costruzione del blocco
4. **Ottimizzazioni**: Modifica l'algoritmo di ricerca del nonce per testare diverse strategie
5. **Monitoraggio della Rete**: Osserva come il sistema reagisce ai nuovi blocchi trovati da altri miner

### Strumenti di Debug e Analisi

Il programma include diversi strumenti per facilitare l'apprendimento:

- **Logging Dettagliato**: Ogni fase del processo è documentata nei log
- **Metriche in Tempo Reale**: Hashrate, tentativi, e statistiche di performance
- **Serializzazione dei Blocchi**: Possibilità di esaminare la struttura binaria dei blocchi
- **Validazione Step-by-Step**: Verifica di ogni componente prima dell'assemblaggio finale

### Note Importanti per l'Uso

*   **Ambiente di Test**: È fortemente consigliato utilizzare questo miner su reti di test come `regtest` (modalità di regression testing locale) o `testnet`. Minare sulla `mainnet` (la rete Bitcoin principale) con questo software è altamente improbabile che porti a trovare blocchi validi a causa dell'enorme difficoltà e della potenza di calcolo richiesta, dominata da hardware specializzato (ASIC).
*   **Configurazione del Nodo Bitcoin Core**: Assicurati che il tuo nodo Bitcoin Core sia configurato per accettare connessioni RPC (tipicamente impostando `server=1`, `rpcuser`, `rpcpassword` nel file `bitcoin.conf`). Per `regtest`, potresti dover generare blocchi iniziali manualmente per attivare la catena (`bitcoin-cli -regtest generate 101`).
*   **Scopo Educativo**: Questo progetto è inteso principalmente per comprendere i meccanismi interni del mining di Bitcoin. Non è ottimizzato per il mining competitivo ma per l'apprendimento e la sperimentazione.
*   **Sicurezza**: Utilizza sempre credenziali RPC sicure e non esporre mai il nodo Bitcoin Core su reti pubbliche durante i test.

## Licenza

Questo progetto è distribuito con la licenza MIT. Consulta il file `LICENSE` per maggiori dettagli.
