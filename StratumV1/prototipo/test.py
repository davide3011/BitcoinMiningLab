from bitcoinrpc.authproxy import AuthServiceProxy
from rpc import connect_rpc
import config
import logging
from typing import Tuple, Optional

# Configurazione logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def decode_raw_transaction_rpc(raw_hex: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Utilizza la chiamata RPC decoderawtransaction per ottenere txid e wtxid di una transazione.
    
    Args:
        raw_hex (str): Transazione in formato esadecimale
        
    Returns:
        Tuple[Optional[str], Optional[str]]: (txid, wtxid) oppure (None, None) in caso di errore
        
    Note:
        - txid: Transaction ID (identificatore della transazione)
        - wtxid: Witness Transaction ID (hash che include i dati witness per SegWit)
        - Per transazioni non-SegWit, txid e wtxid sono identici
    """
    try:
        # Connessione al nodo Bitcoin
        rpc = connect_rpc()
        
        # Decodifica la transazione raw
        decoded_tx = rpc.decoderawtransaction(raw_hex)
        
        # Estrae txid e wtxid dalla risposta
        txid = decoded_tx.get('txid')
        wtxid = decoded_tx.get('hash')  # 'hash' è il campo che contiene il wtxid
        
        log.debug("Transazione decodificata con successo")
        log.info("TXID: %s", txid)
        log.info("WTXID (hash): %s", wtxid)
        
        # Verifica se è una transazione SegWit
        if txid != wtxid:
            log.debug("✓ Transazione SegWit")
        else:
            log.debug("✓ Transazione Legacy")
            
        return txid, wtxid
        
    except Exception as e:
        log.error("Errore durante la decodifica della transazione: %s", e)
        return None, None

if __name__ == "__main__":
    tx = "010000000001010000000000000000000000000000000000000000000000000000000000000000ffffffff230294036a122f4369616f20736f6e6f204461766964652f1234567890abcdef7d45f390ffffffff02c817a804000000001600146909738f4fe3d2d3abe3b14d4542d73ca32bbc110000000000000000266a24aa21a9ede2f61c3f71d1defd3fa999dfa36953755c690689799962b48bebd836974e8cf90120000000000000000000000000000000000000000000000000000000000000000000000000"
    txid, wtxid = decode_raw_transaction_rpc(tx)