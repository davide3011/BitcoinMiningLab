from bitcoinrpc.authproxy import AuthServiceProxy
import config

# Questo modulo gestisce la comunicazione con il nodo Bitcoin tramite chiamate RPC (Remote Procedure Call)
# Fornisce funzioni per ottenere dati dalla blockchain, richiedere template di blocchi e inviare blocchi minati

def connect_rpc():
    """
    Crea una connessione RPC al nodo Bitcoin utilizzando le credenziali configurate.
    
    Returns:
        AuthServiceProxy: Un oggetto proxy che permette di effettuare chiamate RPC al nodo Bitcoin
        
    Note:
        Le chiamate RPC (Remote Procedure Call) permettono di comunicare con un nodo Bitcoin
        e di accedere alle sue funzionalità come se fossero funzioni locali.
        Le credenziali di autenticazione sono prese dal modulo config.
    """
    return AuthServiceProxy(f"http://{config.RPC_USER}:{config.RPC_PASSWORD}@{config.RPC_HOST}:{config.RPC_PORT}")

def test_rpc_connection():
    """
    Verifica la connessione al nodo Bitcoin e mostra informazioni di base sulla blockchain.
    
    Raises:
        Exception: Se la connessione al nodo fallisce
        
    Note:
        Questa funzione è utile per verificare che il nodo sia raggiungibile e funzionante
        prima di iniziare il processo di mining. Mostra informazioni come il tipo di rete
        (mainnet, testnet, regtest), l'altezza della blockchain e la difficoltà attuale.
    """
    print("=== Verifica connessione RPC ===")
    try:
        # Crea una connessione RPC
        rpc = connect_rpc()
        # Richiede informazioni generali sulla blockchain
        info = rpc.getblockchaininfo()
        # Mostra le informazioni principali
        print("\nConnessione riuscita!")
        print(f"Chain: {info['chain']}")          # Tipo di rete (mainnet, testnet, regtest)
        print(f"Blocchi: {info['blocks']}")       # Altezza attuale della blockchain
        print(f"Difficoltà: {info['difficulty']}") # Difficoltà di mining attuale
    except Exception as e:
        # Gestisce e propaga eventuali errori di connessione
        print(f"\nErrore di connessione: {e}")
        raise

def get_best_block_hash(rpc):
    """
    Recupera l'hash del blocco più recente nella blockchain (best block).
    
    Args:
        rpc: Connessione RPC al nodo Bitcoin
        
    Returns:
        str: L'hash del blocco più recente, oppure None in caso di errore
        
    Note:
        La chiamata RPC 'getbestblockhash' restituisce l'identificatore univoco (hash)
        dell'ultimo blocco valido aggiunto alla catena principale della blockchain.
        Questo è utile per conoscere lo stato attuale della blockchain.
    """
    try:
        # Richiede l'hash del blocco più recente
        best_block_hash = rpc.getbestblockhash()
        return best_block_hash
    except Exception as e:
        # Gestisce eventuali errori durante la chiamata RPC
        print(f"\nErrore nel recupero del best block hash: {e}")
        return None

def get_block_template(rpc):
    """
    Richiede un template di blocco al nodo Bitcoin con supporto per le regole SegWit.
    
    Args:
        rpc: Connessione RPC al nodo Bitcoin
        
    Returns:
        dict: Template del blocco contenente transazioni, target di difficoltà e altri metadati,
              oppure None in caso di errore
        
    Note:
        Il template del blocco contiene tutte le informazioni necessarie per costruire un blocco valido:
        - Transazioni da includere nel blocco
        - Hash del blocco precedente
        - Difficoltà target
        - Altezza del blocco
        - Timestamp corrente
        - Valore della ricompensa (coinbase)
        
        Specificando "segwit" nelle regole, richiediamo un template compatibile con
        Segregated Witness (BIP141), che permette di includere transazioni SegWit nel blocco.
    """
    try:
        # Richiede il template specificando il supporto per SegWit
        return rpc.getblocktemplate({"rules": ["segwit"]})
    except Exception as e:
        # Gestisce eventuali errori durante la richiesta
        print(f"Errore nel recupero del template: {e}")
        return None
    
def ensure_witness_data(rpc, template):
    """
    Controlla e aggiorna le transazioni del template con dati completi, inclusi i dati witness.
    
    Args:
        rpc: Connessione RPC al nodo Bitcoin
        template: Template del blocco da aggiornare
        
    Note:
        Questa funzione è importante per il supporto SegWit (Segregated Witness).
        Alcune implementazioni di getblocktemplate potrebbero non includere tutti i dati
        witness necessari per le transazioni. Questa funzione garantisce che ogni transazione
        nel template abbia i dati completi, recuperandoli dalla mempool o direttamente
        tramite getrawtransaction quando necessario.
        
        Il wtxid (witness txid) è l'identificatore di una transazione che include anche
        i dati witness, mentre il txid tradizionale non li include.
    """
    # Lista per le transazioni corrette
    corrected_txs = []
    
    # Recupera informazioni dettagliate sulla mempool
    try:
        # getrawmempool(True) restituisce informazioni dettagliate su tutte le transazioni nella mempool
        mempool_info = rpc.getrawmempool(True)
    except Exception as e:
        print(f"Errore nel recupero della mempool: {e}")
        mempool_info = {}
    
    # Elabora ogni transazione nel template
    for tx in template["transactions"]:
        txid = tx["txid"]  # ID della transazione
        raw = tx["data"]   # Dati grezzi della transazione
        
        # Cerca il witness txid (wtxid) nella mempool
        if txid in mempool_info:
            # Se la transazione è nella mempool, prova a ottenere il wtxid
            wtxid = mempool_info[txid].get("wtxid", txid)
        else:
            # Altrimenti usa il txid normale
            wtxid = txid  # Usa il txid se il wtxid non è disponibile
        
        # Prova a recuperare la transazione completa con i dati witness
        try:
            # getrawtransaction recupera i dati grezzi completi di una transazione
            raw_tx_full = rpc.getrawtransaction(txid, False)
            if raw_tx_full:
                raw = raw_tx_full  # Usa i dati completi se disponibili
        except Exception as e:
            print(f"Impossibile recuperare raw witness di {txid}: {e}")
        
        # Aggiunge la transazione corretta alla lista
        corrected_txs.append({"hash": txid, "data": raw})
    
    # Sostituisce le transazioni nel template con quelle corrette
    template["transactions"] = corrected_txs

def submit_block(rpc, serialized_block):
    """
    Invia il blocco minato al nodo Bitcoin per la validazione e l'inclusione nella blockchain.
    
    Args:
        rpc: Connessione RPC al nodo Bitcoin
        serialized_block: Il blocco serializzato in formato esadecimale
        
    Note:
        Quando un blocco viene minato con successo, deve essere inviato alla rete Bitcoin
        per essere validato e aggiunto alla blockchain. Questa funzione utilizza la chiamata
        RPC 'submitblock' per inviare il blocco al nodo connesso.
        
        Se il blocco è valido e contiene un proof-of-work sufficiente, il nodo lo accetterà
        e lo propagherà agli altri nodi della rete. Se il blocco non è valido per qualsiasi
        motivo (transazioni non valide, proof-of-work insufficiente, ecc.), il nodo lo rifiuterà
        e restituirà un messaggio di errore.
        
        Un risultato None indica che il blocco è stato accettato con successo.
    """
    print("\n=== Invio del blocco al nodo Bitcoin ===")
    print("\nInviando il blocco al nodo Bitcoin...")

    # Verifica che il blocco sia stato serializzato correttamente
    if not serialized_block:
        print("Blocco non serializzato correttamente. Annullando l'invio.")
        return

    try:
        # Invia il blocco al nodo Bitcoin
        result = rpc.submitblock(serialized_block)
        
        # Verifica il risultato dell'invio
        if result is None:
            # Un risultato None indica successo
            print("\nBlocco accettato nella blockchain!")
        else:
            # Qualsiasi altro risultato indica un errore
            print(f"\nErrore nell'invio del blocco: {result}")
    except Exception as e:
        # Gestisce eventuali errori durante la chiamata RPC
        print(f"\nErrore RPC durante submitblock: {e}")