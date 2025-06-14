import config, logging
from rpc import (
    connect_rpc, test_rpc_connection, get_block_template, ensure_legacy_transaction_data,
    submit_block
)
from block_builder import (
    calculate_merkle_root, build_block_header,
    serialize_block, build_coinbase_transaction
)

from utils import (decode_nbits, split_coinbase, calculate_merkle_branch, 
    create_mining_notify_params, save_job_json, generate_extranonce2, save_template_json
    )

log = logging.getLogger(__name__)

# Parametri mining
EXTRANONCE1 = "1234567890abcdef"
SIZE_EXTRANONCE2 = 4  # dimensione in byte per extranonce2

# --------------------------- ciclo principale --------------------------------
def main():
    # TEST RPC
    test_rpc_connection()

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
        ensure_legacy_transaction_data(rpc_template, template)

        tot_tx = len(template["transactions"])
        log.info(f"Transazioni legacy nel template: {tot_tx}")

        # STEP 4) COSTRUISCI COINBASE
        miner_info = rpc_template.getaddressinfo(config.WALLET_ADDRESS)
        miner_script_pubkey = miner_info["scriptPubKey"]
        extranonce2 = generate_extranonce2(SIZE_EXTRANONCE2)
        coinbase_tx, coinbase_txid = build_coinbase_transaction(
            template, miner_script_pubkey, EXTRANONCE1, extranonce2, config.COINBASE_MESSAGE
        )
        log.info(f"Coinbase_hex: {coinbase_tx}")
        log.info(f"Coinbase_txid: {coinbase_txid}")
        log.info(f"Messaggio nella coinbase: {config.COINBASE_MESSAGE}")

        # SPLIT COINBASE
        coinb1, extranonce1_found, extranonce2_found, coinb2 = split_coinbase(coinbase_tx, EXTRANONCE1, extranonce2)
        log.info(f"coinb1: {coinb1}")
        log.info(f"extranonce1 trovato: {extranonce1_found}")
        log.info(f"extranonce2 trovato: {extranonce2_found}")
        log.info(f"coinb2: {coinb2}")

        # STEP 5) USA TARGET DAL TEMPLATE
        nBits_int = int(template["bits"], 16)
        target = decode_nbits(nBits_int)
        log.info(f"Target dal template: {target}")

        # STEP 6) CALCOLA MERKLE BRANCH
        merkle_branch = calculate_merkle_branch(template)
        log.info(f"Merkle branch: {merkle_branch}")

        # STEP 7) CREARE IL JOB
        job = create_mining_notify_params(template, coinb1, coinb2, merkle_branch)
        save_job_json(job)
        log.info(f"Job: {job}")
        
    except Exception:
        log.exception("Errore nel processo di mining")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    main()
