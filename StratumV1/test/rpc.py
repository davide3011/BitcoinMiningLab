from bitcoinrpc.authproxy import AuthServiceProxy
import config
import logging

# Questo modulo gestisce la comunicazione con il nodo Bitcoin tramite chiamate RPC (Remote Procedure Call)
# Fornisce funzioni per ottenere dati dalla blockchain, richiedere template di blocchi e inviare blocchi minati

log = logging.getLogger(__name__)

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
    # Avvio test connessione  → INFO
    log.info("Verifica connessione RPC")
    try:
        # Crea una connessione RPC
        rpc = connect_rpc()
        # Richiede informazioni generali sulla blockchain
        info = rpc.getblockchaininfo()
        # Mostra le informazioni principali
        # Esito positivo        → INFO
        log.info("Connessione RPC riuscita – chain=%s, blocchi=%d, difficoltà=%s",
                 info['chain'], info['blocks'], info['difficulty'])

    except Exception as e:
        # Stack-trace completo  → EXCEPTION
        log.exception("Errore di connessione RPC")
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
        # Valore restituito    → DEBUG (informativo ma non essenziale)
        log.debug("Best block hash: %s", best_block_hash)
        return best_block_hash
    except Exception as e:
        # Gestisce eventuali errori durante la chiamata RPC
        log.error("Errore RPC getbestblockhash: %s", e)
        return None

def get_block_template(rpc):
    """
    Richiede un template di blocco al nodo Bitcoin e lo filtra per blocchi legacy.
    
    Args:
        rpc: Connessione RPC al nodo Bitcoin
        
    Returns:
        dict: Template del blocco contenente solo transazioni legacy, target di difficoltà e altri metadati,
              oppure None in caso di errore
        
    Note:
        Il template del blocco contiene tutte le informazioni necessarie per costruire un blocco valido:
        - Transazioni da includere nel blocco (filtrate per essere solo legacy)
        - Hash del blocco precedente
        - Difficoltà target
        - Altezza del blocco
        - Timestamp corrente
        - Valore della ricompensa (coinbase)
        
        Richiediamo il template con regole SegWit ma filtriamo solo le transazioni legacy.
    """
    try:
        # Richiede il template con regole SegWit (richiesto dal nodo)
        tpl = rpc.getblocktemplate({"rules": ["segwit"]})
        
        # Filtra solo le transazioni legacy (rimuove quelle SegWit)
        legacy_transactions = []
        for tx in tpl.get("transactions", []):
            tx_data = tx.get("data", "")
            # Controlla se la transazione è legacy (non SegWit)
            if not _is_segwit_transaction(tx_data):
                legacy_transactions.append(tx)
        
        # Aggiorna il template con solo transazioni legacy
        tpl["transactions"] = legacy_transactions
        
        log.debug("Template legacy ricevuto - altezza %d, %d tx legacy",
                  tpl.get("height"), len(legacy_transactions))
        return tpl
    except Exception as e:
        # Gestisce eventuali errori durante la richiesta
        log.error("Errore RPC getblocktemplate: %s", e)
        return None

def _is_segwit_transaction(raw_hex: str) -> bool:
    """Controlla se una transazione è in formato SegWit."""
    if len(raw_hex) < 12:
        return False
    # Controlla il marker e flag SegWit (0x00 0x01 dopo la versione)
    return raw_hex[8:12] == "0001"
    
def ensure_legacy_transaction_data(rpc, template):
    """
    Controlla e aggiorna le transazioni del template per blocchi legacy.
    
    Args:
        rpc: Connessione RPC al nodo Bitcoin
        template: Template del blocco da aggiornare
        
    Note:
        Per blocchi legacy, questa funzione garantisce che ogni transazione
        nel template abbia i dati completi in formato legacy (senza witness data).
        Recupera i dati delle transazioni dalla mempool o tramite getrawtransaction
        quando necessario, assicurandosi che siano in formato legacy.
    """
    # Lista per le transazioni corrette
    corrected_txs = []
    
    # Elabora ogni transazione nel template
    for tx in template["transactions"]:
        txid = tx["txid"]  # ID della transazione
        raw = tx["data"]   # Dati grezzi della transazione
        
        # Prova a recuperare la transazione completa in formato legacy
        try:
            # getrawtransaction recupera i dati grezzi completi di una transazione
            raw_tx_full = rpc.getrawtransaction(txid, False)
            if raw_tx_full:
                raw = raw_tx_full  # Usa i dati completi se disponibili
        except Exception as e:
            log.debug("Impossibile recuperare dati completi per %s: %s", txid, e)
        
        # Aggiunge la transazione corretta alla lista (formato legacy)
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
    log.info("Invio del blocco serializzato (%d byte) al nodo",
             len(serialized_block)//2)
    
    # Verifica che il blocco sia stato serializzato correttamente
    if not serialized_block:
        log.error("Blocco non serializzato correttamente - invio annullato")
        return

    try:
        # Invia il blocco al nodo Bitcoin
        result = rpc.submitblock(serialized_block)
        
        # Verifica il risultato dell'invio
        if result is None:
            log.info("Blocco accettato nella blockchain")
        else:
            log.error("submitblock ha restituito un errore: %s", result)

    except Exception as e:
        # Gestisce eventuali errori durante la chiamata RPC
        log.exception("Errore RPC durante submitblock")
