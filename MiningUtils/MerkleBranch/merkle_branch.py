import requests  # Per effettuare richieste HTTP al nodo Bitcoin
import json      # Per la gestione dei dati JSON
import hashlib   # Per il calcolo degli hash SHA256

# Configurazione dei parametri di connessione al nodo Bitcoin RPC
rpc_user = '...'     
rpc_password = '...' 
rpc_host = '...' 
rpc_port = '...'           

# Costruzione dell'URL completo per le chiamate RPC
url = f'http://{rpc_host}:{rpc_port}/'

def rpc_request(method, params=None):
    """
    Effettua una chiamata JSON-RPC al nodo Bitcoin.
    
    Questa funzione gestisce la comunicazione con il nodo Bitcoin, formattando
    correttamente la richiesta JSON-RPC e gestendo la risposta o eventuali errori.
    
    :param method: Metodo RPC da invocare (es. "getblockchaininfo", "getblock", "getblockhash").
    :param params: Lista dei parametri da passare al metodo (opzionale).
    :return: Il risultato della chiamata RPC in formato JSON.
    :raises: Exception se la chiamata RPC fallisce.
    """
    # Imposta l'header per indicare che il contenuto è in formato JSON
    headers = {'content-type': 'application/json'}
    
    # Costruisce il payload della richiesta secondo lo standard JSON-RPC 1.0
    payload = {
        "jsonrpc": "1.0",     # Versione del protocollo JSON-RPC
        "id": "python",      # Identificativo della richiesta
        "method": method,    # Metodo RPC da invocare
        "params": params or [] # Parametri del metodo (lista vuota se non specificati)
    }
    
    # Effettua la richiesta POST con autenticazione HTTP Basic
    response = requests.post(url, auth=(rpc_user, rpc_password), headers=headers, json=payload)
    
    # Converte la risposta in formato JSON
    response_json = response.json()
    
    # Verifica se la risposta contiene un errore
    if response_json.get('error') is not None:
        raise Exception(f"Errore nella chiamata {method}: {response_json['error']}")
    
    # Restituisce solo il campo 'result' della risposta
    return response_json['result']

def double_sha256(data):
    """
    Calcola il doppio hash SHA256 dei dati forniti.
    
    In Bitcoin, molte strutture dati (incluse le transazioni) vengono hashate
    due volte con SHA256 per maggiore sicurezza. Questo è noto come "double SHA256".
    
    :param data: Dati in formato bytes da hashare.
    :return: Il risultato del doppio hash SHA256 in formato bytes.
    """
    # Applica SHA256 una prima volta e ottiene il digest (risultato) in bytes
    first_hash = hashlib.sha256(data).digest()
    # Applica SHA256 una seconda volta al risultato del primo hash
    return hashlib.sha256(first_hash).digest()

def merkle_branch(txids, index):
    """
    Costruisce il merkle branch per il txid all'indice 'index' nella lista 'txids'.
    
    In Stratum V1, questo viene utilizzato per calcolare il merkle branch della
    transazione coinbase (index=0), che viene poi inviato ai minatori insieme
    all'header del blocco e alla transazione coinbase stessa.
    
    :param txids: Lista di txid in formato esadecimale (stringhe hex).
    :param index: Indice del txid per cui calcolare il merkle branch (0 per la coinbase in Stratum V1).
    :return: Lista di hash esadecimali che compongono il merkle branch.
    """
    # Converte i txid da esadecimale a byte e inverte l'ordine (da little-endian a big-endian)
    # In Bitcoin, i txid sono memorizzati in formato little-endian, ma per il calcolo
    # del merkle tree vengono usati in formato big-endian
    current_level = [bytes.fromhex(tx)[::-1] for tx in txids]
    branch = []  # Lista che conterrà gli hash del merkle branch
    current_index = index  # Indice corrente del nodo nel livello attuale
    
    # Continua finché non rimane un solo nodo (la merkle root)
    while len(current_level) > 1:
        # Se il numero di elementi è dispari, duplica l'ultimo nodo
        # Questo è necessario perché il merkle tree richiede un numero pari di nodi a ogni livello
        if len(current_level) % 2 == 1:
            current_level.append(current_level[-1])
        
        next_level = []  # Lista per il livello successivo dell'albero
        
        # Scorre i nodi a coppie per calcolare i nodi del livello superiore
        for i in range(0, len(current_level), 2):
            left = current_level[i]     # Nodo sinistro della coppia
            right = current_level[i+1]  # Nodo destro della coppia
            
            # Se il txid scelto è in questa coppia, salva l'hash del nodo fratello
            # Questo hash sarà parte del merkle branch
            if i == current_index or i+1 == current_index:
                # Determina quale nodo è il fratello (sibling) in base alla posizione
                sibling = right if current_index % 2 == 0 else left
                # Inverte l'ordine del sibling prima di convertirlo in hex (da big-endian a little-endian)
                # per mantenere la coerenza con il formato dei txid in Bitcoin
                branch.append(sibling[::-1].hex())
            
            # Calcola il nodo padre combinando i due nodi figli e applicando il doppio SHA256
            parent = double_sha256(left + right)
            next_level.append(parent)
        
        # Aggiorna l'indice per il livello successivo (divide per 2 perché ogni coppia
        # di nodi genera un solo nodo padre)
        current_index //= 2
        # Passa al livello successivo dell'albero
        current_level = next_level
    
    # Restituisce il merkle branch completo
    return branch

def verify_merkle_branch(coinbase_txid, merkle_branch, expected_merkle_root):
    """
    Verifica che una transazione coinbase sia inclusa nel blocco usando il merkle branch.
    
    Questa funzione simula ciò che fa un minatore in Stratum V1: riceve la transazione
    coinbase e il merkle branch dal pool, e verifica che questi dati producano
    la merkle root attesa.
    
    :param coinbase_txid: TxID della transazione coinbase (stringa esadecimale).
    :param merkle_branch: Lista di hash che compongono il merkle branch (stringhe esadecimali).
    :param expected_merkle_root: Merkle root attesa (stringa esadecimale).
    :return: True se la verifica ha successo, False altrimenti.
    """
    # Converte il txid da esadecimale a byte e inverte l'ordine (da little-endian a big-endian)
    current = bytes.fromhex(coinbase_txid)[::-1]
    
    # Applica ogni hash del merkle branch per calcolare la merkle root
    for h in merkle_branch:
        # Converte l'hash del branch da esadecimale a byte e inverte l'ordine
        h_bytes = bytes.fromhex(h)[::-1]
        
        # In base alla posizione nel tree, l'hash corrente può essere a sinistra o a destra
        # Nel protocollo Stratum V1, la posizione è determinata dal bit meno significativo dell'hash corrente
        if len(current) > 0 and (current[0] & 0x01):
            # Se il bit meno significativo è 1, l'hash corrente va a destra
            current = double_sha256(h_bytes + current)
        else:
            # Altrimenti, l'hash corrente va a sinistra
            current = double_sha256(current + h_bytes)
    
    # Inverte l'ordine della merkle root calcolata (da big-endian a little-endian)
    # e la converte in stringa esadecimale
    calculated_root = current[::-1].hex()
    
    # Confronta la merkle root calcolata con quella attesa
    return calculated_root == expected_merkle_root

def get_coinbase_merkle_branch(txids):
    """
    Calcola il merkle branch per la transazione coinbase.
    
    In Stratum V1, il pool di mining calcola questo merkle branch e lo invia ai minatori
    insieme alla transazione coinbase e all'header del blocco.
    
    :param txids: Lista di txid in formato esadecimale, con la coinbase all'indice 0.
    :return: Merkle branch per la coinbase come lista di stringhe esadecimali.
    """
    # Calcola il merkle branch per la transazione coinbase (indice 0)
    return merkle_branch(txids, 0)

def compute_merkle_root(txids):
    """
    Calcola la merkle root a partire dalla lista dei txid.
    
    La merkle root è l'hash che rappresenta la radice del merkle tree ed è inclusa
    nell'header del blocco Bitcoin. Questa funzione ricostruisce l'intero merkle tree
    e restituisce la radice.
    
    :param txids: Lista di txid in formato esadecimale (stringhe hex).
    :return: Merkle root calcolata (stringa esadecimale).
    """
    # Converte i txid da esadecimale a byte e inverte l'ordine (da little-endian a big-endian)
    current_level = [bytes.fromhex(tx)[::-1] for tx in txids]
    
    # Calcola la merkle root costruendo l'albero dal basso verso l'alto
    while len(current_level) > 1:
        # Se il numero di elementi è dispari, duplica l'ultimo
        if len(current_level) % 2 == 1:
            current_level.append(current_level[-1])
        
        next_level = []  # Lista per il livello successivo dell'albero
        
        # Scorre i nodi a coppie per calcolare i nodi del livello superiore
        for i in range(0, len(current_level), 2):
            # Concatena i due hash e calcola il doppio SHA256
            parent = double_sha256(current_level[i] + current_level[i+1])
            next_level.append(parent)
        
        # Passa al livello successivo dell'albero
        current_level = next_level
    
    # La merkle root è l'unico hash rimasto alla fine
    # Inverte nuovamente (da big-endian a little-endian) per ottenere il formato standard di Bitcoin
    return current_level[0][::-1].hex()

def get_block_template():
    """
    Recupera il template del blocco corrente usando getblocktemplate con regole segwit.
    
    Questa funzione effettua una chiamata RPC a getblocktemplate con il parametro
    {"rules": ["segwit"]} per ottenere un template di blocco che include transazioni
    compatibili con Segregated Witness.
    
    :return: Il template del blocco in formato JSON.
    :raises: Exception se la chiamata RPC fallisce.
    """
    # Effettua la chiamata RPC a getblocktemplate con regole segwit
    template_params = {"rules": ["segwit"]}
    try:
        block_template = rpc_request("getblocktemplate", [template_params])
        return block_template
    except Exception as e:
        # Gestisce eventuali errori nella chiamata RPC
        raise Exception(f"Errore durante la chiamata a getblocktemplate: {e}")

def extract_txids_from_template(block_template):
    """
    Estrae i TxID dalle transazioni presenti nel template del blocco.
    
    In un template di blocco, le transazioni sono fornite come oggetti completi,
    non solo come TxID. Questa funzione estrae i TxID da questi oggetti.
    
    :param block_template: Template del blocco ottenuto da getblocktemplate.
    :return: Lista di TxID in formato esadecimale (senza la coinbase).
    """
    # Estrae le transazioni dal template
    transactions = block_template.get("transactions", [])
    
    # Estrae i txid dalle transazioni
    txids = [tx.get("txid") for tx in transactions]
    
    # Restituisce solo i txid delle transazioni normali (senza coinbase)
    return txids

def main():
    """
    Funzione principale ottimizzata per Stratum V1.
    
    Questa funzione simula il comportamento di un mining pool che utilizza Stratum V1:
    1. Recupera il template del blocco
    2. Estrae i TxID delle transazioni
    3. Genera una transazione coinbase
    4. Calcola il merkle branch per la coinbase
    5. Verifica che il merkle branch sia corretto
    
    In un sistema reale, il pool invierebbe la coinbase, il merkle branch e l'header
    del blocco ai minatori, che userebbero questi dati per cercare la nonce valida.
    """
    # 1. Recupera il template del blocco usando getblocktemplate con regole segwit
    try:
        print("Recupero del template del blocco con regole segwit...")
        block_template = get_block_template()
        print("Template del blocco recuperato con successo.")
        
        # Estrae alcune informazioni dal template per riferimento
        bits = block_template.get("bits")
        height = block_template.get("height")
        print(f"Altezza del blocco nel template: {height}")
        print(f"Bits: {bits}")
    except Exception as e:
        # Gestisce eventuali errori nella chiamata RPC
        print("Errore durante il recupero del template del blocco:")
        print(e)
        return

    # 2. Estrae i TxID dal template del blocco (senza la coinbase)
    try:
        txids = extract_txids_from_template(block_template)
        
        if not txids:
            # Se non ci sono transazioni nel template (caso improbabile)
            print("Nessuna transazione trovata nel template del blocco.")
            return
        # Mostra le transazioni normali (non coinbase)
        print(f"\nTransazioni nel template: ({len(txids)} transazioni)")
        print("Elenco completo di tutte le transazioni:")
        for i, tx in enumerate(txids):
            print(f"{i+1}. {tx}")
    except Exception as e:
        # Gestisce eventuali errori nell'estrazione dei TxID
        print("Errore durante l'estrazione dei TxID dal template:")
        print(e)
        return

    # 3. Chiede all'utente di inserire il TxID della coinbase
    coinbase_txid = input("\nInserisci il TxID della coinbase: ").strip()
    if not coinbase_txid:
        # Usa un valore di esempio se l'utente non inserisce nulla
        coinbase_txid = "0" * 64
        print(f"Usando TxID di esempio: {coinbase_txid}")
    
    # Aggiunge la coinbase all'inizio della lista dei TxID
    all_txids = [coinbase_txid] + txids
    
    # 4. Calcola il merkle branch per la coinbase (indice 0)
    try:
        # Questo è il merkle branch che il pool invierebbe ai minatori in Stratum V1
        branch = get_coinbase_merkle_branch(all_txids)
        print("\nMerkle branch per la coinbase (formato Stratum V1):")
        for i, h in enumerate(branch):
            print(f"{i+1}. {h}")
        
        # Mostra anche il numero totale di hash nel merkle branch
        print(f"\nNumero totale di hash nel merkle branch: {len(branch)}")
        print(f"Dimensione approssimativa: {len(branch) * 32} bytes")
    except Exception as e:
        # Gestisce eventuali errori nel calcolo del merkle branch
        print("Errore nel calcolo del merkle branch:")
        print(e)
        return
    
    # 5. Calcola la Merkle root a partire dalla lista di tutte le transazioni
    computed_merkle_root = compute_merkle_root(all_txids)
    print("\nMerkle root calcolata:")
    print(computed_merkle_root)

# Punto di ingresso del programma quando viene eseguito direttamente
if __name__ == "__main__":
    main()
