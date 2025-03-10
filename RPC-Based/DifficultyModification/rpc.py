from bitcoinrpc.authproxy import AuthServiceProxy
import config

def connect_rpc():
    """ Connette al nodo Bitcoin tramite RPC. """
    return AuthServiceProxy(f"http://{config.RPC_USER}:{config.RPC_PASSWORD}@{config.RPC_HOST}:{config.RPC_PORT}")

def test_rpc_connection():
    """ Verifica la connessione al nodo Bitcoin. """
    print("=== Verifica connessione RPC ===")
    try:
        rpc = connect_rpc()
        info = rpc.getblockchaininfo()
        print("\nConnessione riuscita!")
        print(f"Chain: {info['chain']}")
        print(f"Blocchi: {info['blocks']}")
        print(f"Difficoltà: {info['difficulty']}")
    except Exception as e:
        print(f"\nErrore di connessione: {e}")
        raise

def get_block_template(rpc):
    """ Richiede un template di blocco al nodo (con regole SegWit). """
    try:
        return rpc.getblocktemplate({"rules": ["segwit"]})
    except Exception as e:
        print(f"Errore nel recupero del template: {e}")
        return None
    
def ensure_witness_data(rpc, template):
    """ Controlla e aggiorna le transazioni del template con dati completi. """
    corrected_txs = []
    try:
        mempool_info = rpc.getrawmempool(True)
    except Exception as e:
        print(f"Errore nel recupero della mempool: {e}")
        mempool_info = {}
    
    for tx in template["transactions"]:
        txid = tx["txid"]
        raw = tx["data"]
        
        if txid in mempool_info:
            wtxid = mempool_info[txid].get("wtxid", txid)
        else:
            wtxid = txid  # Usa il txid se il wtxid non è disponibile
        
        try:
            raw_tx_full = rpc.getrawtransaction(txid, False)
            if raw_tx_full:
                raw = raw_tx_full
        except Exception as e:
            print(f"Impossibile recuperare raw witness di {txid}: {e}")
        
        corrected_txs.append({"hash": txid, "data": raw})
    
    template["transactions"] = corrected_txs

def submit_block(rpc, serialized_block):
    """Invia il blocco minato al nodo Bitcoin."""
    print("\n=== Invio del blocco al nodo Bitcoin ===")
    print("\nInviando il blocco al nodo Bitcoin...")

    if not serialized_block:
        print("Blocco non serializzato correttamente. Annullando l'invio.")
        return

    try:
        result = rpc.submitblock(serialized_block)
        if result is None:
            print("\nBlocco accettato nella blockchain!")
        else:
            print(f"\nErrore nell'invio del blocco: {result}")
    except Exception as e:
        print(f"\nErrore RPC durante submitblock: {e}")