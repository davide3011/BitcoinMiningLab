import config
import logging
from rpc import (
    connect_rpc, get_block_template
)
from builder import (
    build_coinbase_transaction
)

from utils import ( is_segwit_tx, split_coinbase, generate_extranonce2, 
    save_template_json, modifica_target, target_to_nbits, strip_witness
    )

log = logging.getLogger(__name__)

# Parametri mining
EXTRANONCE1 = "1234567890abcdef"
SIZE_EXTRANONCE2 = 4  # dimensione in byte per extranonce2

# --------------------------- ciclo principale --------------------------------
def main():
    
    try:
        # STEP 1) Ottieni una nuova connessione per il template
        rpc_template = connect_rpc()

        # STEP 2) GET BLOCK TEMPLATE
        template = get_block_template(rpc_template)
        save_template_json(template) # DEBUG
        if not template:
            log.error("Impossibile ottenere il template del blocco.")
            return

        # STEP 3) Assicurarsi di avere transazioni legacy con dati completi
        tot_tx       = len(template["transactions"])
        witness_tx   = sum(1 for tx in template["transactions"] if is_segwit_tx(tx["data"]))
        legacy_tx    = tot_tx - witness_tx
        log.info(f"Transazioni nel template: totali = {tot_tx}  |  legacy = {legacy_tx}  |  segwit = {witness_tx}")

        # STEP 4) USA TARGET MODIFICATO DAL CONFIG
        rpc_target = connect_rpc()
        target = modifica_target(template, rpc_target)
        log.info(f"Target modificato (DIFFICULTY_FACTOR={config.DIFFICULTY_FACTOR}): {target}")
        
        modified_bits = target_to_nbits(target)   # Converte il target modificato in formato bits
        log.info(f"Bits modificati: {modified_bits}")
        
        # STEP 5) COSTRUZIONE COINBASE
        miner_info = rpc_template.getaddressinfo(config.WALLET_ADDRESS)
        miner_script_pubkey = miner_info["scriptPubKey"]
        extranonce2 = generate_extranonce2(SIZE_EXTRANONCE2)
        coinbase_tx, coinbase_txid, coinbase_hash  = build_coinbase_transaction(
            template, miner_script_pubkey, EXTRANONCE1, extranonce2, 
            template["curtime"], template["bits"], config.COINBASE_MESSAGE
        )
        log.info(f"Coinbase witness: {coinbase_tx}")
        log.info(f"Coinbase_txid: {coinbase_txid}")
        log.info(f"Coinbase_hash: {coinbase_hash}")
        log.info(f"Messaggio nella coinbase: {config.COINBASE_MESSAGE}")

        # SPLIT COINBASE
        
        coinbase_tx_legacy = strip_witness(coinbase_tx)
        
        log.info(f"Coinbase legacy: {coinbase_tx_legacy}")
        
        coinb1, extranonce1_found, extranonce2_found, coinb2 = split_coinbase(coinbase_tx_legacy, EXTRANONCE1, extranonce2)
        log.info(f"coinb1: {coinb1}")
        log.info(f"extranonce1 trovato: {extranonce1_found}")
        log.info(f"extranonce2 trovato: {extranonce2_found}")
        log.info(f"coinb2: {coinb2}")
        
    except Exception:
        log.exception("Errore nel processo.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    main()
