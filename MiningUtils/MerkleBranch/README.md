# Merkle Branch e Merkle Root in Bitcoin

## Introduzione

Questo script Python permette di interagire con un nodo Bitcoin tramite chiamate RPC per recuperare informazioni sui blocchi e calcolare il merkle branch e la merkle root delle transazioni contenute in un blocco.

Il programma è un utile strumento didattico per comprendere i concetti fondamentali di Merkle Tree, Merkle Root e Merkle Branch, elementi essenziali dell'architettura Bitcoin che garantiscono l'integrità e la verificabilità delle transazioni in modo efficiente.

## Concetti Chiave

### Merkle Tree

Un Merkle Tree (o albero di hash) è una struttura dati ad albero binario dove:

- Le foglie dell'albero sono gli hash delle transazioni (TxID)
- Ogni nodo non-foglia è l'hash dei suoi due nodi figli
- La radice dell'albero (Merkle Root) è un singolo hash che rappresenta tutte le transazioni

In Bitcoin, il Merkle Tree viene utilizzato per riassumere tutte le transazioni in un blocco, permettendo di verificare in modo efficiente l'appartenenza di una transazione a un blocco senza dover conoscere tutte le altre transazioni.

![Merkle Tree](https://upload.wikimedia.org/wikipedia/commons/9/95/Hash_Tree.svg)

### Merkle Root

La Merkle Root è l'hash che rappresenta la radice del Merkle Tree ed è inclusa nell'header del blocco Bitcoin. Questo singolo hash di 32 byte riassume crittograficamente tutte le transazioni contenute nel blocco.

L'inclusione della Merkle Root nell'header del blocco è fondamentale per il funzionamento di Bitcoin perché:

1. Permette di verificare l'integrità di tutte le transazioni nel blocco
2. Consente ai nodi di validare l'intero blocco senza dover scaricare tutte le transazioni (SPV - Simplified Payment Verification)
3. Rende computazionalmente impossibile modificare una transazione senza alterare l'header del blocco e, di conseguenza, l'intero proof-of-work

### Merkle Branch

Il Merkle Branch (o Merkle Path) è l'insieme degli hash necessari per verificare che una transazione specifica sia inclusa nel blocco, senza dover conoscere tutte le transazioni. È essenzialmente il percorso dal nodo foglia (la transazione) fino alla radice del Merkle Tree, includendo tutti i nodi "fratelli" necessari per il calcolo.

Per una blockchain con milioni di transazioni, il Merkle Branch permette di verificare l'appartenenza di una transazione con solo log₂(n) hash, dove n è il numero di transazioni nel blocco. Ad esempio, per un blocco con 1 milione di transazioni, sono necessari solo circa 20 hash per la verifica, invece di 1 milione.

## Algoritmo per il Calcolo del Merkle Branch

L'algoritmo implementato nello script per calcolare il Merkle Branch funziona come segue:

1. Inizia con la lista di tutti i TxID nel blocco (le foglie del Merkle Tree)
2. Converte i TxID da formato esadecimale a byte e inverte l'ordine (da little-endian a big-endian)
3. Per ogni livello dell'albero:
   - Se il numero di elementi è dispari, duplica l'ultimo nodo
   - Scorre i nodi a coppie per calcolare i nodi del livello superiore
   - Se il TxID scelto è in una coppia, salva l'hash del nodo fratello nel Merkle Branch
   - Calcola il nodo padre combinando i due nodi figli e applicando il doppio SHA256
4. Continua finché non rimane un solo nodo (la Merkle Root)
5. Restituisce la lista degli hash che compongono il Merkle Branch

```python
def merkle_branch(txids, index):
    # Converte i txid da esadecimale a byte e inverte l'ordine
    current_level = [bytes.fromhex(tx)[::-1] for tx in txids]
    branch = []  # Lista che conterrà gli hash del merkle branch
    current_index = index  # Indice corrente del nodo nel livello attuale
    
    # Continua finché non rimane un solo nodo (la merkle root)
    while len(current_level) > 1:
        # Se il numero di elementi è dispari, duplica l'ultimo nodo
        if len(current_level) % 2 == 1:
            current_level.append(current_level[-1])
        
        next_level = []  # Lista per il livello successivo dell'albero
        
        # Scorre i nodi a coppie per calcolare i nodi del livello superiore
        for i in range(0, len(current_level), 2):
            left = current_level[i]     # Nodo sinistro della coppia
            right = current_level[i+1]  # Nodo destro della coppia
            
            # Se il txid scelto è in questa coppia, salva l'hash del nodo fratello
            if i == current_index or i+1 == current_index:
                # Determina quale nodo è il fratello in base alla posizione
                sibling = right if current_index % 2 == 0 else left
                branch.append(sibling[::-1].hex())
            
            # Calcola il nodo padre combinando i due nodi figli
            parent = double_sha256(left + right)
            next_level.append(parent)
        
        # Aggiorna l'indice per il livello successivo
        current_index //= 2
        # Passa al livello successivo dell'albero
        current_level = next_level
    
    # Restituisce il merkle branch completo
    return branch
```

### Verifica del Merkle Branch

La verifica che una transazione sia inclusa in un blocco utilizzando il Merkle Branch è un processo complementare al calcolo del branch stesso:

```python
def verify_merkle_branch(coinbase_txid, merkle_branch, expected_merkle_root):
    # Converte il txid da esadecimale a byte e inverte l'ordine
    current = bytes.fromhex(coinbase_txid)[::-1]
    
    # Applica ogni hash del merkle branch per calcolare la merkle root
    for h in merkle_branch:
        # Converte l'hash del branch da esadecimale a byte e inverte l'ordine
        h_bytes = bytes.fromhex(h)[::-1]
        
        # In base alla posizione nel tree, l'hash corrente può essere a sinistra o a destra
        if len(current) > 0 and (current[0] & 0x01):
            # Se il bit meno significativo è 1, l'hash corrente va a destra
            current = double_sha256(h_bytes + current)
        else:
            # Altrimenti, l'hash corrente va a sinistra
            current = double_sha256(current + h_bytes)
    
    # Inverte l'ordine della merkle root calcolata e la converte in stringa esadecimale
    calculated_root = current[::-1].hex()
    
    # Confronta la merkle root calcolata con quella attesa
    return calculated_root == expected_merkle_root
```

## Merkle Branch e Merkle Root in Stratum V1

Il protocollo Stratum V1 è ampiamente utilizzato per il mining di Bitcoin e altre criptovalute. In questo contesto, il Merkle Branch svolge un ruolo fondamentale per l'efficienza e la sicurezza del processo di mining.

### Architettura di Stratum V1

Stratum V1 è un protocollo client-server che consente ai mining pool di distribuire il lavoro di mining a migliaia di minatori. La sua architettura si basa su:

1. **Mining Pool (Server)**: Gestisce la creazione dei blocchi candidati, la distribuzione del lavoro e la verifica delle soluzioni
2. **Minatori (Client)**: Ricevono il lavoro dal pool e cercano la nonce valida per il proof-of-work
3. **Protocollo di Comunicazione**: Basato su JSON-RPC su TCP, definisce i messaggi scambiati tra pool e minatori

### Ruolo del Merkle Branch nel Mining Pool

Quando un mining pool distribuisce il lavoro ai minatori, non invia l'intero blocco con tutte le transazioni, ma solo:

1. L'header del blocco (senza la nonce, che sarà trovata dal minatore)
2. La transazione coinbase (che contiene l'indirizzo del pool e dei minatori per ricevere la ricompensa)
3. Il Merkle Branch necessario per collegare la transazione coinbase alla Merkle Root

Questo approccio offre diversi vantaggi:

- **Efficienza di rete**: I minatori ricevono solo i dati essenziali (pochi KB) invece dell'intero blocco (potenzialmente MB)
- **Rapida distribuzione del lavoro**: Il pool può inviare rapidamente nuovi compiti ai minatori quando arrivano nuove transazioni
- **Controllo centralizzato delle transazioni**: Il pool decide quali transazioni includere nel blocco, mentre i minatori si concentrano solo sul trovare la nonce
- **Personalizzazione della coinbase**: Ogni minatore può ricevere una transazione coinbase unica, permettendo al pool di tracciare i contributi individuali

### Flusso di Lavoro in Stratum V1

1. **Inizializzazione**:
   - Il minatore si connette al pool e si autentica
   - Il pool registra il minatore e prepara la distribuzione del lavoro

2. **Distribuzione del lavoro**:
   - Il pool costruisce un blocco candidato con tutte le transazioni
   - Per ogni minatore, il pool:
     - Crea una transazione coinbase unica (con un identificativo del minatore)
     - Calcola il Merkle Branch per collegare questa coinbase alla Merkle Root
     - Invia al minatore: versione, hash del blocco precedente, timestamp, bits, e Merkle Branch

3. **Mining**:
   - Il minatore riceve i dati dal pool
   - Ricostruisce la Merkle Root usando la transazione coinbase e il Merkle Branch
   - Inserisce la Merkle Root nell'header del blocco
   - Cerca la nonce che rende valido l'header del blocco (proof-of-work)

4. **Sottomissione delle soluzioni**:
   - Quando un minatore trova una nonce valida, la invia al pool
   - Il pool verifica la soluzione ricostruendo l'header del blocco
   - Se valida, il pool assembla il blocco completo e lo trasmette alla rete Bitcoin

### Ottimizzazioni in Stratum V1

Il protocollo Stratum V1 include diverse ottimizzazioni per il mining di Bitcoin:

- **Extranonce Rolling**: Permette ai minatori di modificare parte della transazione coinbase (extranonce) senza richiedere un nuovo lavoro dal pool
- **Notifiche di Nuovi Blocchi**: Il pool informa immediatamente i minatori quando viene trovato un nuovo blocco, evitando lavoro inutile
- **Difficoltà Variabile**: Il pool può assegnare difficoltà diverse a minatori diversi in base alla loro potenza di hash

## Vantaggi dell'Utilizzo del Merkle Branch in Stratum V1

### Efficienza

- **Riduzione del Traffico di Rete**: I minatori ricevono solo gli hash necessari (log₂(n) hash) invece di tutte le transazioni
- **Aggiornamenti Rapidi**: Quando nuove transazioni arrivano, il pool può aggiornare il lavoro inviando solo un nuovo Merkle Branch
- **Scalabilità**: Il protocollo può gestire migliaia di minatori contemporaneamente con un overhead minimo

### Sicurezza

- **Integrità Garantita**: I minatori possono verificare che stanno lavorando su un blocco valido
- **Resistenza alle Manipolazioni**: Non è possibile sostituire transazioni senza che il pool se ne accorga
- **Tracciabilità**: Ogni minatore riceve una coinbase unica, permettendo al pool di tracciare i contributi

### Flessibilità

- **Controllo Centralizzato**: Il pool può decidere quali transazioni includere e come distribuire le ricompense
- **Adattabilità**: Il protocollo può essere esteso per supportare nuove funzionalità (come è avvenuto con Stratum V2)
- **Compatibilità**: Funziona con diversi algoritmi di mining e diverse criptovalute

## Limitazioni di Stratum V1 e Merkle Branch

Nonostante i vantaggi, Stratum V1 presenta alcune limitazioni:

- **Centralizzazione**: Il pool ha controllo completo sulle transazioni incluse nel blocco
- **Overhead di Comunicazione**: Ogni cambio di lavoro richiede una nuova comunicazione tra pool e minatori
- **Sicurezza Limitata**: Il protocollo non è crittograficamente sicuro (comunicazioni in chiaro)
- **Efficienza Subottimale**: Stratum V2 migliora ulteriormente l'efficienza con un protocollo binario e altre ottimizzazioni

## Utilizzo del Programma

Questo script Python simula il comportamento di un mining pool che utilizza Stratum V1, permettendo di:

1. Recuperare il template del blocco corrente da un nodo Bitcoin
2. Estrarre i TxID delle transazioni nel template
3. Generare una transazione coinbase (o utilizzare un TxID fornito dall'utente)
4. Calcolare il Merkle Branch per la coinbase
5. Verificare che il Merkle Branch sia corretto calcolando la Merkle Root

### Prerequisiti

- Python 3.6 o superiore
- Librerie: `requests`, `json`, `hashlib` (incluse nella libreria standard Python)
- Un nodo Bitcoin configurato e accessibile via RPC

### Configurazione

Prima di eseguire lo script, modifica i parametri di connessione RPC nel codice:

```python
# Configurazione dei parametri di connessione al nodo Bitcoin RPC
rpc_user = 'username'     
rpc_password = 'password' 
rpc_host = '127.0.0.1' 
rpc_port = '8332'           
```

### Esecuzione

Per eseguire lo script:

```bash
python merkle_branch.py
```

Il programma:

1. Si connette al nodo Bitcoin e recupera il template del blocco corrente
2. Mostra le transazioni presenti nel template
3. Chiede all'utente di inserire un TxID per la coinbase (o usa un valore predefinito)
4. Calcola e mostra il Merkle Branch per la coinbase
5. Calcola e mostra la Merkle Root risultante

## Conclusione

Il Merkle Tree, la Merkle Root e il Merkle Branch sono componenti fondamentali dell'architettura Bitcoin che consentono verifiche efficienti dell'integrità dei dati. La loro implementazione nel protocollo Stratum V1 ha reso possibile il mining pool distribuito, permettendo a migliaia di minatori di collaborare efficacemente nella ricerca di nuovi blocchi.

Questo script fornisce uno strumento pratico per esplorare questi concetti e comprendere meglio il funzionamento interno di Bitcoin e del processo di mining. Attraverso la simulazione del comportamento di un mining pool, è possibile osservare come il Merkle Branch venga calcolato e utilizzato per verificare l'integrità delle transazioni in un blocco.

La comprensione di questi meccanismi è essenziale per chiunque voglia approfondire il funzionamento di Bitcoin a livello tecnico, sia per scopi educativi che per lo sviluppo di applicazioni nel campo delle criptovalute.