# Bitcoin Mining (RPC-Based)

Questo progetto è un semplice miner Bitcoin scritto interamente in Python e suddiviso in moduli. È pensato per scopi didattici e di test in ambiente **regtest**.

Il miner permette di modificare la difficoltà mediante il parametro ```DIFFICULTY_FACTOR``` e offre tre modalità differenti per l'elaborazione del nonce (incremental, random e mixed), per facilitare esperimenti e comprensione del processo di mining. Inoltre, è possibile personalizzare il messaggio nella transazione coinbase.

**Attenzione**: Questo miner è concepito esclusivamente per scopi di test in ambiente Regtest e non è adatto al mining competitivo in mainnet o testnet.

## Cosa puoi imparare:

- Come un nodo Bitcoin fornisce un template di blocco per il mining.
- Come vengono costruiti i blocchi, a partire dalla transazione coinbase fino al Merkle Root.
- Il processo di hashing e la ricerca di un nonce valido per soddisfare la difficoltà richiesta.
- L'invio del blocco minato al nodo per la validazione.
- Come inserire messaggi personalizzati nella transazione coinbase.

## Struttura del Progetto

Il progetto è organizzato in moduli per separare chiaramente le responsabilità:

- **```config.py```**: Contiene tutte le impostazioni di configurazione:
  - Parametri RPC (utente, password, host e porta)
  - Indirizzo del wallet del miner
  - Fattore di difficoltà regolabile (```DIFFICULTY_FACTOR```)
  - Modalità di calcolo del nonce (```NONCE_MODE```)
  - Messaggio personalizzato per la coinbase (```COINBASE_MESSAGE```)

- **```rpc.py```**: Gestisce le connessioni RPC al nodo Bitcoin con funzioni per:
  - Connettersi al nodo (```connect_rpc()```)
  - Verificare la connessione (```test_rpc_connection()```)
  - Ottenere il template del blocco (```get_block_template()```)
  - Aggiornare i dati witness delle transazioni (```ensure_witness_data()```)
  - Inviare il blocco minato (```submit_block()```)

- **```block_builder.py```**: Contiene la logica per la costruzione del blocco:
  - Funzioni di hashing (```double_sha256()```)
  - Decodifica nBits (```decode_nbits()```)
  - Costruzione transazione coinbase (```build_coinbase_transaction()```)
  - Calcolo Merkle Root (```calculate_merkle_root()```)
  - Serializzazione del blocco (```serialize_block()```)

- **```miner.py```**: Implementa gli algoritmi di mining con tre strategie:
  - **Incremental**: Scansione sequenziale da 0 a 2³²-1
  - **Random**: Generazione casuale ad ogni iterazione
  - **Mixed**: Nonce iniziale casuale con incrementi successivi

- **```main.py```**: Coordina il processo di mining con un ciclo continuo che:
  1. Verifica la connessione RPC
  2. Richiede e prepara il template del blocco
  3. Controlla le transazioni presenti
  4. Costruisce la transazione coinbase
  5. Modifica la difficoltà
  6. Calcola il Merkle Root
  7. Costruisce il blocco
  8. Esegue il mining
  9. Serializza il blocco
  10. Invia il blocco al nodo

## Configurazione

### File bitcoin.conf
```
regtest=1
server=1
rpcuser=tuo_utente
rpcpassword=tua_password
rpcallowip=127.0.0.1
rpcport=8332
```

### Parametri Principali (config.py)
| Parametro | Descrizione |
|-----------|-------------|
| RPC_HOST | Indirizzo IP del nodo Bitcoin |
| RPC_PORT | Porta RPC |
| DIFFICULTY_FACTOR | Moltiplica la difficoltà di base |
| NONCE_MODE | Strategia di ricerca nonce |
| COINBASE_MESSAGE | Messaggio nella transazione coinbase |

## Installazione
```bash
pip install -r requirements.txt
```

## Esecuzione
```bash
python main.py
```

## Funzionamento del Programma

Il miner implementa un ciclo di mining completo con i seguenti passaggi:

1. **Preparazione ambiente**
   - Verifica connessione RPC con il nodo Bitcoin
   - Controllo dello stato del wallet

2. **Acquisizione template**
   - Richiesta block template via RPC
   - Verifica presenza transazioni
   - Aggiornamento dati witness

3. **Costruzione blocco**
   - Creazione transazione coinbase con messaggio personalizzato
   - Calcolo Merkle Root
   - Aggiornamento versione blocco
   - Impostazione timestamp
   - Regolazione difficoltà (target nBits)

4. **Processo di mining**
   - Selezione strategia nonce (in base a NONCE_MODE)
   - Hashing sequenziale con SHA-256
   - Verifica target difficulty
   - Aggiornamento timestamp ogni 5 secondi

5. **Invio risultati**
   - Validazione blocco completato
   - Trasmissione via RPC con submit_block
   - Gestione errori e ripristino

6. **Gestione errori**
   - Reconnessione automatica RPC
   - Ritentativi su fallimenti di rete
   - Logging dettagliato degli errori

Il ciclo si ripete automaticamente dopo ogni blocco minato o in caso di errori risolvibili.

## Licenza
Progetto open-source disponibile sotto licenza MIT.