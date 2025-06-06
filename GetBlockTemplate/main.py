import time, threading, config, hashlib, logging
from rpc import (
    connect_rpc, test_rpc_connection, get_block_template, ensure_witness_data,
    submit_block, get_best_block_hash 
)
from block_builder import (
    decode_nbits, calculate_merkle_root, build_block_header, is_segwit_tx,
    serialize_block, build_coinbase_transaction
)
from miner import mine_block

log = logging.getLogger(__name__)

# -- parametri per il mining ----------------------------------------------
EXTRANONCE1 = "1234567890abcdef"
EXTRANONCE2 = "12341234"

# -- parametro: intervallo (secondi) fra due poll del best-block --------------
CHECK_INTERVAL = 20

# --------------------------- funzioni di supporto -----------------------------
def modifica_target(template, rpc_conn):
    """
    Modifica il target di mining in base alla rete e al fattore di difficoltà.
    
    Args:
        template (dict): Il template del blocco ottenuto da getblocktemplate
        rpc_conn: Connessione RPC al nodo Bitcoin
        
    Returns:
        str: Il target modificato in formato esadecimale
        float: Il valore effettivo di DIFFICULTY_FACTOR utilizzato
    """
    log = logging.getLogger(__name__)
    
    # Determina la rete e imposta DIFFICULTY_FACTOR appropriato
    blockchain_info = rpc_conn.getblockchaininfo()
    network = blockchain_info.get("chain", "")
    
    # Imposta DIFFICULTY_FACTOR in base alla rete
    if network == "regtest":
        difficulty_factor = float(config.DIFFICULTY_FACTOR)
        # Su regtest permettiamo anche difficoltà minori di 1 per scopi didattici
        if difficulty_factor < 0:
            log.warning("DIFFICULTY_FACTOR deve essere >= 0. Impostazione a 0.1")
            difficulty_factor = 0.1
    else:  # testnet o mainnet
        difficulty_factor = 1.0
        log.info(f"Rete {network} rilevata: DIFFICULTY_FACTOR impostato a 1.0")
    
    # Decodifica il target originale
    nBits_int = int(template["bits"], 16)
    original_target = decode_nbits(nBits_int)
    log.debug(f"Target originale: {original_target}")
    
    # Calcola il target modificato
    if difficulty_factor == 0:
        # Usa il target originale
        modified_target = original_target
        log.info("DIFFICULTY_FACTOR = 0: utilizzo il target originale della rete")
    else:
        # Calcola il target in base alla difficoltà
        max_target = 0x00000000FFFF0000000000000000000000000000000000000000000000000000
        target_value = int(max_target / difficulty_factor)
        
        # Limita il target al massimo valore consentito
        max_possible_target = (1 << 256) - 1
        if target_value > max_possible_target:
            target_value = max_possible_target
            log.warning("Target calcolato troppo grande. Limitato al massimo valore possibile.")
            
        modified_target = f"{target_value:064x}"
        log.info(f"Target modificato (difficoltà {difficulty_factor}): {modified_target}")
    
    return modified_target


# --------------------------- watchdog thread ---------------------------------
def watchdog_bestblock(rpc_conn, stop_event: threading.Event):
    """
    Chiama getbestblockhash() ogni CHECK_INTERVAL.
    Quando l'hash cambia, setta stop_event per segnalare ai worker di fermarsi.
    """
    last_hash = get_best_block_hash(rpc_conn)
    while not stop_event.is_set():
        time.sleep(CHECK_INTERVAL)
        new_hash = get_best_block_hash(rpc_conn)
        if new_hash and new_hash != last_hash:
            stop_event.set()          # segnala “nuovo blocco trovato”
        else:
            last_hash = new_hash


# --------------------------- ciclo principale --------------------------------
def main():
    # TEST RPC
    test_rpc_connection()
    
    # Log dell'extranonce2 utilizzato
    log.info(f"Extranonce2 utilizzato: {EXTRANONCE2}")

    while True:
        try:
            log.info("=== Nuovo ciclo di mining ===")

            # STEP 1) Ottieni una nuova connessione per il template
            rpc_template = connect_rpc()

            # STEP 2) GET BLOCK TEMPLATE
            template = get_block_template(rpc_template)
            if not template:
                log.error("Impossibile ottenere il template del blocco. Riprovo...")
                time.sleep(5)
                continue

            # STEP 3) Assicurarsi di avere transazioni con dati completi
            ensure_witness_data(rpc_template, template)

            tot_tx       = len(template["transactions"])
            witness_tx   = sum(1 for tx in template["transactions"] if is_segwit_tx(tx["data"]))
            legacy_tx    = tot_tx - witness_tx

            log.info(f"Transazioni nel template: totali = {tot_tx}  |  legacy = {legacy_tx}  |  segwit = {witness_tx}")

            # STEP 4) COSTRUISCI COINBASE
            miner_info = rpc_template.getaddressinfo(config.WALLET_ADDRESS)
            miner_script_pubkey = miner_info["scriptPubKey"]
            coinbase_tx, coinbase_txid = build_coinbase_transaction(
                template, miner_script_pubkey, EXTRANONCE1, EXTRANONCE2, config.COINBASE_MESSAGE
            )
            log.info(f"Messaggio nella coinbase: {config.COINBASE_MESSAGE}")

            # STEP 5) MODIFICA TARGET
            modified_target = modifica_target(template, rpc_template)

            # STEP 6) CALCOLA MERKLE ROOT
            merkle_root = calculate_merkle_root(coinbase_txid, template["transactions"])

            # STEP 7) COSTRUISCI HEADER
            header_hex = build_block_header(
                template["version"], template["previousblockhash"],
                merkle_root, template["curtime"], template["bits"], 0
            )

            # ---------- watchdog: avvia thread di controllo best-block ----------
            stop_event = threading.Event()
            rpc_watch  = connect_rpc()
            t_watch = threading.Thread(
                target=watchdog_bestblock, args=(rpc_watch, stop_event), daemon=True
            )
            t_watch.start()

            # STEP 8) MINING
            nonce_mode = config.NONCE_MODE
            mined_header_hex, nonce, hashrate = mine_block(
                header_hex, modified_target, nonce_mode, stop_event
            )

            # ---------- chiusura watchdog ----------
            stop_event.set()
            t_watch.join(timeout=0.2)

            # se il mining è stato interrotto da nuovo blocco → ricomincia il ciclo
            if mined_header_hex is None:
                log.info("Nuovo blocco minato: riparto con un template aggiornato")
                continue

            # STEP 9) SERIALIZZA IL BLOCCO
            serialized_block = serialize_block(
                mined_header_hex, coinbase_tx, template["transactions"]
            )
            if not serialized_block:
                log.error("Blocco non serializzato correttamente. Riprovo...")
                continue

            # STEP 10) CALCOLA L'HASH DEL BLOCCO E INVIALO
            # Calcola l'hash del blocco dall'header
            header_bytes = bytes.fromhex(mined_header_hex)
            block_hash = hashlib.sha256(hashlib.sha256(header_bytes).digest()).digest()[::-1].hex()
            log.info(f"Hash del blocco trovato: {block_hash}")
            
            # Invia il blocco
            rpc_submit = connect_rpc()
            submit_block(rpc_submit, serialized_block)

        except Exception:
            log.exception("Errore nel ciclo di mining")

        # Pausa prima di iniziare un nuovo ciclo
        log.info("Ciclo completato, in attesa del prossimo ciclo...")
        time.sleep(1)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    main()
