# Transazione Coinbase per Protocollo Stratum

Questo progetto è un programma di test per la costruzione di transazioni coinbase, sviluppato per essere implementato nel protocollo Stratum. Il software permette di comprendere e testare la creazione di coinbase transactions in modo didattico e personalizzabile.

## Scopo del Programma

Il programma serve come:
- **Strumento di test** per la costruzione di coinbase transactions
- **Base di sviluppo** per l'implementazione nel protocollo Stratum
- **Strumento didattico** per comprendere il funzionamento delle coinbase transactions
- **Ambiente di sperimentazione** con parametri completamente customizzabili

## Cos'è una Coinbase Transaction

### Definizione
La **coinbase transaction** è la prima transazione di ogni blocco Bitcoin. È una transazione speciale che:
- **Crea nuovi bitcoin** dal nulla (mining reward)
- **Raccoglie le commissioni** di tutte le transazioni del blocco
- **Non ha input validi** (non spende bitcoin esistenti)
- **Ha un solo output** che va al miner che ha minato il blocco

### Elementi di una Coinbase Transaction

#### 1. **Versione (Version)**
- Campo di 4 byte che specifica la versione del formato della transazione
- Solitamente `01000000` (versione 1 in little-endian)

#### 2. **Input Count**
- Sempre `01` (una sola input)
- Le coinbase hanno sempre esattamente un input

#### 3. **Input Coinbase**
- **Previous Transaction Hash**: 32 byte di zeri (`00000000...`)
- **Previous Output Index**: 4 byte di `0xFFFFFFFF`
- **Script Length**: lunghezza variabile del coinbase script
- **Coinbase Script**: contiene dati arbitrari e obbligatori
- **Sequence**: solitamente `0xFFFFFFFF`

#### 4. **Coinbase Script (Input Script)**
Il coinbase script contiene:
- **Altezza del blocco** (BIP34): obbligatoria dal blocco 227,836
- **Extranonce1 + Extranonce2**: per il mining distribuito (Stratum)
- **Messaggio personalizzato**: testo arbitrario del miner
- **Timestamp**: opzionale, per variare il contenuto

#### 5. **Output Count**
- Numero di output (solitamente 1 o 2)
- Se presente SegWit, può esserci un output aggiuntivo per il witness commitment

#### 6. **Output(s)**
- **Valore**: ricompensa del blocco + commissioni (in satoshi)
- **Script Length**: lunghezza dello script di output
- **Script PubKey**: script che definisce come spendere i bitcoin

#### 7. **Witness Commitment** (se SegWit)
- Output aggiuntivo con valore 0
- Contiene l'hash delle witness data di tutte le transazioni SegWit
- Formato: `OP_RETURN + 32 byte di commitment`

#### 8. **Lock Time**
- Campo di 4 byte, solitamente `00000000`
- Specifica quando la transazione può essere inclusa in un blocco

### Particolarità della Coinbase

#### **Creazione di Valore**
La coinbase è l'unica transazione che può creare bitcoin dal nulla. Il valore totale dell'output non può superare:
```
Ricompensa del blocco + Somma delle commissioni delle transazioni
```

#### **BIP34 - Altezza Obbligatoria**
Dal blocco 227,836, il coinbase script deve iniziare con l'altezza del blocco codificata:
- L'altezza viene codificata in formato little-endian
- Preceduta dalla sua lunghezza in byte
- Esempio: altezza 850000 → `03a0f90c`

#### **Stratum Mining**
Nel mining distribuito (pool), la coinbase contiene:
- **Extranonce1**: assegnato dalla pool al miner
- **Extranonce2**: generato dal miner per variare l'hash
- Questi valori permettono a ogni miner di lavorare su uno spazio di hash diverso

#### **SegWit Compatibility**
Per blocchi con transazioni SegWit:
- Deve essere presente un witness commitment
- Il commitment è calcolato dalle witness data di tutte le transazioni
- Viene inserito come output aggiuntivo con valore 0

## Come Funziona il Programma

### Struttura del Progetto

```
prototipo/
├── main.py              # Test generale della coinbase
├── test_coinbase.py     # Test con parametri customizzabili
├── config.py            # Configurazione RPC e parametri
├── builder.py           # Costruzione della coinbase transaction
├── rpc.py               # Comunicazione con il nodo Bitcoin
├── utils.py             # Funzioni di utilità
└── requirements.txt     # Dipendenze Python
```

### File Principali

#### **main.py** - Test Generale
Questo file genera una coinbase transaction corretta per il nodo Bitcoin a cui è collegato, utilizzando alcuni parametri customizzabili:

1. **Connessione RPC**: Si connette al nodo Bitcoin
2. **Richiesta Template**: Ottiene un template di blocco reale
3. **Analisi Transazioni**: Conta transazioni legacy e SegWit
4. **Modifica Difficoltà**: Applica un fattore di difficoltà personalizzato
5. **Costruzione Coinbase**: Crea la coinbase transaction corretta
6. **Validazione**: Verifica la correttezza della coinbase generata

```bash
python main.py
```

#### **test_coinbase.py** - Test Personalizzato
Questo file permette di testare la coinbase con parametri completamente customizzabili:

**Parametri Configurabili:**
```python
TEMPLATE = {
    "height": 850000,                    # Altezza del blocco
    "coinbasevalue": 625000000,          # Ricompensa in satoshi
    "default_witness_commitment": "...", # Commitment SegWit
    "curtime": 1703001600,               # Timestamp
    "bits": "17034a7d"                   # Difficoltà target
}

EXTRANONCE1 = "1234567890abcdef"         # Extranonce1 personalizzato
EXTRANONCE2 = "12345678"                 # Extranonce2 personalizzato
COINBASE_MESSAGE = "/Ciao sono Davide/"  # Messaggio personalizzato
```

```bash
python test_coinbase.py
```

### Configurazione

#### **config.py**
Contiene tutti i parametri di configurazione:

```python
# Connessione RPC al nodo Bitcoin
RPC_USER = "username"
RPC_PASSWORD = "password"
RPC_HOST = "IP_ADDRESS"
RPC_PORT = 8332

# Indirizzo del miner (dove vanno i bitcoin)
WALLET_ADDRESS = "bcrt1q..."

# Fattore di difficoltà (0 = difficoltà originale)
DIFFICULTY_FACTOR = 0

# Messaggio personalizzato nella coinbase
COINBASE_MESSAGE = "/Ciao sono Davide/"
```

### Moduli di Supporto

#### **builder.py**
- Costruisce la coinbase transaction completa
- Gestisce la codifica BIP34 dell'altezza
- Supporta transazioni SegWit e legacy
- Calcola correttamente tutti i campi

#### **rpc.py**
- Gestisce la comunicazione con il nodo Bitcoin
- Richiede template di blocco
- Supporta autenticazione RPC

#### **utils.py**
- Funzioni di utilità per hash e codifiche
- Gestione endianness
- Generazione di extranonce
- Salvataggio template per debug

## Installazione e Utilizzo

### Prerequisiti
- Python 3.8+
- Nodo Bitcoin in esecuzione
- Accesso RPC configurato

### Installazione
```bash
# Clona o scarica il progetto
cd prototipo

# Installa le dipendenze
pip install -r requirements.txt
```

### Configurazione
1. Modifica `config.py` con i tuoi parametri RPC
2. Imposta il tuo indirizzo wallet
3. Personalizza i messaggi e parametri

### Esecuzione
```bash
# Test generale con template reale
python main.py

# Test con parametri personalizzati
python test_coinbase.py
```

### Output Esempio
```
2024-01-01 12:00:00 | INFO | Transazioni nel template: totali = 150 | legacy = 120 | segwit = 30
2024-01-01 12:00:00 | INFO | Target modificato (DIFFICULTY_FACTOR=0): 0000000000034a7d...
2024-01-01 12:00:00 | INFO | Coinbase costruita: 250 byte
2024-01-01 12:00:00 | INFO | TXID: a1b2c3d4e5f6...
2024-01-01 12:00:00 | INFO | Hash: a1b2c3d4e5f6...
```

## Sviluppi Futuri

Questo prototipo può essere esteso per:
- Implementazione completa del protocollo Stratum
- Mining pool software
- Test più avanzati per il protocollo Stratum
- Simulatori di mining educativi

---

**Nota**: Questo è un software educativo e di test. Per uso in produzione, sono necessarie ulteriori validazioni e ottimizzazioni di sicurezza.