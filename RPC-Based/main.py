import time, config
from rpc import connect_rpc, test_rpc_connection, get_block_template, ensure_witness_data, submit_block
from block_builder import decode_nbits, calculate_merkle_root, build_block_header, serialize_block, build_coinbase_transaction
from miner import mine_block

def main():    
    # TEST RPC
    test_rpc_connection()

    while True:
        try:
            print("\033[K\r\n=== Nuovo ciclo di mining ===", end="\r\n\n")
            # STEP 1) Ottieni una nuova connessione per il template
            rpc_template = connect_rpc()

            # STEP 2) GET BLOCK TEMPLATE
            template = get_block_template(rpc_template)
            if not template:
                print("\033[K\rERRORE: Impossibile ottenere il template del blocco. Riprovo...", end="\r\n")
                time.sleep(5)
                continue

            # STEP 3) Assicurarsi di avere transazioni con dati completi
            ensure_witness_data(rpc_template, template)

            # STEP 4) COSTRUISCI COINBASE
            miner_info = rpc_template.getaddressinfo(config.WALLET_ADDRESS)
            miner_script_pubkey = miner_info["scriptPubKey"]
            coinbase_tx = build_coinbase_transaction(template, miner_script_pubkey, config.COINBASE_MESSAGE)
            print(f"\033[K\rMessaggio nella coinbase: {config.COINBASE_MESSAGE}", end="\r\n")

            # STEP 5) MODIFICA TARGET
            # Ottieni informazioni sulla rete
            blockchain_info = rpc_template.getblockchaininfo()
            network = blockchain_info.get("chain", "")
            
            # Imposta DIFFICULTY_FACTOR in base alla rete
            if network == "regtest":
                DIFFICULTY_FACTOR = float(config.DIFFICULTY_FACTOR)
                if DIFFICULTY_FACTOR < 1:
                    print("\033[K\rAttenzione: DIFFICULTY_FACTOR deve essere >= 1. Impostazione a 1.0", end="\r\n")
                    DIFFICULTY_FACTOR = 1.0
            else:  # testnet o mainnet
                DIFFICULTY_FACTOR = 1.0
                print(f"\033[K\rRete {network} rilevata: DIFFICULTY_FACTOR impostato a 1.0", end="\r\n")

            nBits_int = int(template["bits"], 16)
            original_target = decode_nbits(nBits_int)
            modified_target_int = int(original_target, 16) // int(DIFFICULTY_FACTOR)
            modified_target = f"{modified_target_int:064x}"
            print(f"\033[K\rTarget originale: {original_target}", end="\r\n")
            print(f"\033[K\rTarget modificato ({DIFFICULTY_FACTOR}x più difficile): {modified_target}", end="\r\n")

            # STEP 6) CALCOLA MERKLE ROOT
            merkle_root = calculate_merkle_root(coinbase_tx, template["transactions"])

            # STEP 7) COSTRUISCI HEADER
            header_hex = build_block_header(template["version"], template["previousblockhash"],
                                            merkle_root, template["curtime"], template["bits"], 0)

            # STEP 8) MINING
            nonce_mode = config.NONCE_MODE
            mined_header_hex, nonce, hashrate = mine_block(header_hex, modified_target, nonce_mode)
            if not mined_header_hex:
                print("\033[K\rERRORE: Nessun hash valido trovato! Riprovo...", end="\r\n")
                continue
                
            # STEP 9) SERIALIZZA IL BLOCCO
            serialized_block = serialize_block(mined_header_hex, coinbase_tx, template["transactions"])
            if not serialized_block:
                print("\033[K\rERRORE: Blocco non serializzato correttamente. Riprovo...", end="\r\n")
                continue

            # STEP 10) INVIA IL BLOCCO
            rpc_submit = connect_rpc()
            submit_block(rpc_submit, serialized_block)
        except Exception as e:
            print(f"\033[K\rErrore nel ciclo di mining: {e}", end="\r\n")

        # Pausa prima di iniziare un nuovo ciclo
        print("\033[K\rCiclo completato, in attesa del prossimo ciclo...", end="\r\n")
        time.sleep(1)

if __name__ == "__main__":
    main()
