# Bitcoin Coinbase Transaction Generator

## Teoria della Coinbase Transaction

### Cos'è la Coinbase Transaction
La coinbase transaction è la prima transazione in ogni blocco Bitcoin. A differenza delle transazioni normali, essa non spende UTXO (Unspent Transaction Outputs) esistenti, ma crea nuovi bitcoin "dal nulla". Questa transazione speciale rappresenta il meccanismo attraverso cui nuovi bitcoin vengono emessi e distribuiti ai miner come ricompensa per il loro lavoro di validazione e sicurezza della rete.

### A cosa serve la Coinbase Transaction
La coinbase transaction svolge diverse funzioni fondamentali:

1. **Emissione di nuova valuta**: È l'unico meccanismo attraverso cui nuovi bitcoin entrano in circolazione, seguendo un programma di emissione predefinito.
2. **Ricompensa per i miner**: Distribuisce la ricompensa del blocco (block reward) e le commissioni delle transazioni (fees) al miner che ha risolto il blocco.
3. **Identificazione del blocco**: Contiene dati che rendono ogni blocco unico, prevenendo attacchi di tipo "duplicate mining".
4. **Comunicazione**: Permette ai miner di includere messaggi arbitrari (coinbase message) che vengono registrati permanentemente nella blockchain.

### Caratteristiche distintive rispetto alle transazioni normali

| Caratteristica | Coinbase Transaction | Transazioni Normali |
|----------------|----------------------|---------------------|
| **Input** | Non ha input reali, ma un input "fittizio" con hash di transazione nullo (32 byte di zeri) | Deve spendere UTXO esistenti e validi |
| **Sequence** | Solitamente impostato a 0xFFFFFFFF | Può variare in base a requisiti di timelock |
| **ScriptSig** | Contiene l'altezza del blocco (BIP34), extranonce e messaggi arbitrari | Contiene firme che provano la proprietà degli UTXO |
| **Output** | Primo output destinato al miner, eventuale secondo output per witness commitment | Qualsiasi numero di output a qualsiasi indirizzo |
| **Valore** | Somma di block reward + fees delle transazioni | Limitato agli UTXO spesi meno le fees |
| **Maturità** | Richiede 100 conferme prima di poter essere spesa | Spendibile dopo 1 conferma (o anche 0 per transazioni a basso rischio) |

### Struttura della Coinbase Transaction

1. **Version** (4 bytes): Versione del formato della transazione.
2. **Input Count** (1-9 bytes, VarInt): Sempre 1 per la coinbase.
3. **Input**:
   - **Previous Transaction Hash** (32 bytes): Tutti zeri.
   - **Previous Output Index** (4 bytes): 0xFFFFFFFF.
   - **ScriptSig Length** (1-9 bytes, VarInt): Lunghezza dello script.
   - **ScriptSig**: Contiene:
     - Altezza del blocco (BIP34)
     - Extranonce (per mining)
     - Messaggi arbitrari
   - **Sequence** (4 bytes): Solitamente 0xFFFFFFFF.
4. **Output Count** (1-9 bytes, VarInt): 1 o 2 (se SegWit).
5. **Outputs**:
   - **Value** (8 bytes): Ricompensa + fees.
   - **ScriptPubKey Length** (1-9 bytes, VarInt): Lunghezza dello script.
   - **ScriptPubKey**: Script che definisce le condizioni per spendere l'output.
   - (Opzionale) Secondo output per witness commitment in blocchi SegWit.
6. **Locktime** (4 bytes): Solitamente 0.

### Evoluzione storica
- **BIP34**: Ha reso obbligatorio includere l'altezza del blocco nello scriptSig.
- **BIP141 (SegWit)**: Ha introdotto il witness commitment come secondo output.
- **Taproot**: Ha aggiunto supporto per nuovi tipi di script più efficienti e privati.

## Funzionamento del Programma

### Panoramica
Questo software implementa un generatore di transazioni coinbase completo, con supporto per il protocollo Stratum v1 utilizzato nelle mining pool. Il programma si connette a un nodo Bitcoin, ottiene un template del blocco, e costruisce una transazione coinbase valida secondo le specifiche del protocollo.

### Componenti principali

#### 1. Connessione RPC al nodo Bitcoin
Il programma utilizza la libreria `python-bitcoinrpc` per comunicare con un nodo Bitcoin attraverso chiamate RPC (Remote Procedure Call):

```python
def connect_rpc():
    """Crea una connessione RPC al nodo Bitcoin utilizzando i parametri di configurazione."""
    connection_url = f"http://{RPC_USER}:{RPC_PASSWORD}@{RPC_HOST}:{RPC_PORT}"
    return AuthServiceProxy(connection_url)
```

Questa connessione permette di ottenere informazioni aggiornate sulla blockchain e richiedere un template per il nuovo blocco da minare.

#### 2. Ottenimento del Block Template
Il programma richiede un template del blocco al nodo Bitcoin, che contiene tutte le informazioni necessarie per costruire un blocco valido:

```python
def get_block_template(rules=None):
    """Ottiene un template per un nuovo blocco dal nodo Bitcoin."""
    if rules is None:
        rules = ["segwit"]
    
    rpc = connect_rpc()
    return rpc.getblocktemplate({"rules": rules})
```

Il template include:
- L'altezza del blocco
- Il valore della coinbase (ricompensa + fees)
- Le transazioni da includere
- Il witness commitment (per blocchi SegWit)
- Altri parametri necessari per il mining

#### 3. Costruzione della Coinbase Transaction
Il cuore del programma è la funzione `build_coinbase_tx()` che costruisce la transazione coinbase seguendo le specifiche del protocollo Bitcoin:

```python
def build_coinbase_tx(coinbase_value: int, coinbase_address: str, coinbase_message: str, block_template: dict) -> str:
    # Implementazione dettagliata...
```

Questa funzione:
1. Determina se SegWit è attivo
2. Costruisce l'input della coinbase con:
   - Hash di transazione nullo
   - Altezza del blocco (BIP34)
   - Extranonce (per mining)
   - Messaggio personalizzato
3. Crea gli output:
   - Output principale con la ricompensa al miner
   - Output opzionale per witness commitment (SegWit)
4. Assembla la transazione completa

#### 4. Gestione degli Indirizzi Bitcoin
Il programma supporta indirizzi Bech32 (SegWit nativi) e li converte nel corrispondente scriptPubKey:

```python
def address_to_scriptPubKey(address):
    """Converte un indirizzo Bitcoin in scriptPubKey."""
    # Implementazione per decodifica Bech32 e conversione...
```

#### 5. Divisione della Coinbase per Stratum
Per l'integrazione con il protocollo Stratum v1, la coinbase viene divisa in componenti:

```python
def split_coinbase(tx_hex: str) -> (str, str, str, str):
    """Divide la coinbase transaction in coinb1, extranonce1, extranonce2, coinb2."""
    # Implementazione...
```

Questa divisione permette alle mining pool di distribuire il lavoro tra i miner, consentendo loro di modificare solo l'extranonce2 per generare hash diversi.

### Flusso di esecuzione

1. Il programma si connette al nodo Bitcoin
2. Richiede un block template aggiornato
3. Calcola il valore della coinbase (ricompensa + fees)
4. Costruisce la transazione coinbase con:
   - Altezza del blocco corrente
   - Extranonce configurato
   - Messaggio personalizzato
   - Indirizzo di destinazione
5. Se SegWit è attivo, aggiunge il witness commitment
6. Divide la coinbase in componenti per Stratum
7. Visualizza la transazione completa e i suoi componenti

## Requisiti e Configurazione

### Requisiti
- Python 3.7+
- Accesso a un nodo Bitcoin
- Dipendenze Python (installabili via requirements.txt):
  - `python-bitcoinrpc`
  - `base58`
  - `requests`

### Configurazione
Modifica le seguenti variabili nel file `coinbase.py`:

```python
# Configurazioni RPC
RPC_USER = 'tuo_username_rpc'
RPC_PASSWORD = 'tua_password_rpc'
RPC_HOST = 'indirizzo_nodo'
RPC_PORT = '8332'

# Configurazioni Coinbase
COINBASE_ADDRESS = 'bc1q...'  # Il tuo indirizzo Bitcoin (Bech32)
COINBASE_MESSAGE = '/Il tuo messaggio personalizzato/'

# Extranonce per mining
EXTRANONCE1 = '12345678'  # 8 byte
EXTRANONCE2 = 'abcd'      # 4 byte
```

## Installazione e Utilizzo

1. Clona il repository
2. Installa le dipendenze:
   ```bash
   pip install -r requirements.txt
   ```
3. Configura i parametri nel file `coinbase.py`
4. Esegui il programma:
   ```bash
   python coinbase.py
   ```

## Sicurezza e Considerazioni

Questo software è fornito "così com'è", senza garanzie. Si consiglia di testare accuratamente in ambiente di sviluppo prima dell'uso in produzione. Prestare particolare attenzione alla gestione delle credenziali RPC e assicurarsi che il nodo Bitcoin sia configurato in modo sicuro.

## Licenza

Questo progetto è rilasciato sotto licenza MIT.

## Contribuire

Se desideri contribuire al progetto:
1. Fai un fork del repository
2. Crea un branch per le tue modifiche
3. Invia una pull request
