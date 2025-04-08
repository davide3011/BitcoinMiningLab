from bitcoin_rpc import connect_rpc, rpc_call
from utils import (
    encode_varint,
    push_data,
    base58_decode,
    bech32_hrp_expand,
    bech32_polymod,
    bech32_verify_checksum,
    bech32_decode,
    convertbits,
    address_to_scriptPubKey
)
from typing import Tuple
import config
import requests
import json
import struct
import hashlib
import time

from merkle import build_merkle_tree, extract_merkle_branch
from typing import Tuple
import config

EXTRANONCE_PLACEHOLDER = b"{{extranonce}}"

##########################################
# Costruzione della coinbase transaction
##########################################

def build_coinbase_tx(coinbase_value: int, coinbase_address: str, coinbase_message: str, block_template: dict) -> str:
    """
    Costruisce la coinbase transaction usando i parametri del block template.

    Se "!segwit" è presente in block_template["rules"], forziamo la modalità legacy
    anche se c'è "default_witness_commitment". Altrimenti, se "segwit" è
    presente o se troviamo "default_witness_commitment", costruiamo segwit.
    """
    # 1. Determiniamo se segwit è effettivamente attivo:
    rules = block_template.get("rules", [])
    if "!segwit" in rules:
        segwit_active = False
    else:
        # In regtest potrebbe esserci "segwit", "taproot", "csv"...
        # oppure semplicemente la presenza di "default_witness_commitment"
        # Indicherebbe un nodo che si aspetta il witness. Flessibilità:
        segwit_active = ("segwit" in rules) or ("default_witness_commitment" in block_template)

    # 2. Versione
    version = struct.pack("<I", 2)

    # 3. Input count: sempre 1 per la coinbase
    input_count = encode_varint(1)

    # 4. Prevout nullo (32 zero bytes + 0xffffffff)
    prevout = b'\x00' * 32 + b'\xff\xff\xff\xff'

    # 5. Blocco height
    block_height = block_template.get("height", 0)
    if block_height == 0:
        height_bytes = b'\x00'
    else:
        height_bytes = block_height.to_bytes((block_height.bit_length() + 7) // 8, 'little')

    # 6. Costruisce lo scriptSig: push(height) || EXTRANONCE_PLACEHOLDER || push(coinbase_message)
    height_push = push_data(height_bytes)
    msg_bytes = coinbase_message.encode('utf8')
    msg_push = push_data(msg_bytes)

    scriptSig = height_push + EXTRANONCE_PLACEHOLDER + msg_push
    scriptSig_length = encode_varint(len(scriptSig))

    sequence = b'\xff\xff\xff\xff'
    coinbase_input = prevout + scriptSig_length + scriptSig + sequence

    # 7. Output(s)
    outputs = b""
    output_value = struct.pack("<Q", coinbase_value)
    address_script_hex = address_to_scriptPubKey(coinbase_address)
    address_script = bytes.fromhex(address_script_hex)
    address_script_length = encode_varint(len(address_script))
    output1 = output_value + address_script_length + address_script
    outputs += output1

    if segwit_active and "default_witness_commitment" in block_template:
        # Aggiungi witness commitment come secondo output
        wc_hex = block_template["default_witness_commitment"]
        wc_script = bytes([0x6a, 0x24]) + bytes.fromhex("aa21a9ed") + bytes.fromhex(wc_hex)
        wc_script_length = encode_varint(len(wc_script))
        wc_value = struct.pack("<Q", 0)
        output2 = wc_value + wc_script_length + wc_script
        outputs += output2
        output_count = encode_varint(2)
    else:
        output_count = encode_varint(1)

    # 8. Locktime = 0
    locktime = b'\x00\x00\x00\x00'

    # 9. Costruiamo la transazione
    if segwit_active:
        # marker (0x00) e flag (0x01) e witness vuoto per coinbase
        marker_flag = b'\x00\x01'
        witness_count = encode_varint(0)
        tx = version + marker_flag + input_count + coinbase_input + output_count + outputs + witness_count + locktime
    else:
        # legacy
        tx = version + input_count + coinbase_input + output_count + outputs + locktime

    return tx.hex()

def split_coinbase(tx_hex: str) -> Tuple[str, str]:
    """
    Divide la coinbase transaction in coinb1 e coinb2 in corrispondenza del placeholder.
    coinb1: tutto ciò che precede il placeholder
    coinb2: tutto ciò che segue il placeholder
    """
    marker = EXTRANONCE_PLACEHOLDER.hex()
    index = tx_hex.find(marker)
    if index == -1:
        raise ValueError("Placeholder per l'extranonce non trovato nella coinbase")
    coinb1 = tx_hex[:index]
    coinb2 = tx_hex[index + len(marker):]
    return coinb1, coinb2

###############################################################
# Main: chiamata al nodo e costruzione della coinbase
###############################################################

def main():
    while True:
        try:
            # Connessione RPC e recupero del block template
            rpc = connect_rpc()
            block_template = rpc.getblocktemplate({"rules": ["segwit"]})
            print("Block Template ottenuto:")
            # Mostra i parametri principali (escludendo la lista delle transazioni)
            print(json.dumps({k: v for k, v in block_template.items() if k != 'transactions'}, indent=4))

            # 1. Costruisci la coinbase transaction
            coinbase_value = block_template["coinbasevalue"]
            raw_coinbase_tx = build_coinbase_tx(
                coinbase_value,
                config.COINBASE_ADDRESS,
                config.COINBASE_MESSAGE,
                block_template
            )
            print("\nCoinbase Transaction (raw):")
            print(raw_coinbase_tx)

            # Dividi la coinbase in coinb1 e coinb2
            coinb1, coinb2 = split_coinbase(raw_coinbase_tx)
            print("\nCoinbase1:")
            print(coinb1)
            print("\nCoinbase2:")
            print(coinb2)

            # 2. Costruisci la lista delle transazioni per l'albero Merkle
            # In un blocco reale, la prima transazione deve essere la coinbase.
            # Se il template contiene già una lista di transazioni, aggiungi la coinbase in testa.
            txs = block_template.get("transactions", [])
            # Prepara la lista delle foglie (txid) inserendo la coinbase in posizione 0.
            # Qui, supponiamo che la coinbase abbia un txid, che puoi calcolare (ad esempio, il doppio SHA256 del raw tx).
            # Per semplicità, useremo l'hash della coinbase come txid:
            coinbase_txid = hashlib.sha256(hashlib.sha256(bytes.fromhex(raw_coinbase_tx)).digest()).hexdigest()
            leaves = [coinbase_txid]
            # Aggiungi gli txid delle altre transazioni, se presenti.
            leaves += [tx["txid"] for tx in txs]
            print(f"\nNumero di transazioni (foglie): {len(leaves)}")

            # 3. Costruisci l'albero Merkle usando il modulo merkle.py
            tree = build_merkle_tree(leaves)
            merkle_root = tree[-1][0]
            print("\nMerkle Root calcolato:")
            print(merkle_root)

            # 4. Estrai la Merkle branch per la coinbase (foglia indice 0)
            branch = extract_merkle_branch(tree, 0)
            print("\nMerkle Branch per la foglia (coinbase, indice 0):")
            for lvl, h in enumerate(branch):
                print(f"Livello {lvl}: {h}")

            # A questo punto, il job che il pool dovrà inviare ai miner dovrà includere:
            # - coinb1, coinb2, extranonce1 (preso dalla subscribe, ad es. "1a2b3c4d" dal template di subscribe)
            # - extranonce2_size (numero di byte, es. 4)
            # - Merkle branch (estratta qui)
            # - previousblockhash, version, nbits/target, curtime, etc.
            # Puoi assemblare questi dati in un dizionario e inviarli nel messaggio mining.notify.

        except Exception as e:
            print(f"Errore durante l'operazione RPC: {e}")
        time.sleep(config.UPDATE_INTERVAL)

if __name__ == "__main__":
    main()
