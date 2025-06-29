"""
Script di test per la funzione build_coinbase_transaction.
"""

import logging
import config
from builder import build_coinbase_transaction
from rpc import connect_rpc

# Configurazione logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)

# ==================== PARAMETRI DI TEST ====================
# Template simulato
TEMPLATE = {
    "height": 850000,
    "coinbasevalue": 625000000,
    "default_witness_commitment": "6a24aa21a9ede2f61c3f71d1defd3fa999dfa36953755c690689799962b48bebd836974e8cf9",
    "curtime": 1703001600,
    "bits": "17034a7d"
}

# Parametri mining
EXTRANONCE1 = "1234567890abcdef"
EXTRANONCE2 = "12345678"
COINBASE_MESSAGE = "/Ciao sono Davide/"


def test_coinbase_transaction():
    """Test della funzione build_coinbase_transaction."""
    
    # Ottieni script pubkey del miner
    try:
        rpc_connection = connect_rpc()
        miner_info = rpc_connection.getaddressinfo(config.WALLET_ADDRESS)
        
        if "scriptPubKey" not in miner_info:
            raise ValueError(f"Manca 'scriptPubKey' per l'indirizzo {config.WALLET_ADDRESS}")
        
        miner_script_pubkey = miner_info["scriptPubKey"]
        
        if not miner_script_pubkey or not all(c in '0123456789abcdefABCDEF' for c in miner_script_pubkey):
            raise ValueError(f"Script pubkey non valido: {miner_script_pubkey}")
        
        log.info(f"Script pubkey: {miner_script_pubkey}")
        
    except Exception as e:
        log.error(f"Errore RPC ({config.WALLET_ADDRESS}): {e}")
        return None
    
    # Creazione transazione coinbase
    log.info(f"Test blocco {TEMPLATE['height']} - Ricompensa: {TEMPLATE['coinbasevalue']} sat")
    
    try:
        coinbase_hex, txid, hash_result = build_coinbase_transaction(
            template=TEMPLATE,
            miner_script_pubkey=miner_script_pubkey,
            extranonce1=EXTRANONCE1,
            extranonce2=EXTRANONCE2,
            ntime=TEMPLATE["curtime"],
            bits=TEMPLATE["bits"],
            coinbase_message=COINBASE_MESSAGE
        )
        
        log.info(f"Coinbase creata - TXID: {txid}")
        
        print(f"\nCoinbase Hex: {coinbase_hex}")
        print(f"TXID: {txid}")
        print(f"Hash: {hash_result}")
        print(f"Dimensione: {len(coinbase_hex)//2} byte")
        
        return coinbase_hex, txid, hash_result
        
    except Exception as e:
        log.error(f"Errore creazione coinbase: {e}")
        raise

if __name__ == "__main__":
    print("\nTest build_coinbase_transaction")
    
    try:
        result = test_coinbase_transaction()
        
        if result:
            print("\nTest completato!")
        else:
            print("\nTest fallito")
            
    except Exception as e:
        log.error(f"Errore critico: {e}")
        print(f"\nErrore critico: {e}")