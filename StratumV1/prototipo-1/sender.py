# ──────────────────────────────────────────────────────────────────────────────
#  Ricostruzione e serializzazione del blocco lato pool / test_sender
# ──────────────────────────────────────────────────────────────────────────────
from binascii import unhexlify, hexlify
import json
import logging
import struct
from pathlib import Path
from typing import List

from utils import double_sha256, modifica_target, target_to_nbits
from block_builder import (                       
    build_coinbase_transaction,
    serialize_block, calculate_merkle_root
)
from main import EXTRANONCE1                       # costante fissa del pool
from rpc import connect_rpc, decode_raw_transaction_rpc, submit_block
import config                                      # configurazioni globali

# ════════════════════════════════════════════════════════════════════
#  Helper
# ════════════════════════════════════════════════════════════════════

def build_block_header(version_hex, prev_hash, merkle_root, ntime_hex, bits, nonce_hex):
    """Costruisce l'header del blocco (80 byte) da input esadecimali."""
    header = (
        unhexlify(version_hex)[::-1] +             # Version (4 byte, little-endian)
        unhexlify(prev_hash)[::-1] +               # Previous Block Hash (32 byte, little-endian)
        unhexlify(merkle_root)[::-1] +             # Merkle Root (32 byte, little-endian)
        unhexlify(ntime_hex)[::-1] +               # Timestamp (4 byte, little-endian)
        unhexlify(bits)[::-1] +                    # Bits/Target (4 byte, little-endian)
        unhexlify(nonce_hex)[::-1]                 # Nonce (4 byte, little-endian)
    )
    return hexlify(header).decode()

# ════════════════════════════════════════════════════════════════════
#  Core workflow
# ════════════════════════════════════════════════════════════════════

def load_json(path: str) -> dict:
    return json.loads(Path(path).read_text())


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s | %(message)s")
    log = logging.getLogger("sender")

    # 1. Artefatti
    job   = load_json("job.json")        # mining.notify
    share = load_json("solution.json")   # mining.submit
    tmpl  = load_json("template.json")   # getblocktemplate originale

    extranonce1 = bytes.fromhex(EXTRANONCE1).hex()            # Convert to little-endian
    extranonce2 = bytes.fromhex(share["extranonce2"]).hex()   # Convert to little-endian
    ntime_hex = share["ntime"].zfill(8)                       # Normalizza a 4 byte (8 cifre hex)
    nonce_hex = bytes.fromhex(share["nonce"]).hex().zfill(8)  # Normalizza a 4 byte (8 cifre hex)

    # 2. Ricrea coinbase (placeholder commitment) con builder
    rpc_temp = connect_rpc()
    miner_info = rpc_temp.getaddressinfo(config.WALLET_ADDRESS)
    miner_spk = miner_info["scriptPubKey"]
    
    
    coinbase_hex, coinbase_txid, coinbase_hash = build_coinbase_transaction(
        tmpl, miner_spk, extranonce1, extranonce2, config.COINBASE_MESSAGE
    )

    log.info(f"Coinbase_hex: {coinbase_hex}")
    log.info(f"Coinbase_txid: {coinbase_txid}")
    log.info(f"Coinbase_hash: {coinbase_hash}")
    
    # 3. CALCOLA MERKLE ROOT
    merkle_root = calculate_merkle_root(coinbase_txid, tmpl["transactions"])

    # 3.5. CALCOLA BITS MODIFICATI (come in main.py)
    rpc_target = connect_rpc()
    target = modifica_target(tmpl, rpc_target)
    modified_bits = target_to_nbits(target)

    # 4. COSTRUISCI HEADER
    version_hex = f"{tmpl['version']:08x}"
    header_hex = build_block_header(
                version_hex, tmpl["previousblockhash"],
                merkle_root, ntime_hex, modified_bits, nonce_hex
            )

    block_hash = double_sha256(unhexlify(header_hex))[::-1].hex()
    log.info(f"Version: {version_hex}")
    log.info(f"previousblockhash: {tmpl['previousblockhash']}")
    log.info(f"merkle_root: {merkle_root}")
    log.info(f"timestamp: {ntime_hex}")
    log.info(f"bits: {modified_bits}")
    log.info(f"nonce: {nonce_hex}")
    log.info(f"lunghezza header: {len(header_hex)}")
    log.info(f"Header: {header_hex}")
    log.info(f"Hash del blocco trovato: {block_hash}")
    


    # 5. Blocco completo
    raw_block_hex = serialize_block(header_hex, coinbase_hex, tmpl["transactions"])

    # 8. (facoltativo) invialo al nodo
    rpc = connect_rpc()
    submit_block(rpc, raw_block_hex)


if __name__ == "__main__":
    main()