# Costruzione della Transazione Coinbase

Questo documento descrive il funzionamento dello script `coinbase.py`, focalizzandosi sulla costruzione della transazione coinbase, un elemento fondamentale nel processo di mining di Bitcoin.

## 1. Introduzione alla Transazione Coinbase

La transazione coinbase è un elemento fondamentale e unico all'interno di ogni blocco della blockchain Bitcoin. Questa particolare transazione occupa sempre la prima posizione nel blocco e presenta caratteristiche che la distinguono da tutte le altre:

1. **Creazione di Nuova Valuta:**
   - A differenza delle normali transazioni che spostano bitcoin esistenti, la coinbase genera nuovi bitcoin "dal nulla"
   - Questo processo è noto come *block reward* ed è il meccanismo principale con cui nuovi bitcoin entrano in circolazione
   - Il reward si dimezza ogni 210.000 blocchi (circa 4 anni) secondo il protocollo di halving

2. **Struttura Unica:**
   - Non ha UTXO (Unspent Transaction Output) in input
   - Utilizza un campo speciale chiamato "coinbase" al posto degli input tradizionali
   - Questo campo può contenere dati arbitrari fino a 100 byte

3. **Ricompense del Mining:**
   - Assegna il *block reward* al miner che ha risolto con successo il blocco
   - Include tutte le commissioni (*fees*) delle transazioni contenute nel blocco
   - La ricompensa totale è quindi: block reward + somma delle fees

4. **Maturità:**
   - Gli output della coinbase hanno regole speciali
   - Non possono essere spesi per 100 blocchi
   - Questa regola previene la spesa di monete in caso di riorganizzazione della blockchain

Lo script `coinbase.py` automatizza la creazione di questa transazione speciale, recuperando le informazioni necessarie da un nodo Bitcoin tramite RPC (Remote Procedure Call) e assemblando i dati secondo le regole del protocollo Bitcoin.

## 2. Configurazione

Lo script richiede alcuni parametri di configurazione iniziali:

*   **RPC Connection:**
    *   `RPC_USER`, `RPC_PASSWORD`: Credenziali per l'autenticazione RPC al nodo Bitcoin.
    *   `RPC_HOST`, `RPC_PORT`: Indirizzo IP e porta del nodo Bitcoin.
*   **Payout:**
    *   `WALLET_ADDRESS`: L'indirizzo Bitcoin del miner a cui verrà inviato il block reward.
*   **Coinbase Data:**
    *   `COINBASE_MESSAGE`: Un messaggio arbitrario che il miner può includere nella transazione (spesso usato per identificare la mining pool).
    *   `EXTRANONCE1`, `EXTRANONCE2`: Valori utilizzati nel protocollo Stratum per permettere ai miner di variare l'hash della coinbase senza dover richiedere un nuovo `block template` al nodo. `EXTRANONCE1` è solitamente fornito dal server Stratum, mentre `EXTRANONCE2` è iterato dal singolo worker/ASIC.

## 3. Struttura della Transazione Coinbase

Una transazione Bitcoin, inclusa la coinbase, è composta dai seguenti campi principali:

| **Campo**          | **Descrizione**                                         |
|--------------------|---------------------------------------------------------|
| **Versione**       | Indica le regole di validazione (solitamente 1 o 2)     |
| **Marker & Flag**  | Presenti solo se SegWit è attivo (0x00, 0x01)           |
| **Input Count**    | Numero di input (sempre 1 per la coinbase)              |
| **Inputs**         | Lista degli input                                       |
| **Output Count**   | Numero di output                                        |
| **Outputs**        | Lista degli output                                      |
| **Witness Data**   | Dati di witness (solo se SegWit è attivo)               |
| **Locktime**       | Solitamente 0 per la coinbase                           |

Ogni campo è descritto nel dettaglio nelle sezioni successive.

### 3.1 Versione (Version)

*   **Valore:** `01000000` (little-endian per 1) o `02000000` (little-endian per 2).
*   **Scopo:** Indica la versione della transazione. La versione 2 è usata per segnalare il supporto a funzionalità come `CheckSequenceVerify` (BIP 68/112/113).

### 3.2 Marker & Flag (SegWit)

*   **Valore:** `0001` (Marker `0x00`, Flag `0x01`).
*   **Scopo:** Presenti *solo* se la transazione include dati di witness (Segregated Witness - SegWit). Indicano che i dati di firma sono separati dal corpo principale della transazione.
*   **Logica Script:** Lo script aggiunge questi byte se il `block template` fornito dal nodo contiene un `default_witness_commitment`.

### 3.3 Input (Singolo)

La transazione coinbase ha sempre **un solo input** con caratteristiche specifiche:

*   **Previous Output (Prevout):**
    *   `TxID`: `0000...0000` (32 byte nulli). Indica che non spende output precedenti.
    *   `Index`: `ffffffff` (4 byte). Valore massimo, non applicabile.
*   **ScriptSig Length:** Lunghezza dello `scriptSig` codificata come VarInt.
*   **ScriptSig:** Contiene dati specifici invece di una firma:
    *   **Block Height (BIP-34):** L'altezza del blocco corrente, codificata in modo speciale. È obbligatoria per i blocchi con versione >= 2.
        *   *Codifica:* Il primo byte indica la lunghezza dei byte successivi che contengono l'altezza in formato little-endian. Esempio: altezza 2 -> `0102`; altezza 256 -> `020001`.
        *   *Funzione:* `tx_encode_coinbase_height`.
    *   **Arbitrary Data (Messaggio):** Dati opzionali scelti dal miner (es. `COINBASE_MESSAGE`). Lo script aggiunge `6a` (OP_RETURN) seguito dalla lunghezza del messaggio e dal messaggio stesso in esadecimale.
    *   **Extranonce:** Valori `EXTRANONCE1` e `EXTRANONCE2` concatenati. Permettono ai miner (specialmente in pool con Stratum) di modificare l'hash della coinbase senza ricostruire l'intera transazione o richiedere un nuovo template.
    *   *Limite:* La lunghezza totale dello `scriptSig` non deve superare i 100 byte.
*   **Sequence:** `ffffffff`. Indica che `nLockTime` e `CheckSequenceVerify` non sono applicati a questo input.

### 3.4 Output (Uno o Più)

La coinbase ha almeno un output, ma può averne di più:

*   **Output Count:** Numero di output codificato come VarInt.
*   **Output(s):**
    1.  **Miner Reward Output:**
        *   `Value`: Il valore del block reward + fees (in satoshi, little-endian, 8 byte). Ottenuto da `template['coinbasevalue']`.
        *   `ScriptPubKey Length`: Lunghezza dello `scriptPubKey` come VarInt.
        *   `ScriptPubKey`: Lo script che definisce le condizioni per spendere questo output (tipicamente P2PKH, P2SH, P2WPKH, P2WSH). Lo script lo ottiene dall'indirizzo `WALLET_ADDRESS` tramite `get_script_pubkey`.
    2.  **Witness Commitment Output (Opzionale, SegWit):**
        *   `Value`: `0000000000000000` (0 satoshi).
        *   `ScriptPubKey Length`: Lunghezza dello `scriptPubKey` come VarInt.
        *   `ScriptPubKey`: Uno script `OP_RETURN` che contiene l'hash della radice di Merkle dei dati di witness di tutte le transazioni nel blocco. Inizia con `6a24aa21a9ed` seguito dall'hash di 32 byte. Lo script lo prende da `template['default_witness_commitment']`.

### 3.5 Witness Data (SegWit)

*   **Valore:** `01` (numero di elementi stack) + `20` (lunghezza elemento) + `00...00` (32 byte nulli).
*   **Scopo:** Placeholder per i dati di witness della coinbase. Poiché la coinbase non spende output precedenti, non ha firme reali. Questo campo è richiesto per coerenza se SegWit è attivo.

### 3.6 Locktime

*   **Valore:** `00000000`.
*   **Scopo:** Generalmente impostato a 0 per le transazioni coinbase.

## 4. Split della Coinbase per Stratum

Il protocollo Stratum, usato nel mining in pool, richiede che la transazione coinbase sia divisa in due parti (`coinb1` e `coinb2`) attorno agli extranonce. Questo permette al server Stratum di inviare `coinb1` e `coinb2` una sola volta, e poi solo `extranonce1` aggiornato, mentre il miner itera su `extranonce2`.

*   `coinb1`: Parte della coinbase *prima* di `EXTRANONCE1`.
*   `coinb2`: Parte della coinbase *dopo* `EXTRANONCE2`.

La funzione `split_coinbase` esegue questo split, assicurandosi che `EXTRANONCE1` e `EXTRANONCE2` siano presenti e contigui nella coinbase generata.

## 5. Calcolo del Transaction ID (TxID)

Il TxID è l'identificatore univoco di una transazione. Si calcola applicando due volte l'hash SHA-256 ai dati serializzati della transazione e invertendo l'ordine dei byte (little-endian).

*   **Legacy TxID:** Calcolato sull'intera transazione serializzata.
*   **SegWit TxID (wtxid):** Calcolato sulla transazione serializzata *inclusi* Marker, Flag e Witness Data.
*   **TxID usato nel Block Header:** Per le transazioni SegWit, il TxID incluso nella radice di Merkle del blocco è calcolato sulla transazione *senza* Marker, Flag e Witness Data. Lo script calcola questo TxID legacy anche per le transazioni SegWit rimuovendo le parti pertinenti prima dell'hashing.

Lo script calcola e restituisce il TxID legacy (`txid`).

## 6. Dipendenze

*   `python-bitcoinrpc`: Per comunicare con il nodo Bitcoin. Installare con `pip install python-bitcoinrpc`.

## 7. Utilizzo

Eseguire lo script Python (`python coinbase.py`). Si connetterà al nodo Bitcoin specificato, otterrà un `block template`, costruirà la transazione coinbase e stamperà:

*   Dettagli del template (altezza, reward, SegWit).
*   Dimensioni degli extranonce.
*   La transazione coinbase completa in formato esadecimale (`coinbase_hex`).
*   Il TxID legacy della coinbase (`coinbase_txid`).
*   Le parti `coinb1`, `extranonce1`, `extranonce2`, `coinb2` per l'uso con Stratum.

## 8. Riferimenti

- [BIP-34: Block v2, Height in Coinbase](https://github.com/bitcoin/bips/blob/master/bip-0034.mediawiki)
- [BIP-141: Segregated Witness](https://github.com/bitcoin/bips/blob/master/bip-0141.mediawiki) 
- [Bitcoin Developer Reference](https://developer.bitcoin.org/reference/)
- [Bitcoin Core Source Code](https://github.com/bitcoin/bitcoin)
- [Stratum Mining Protocol](https://en.bitcoin.it/wiki/Stratum_mining_protocol)

## 9. Licenza

Questo script è rilasciato sotto la licenza MIT.