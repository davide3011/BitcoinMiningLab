import json
import logging
from pathlib import Path

from utils import double_sha256           # funzioni di hashing comuni
from block_builder import serialize_block # serializzazione header+tx
from main import EXTRANONCE1              # extranonce1 comunicato dal server
from rpc import connect_rpc, submit_block

###############################################################################
# Helper di basso livello                                                     
###############################################################################

def be_hex_to_le_bytes(hex_str: str) -> bytes:
    """Converte stringa hex *big‑endian* in bytes *little‑endian*."""
    return bytes.fromhex(hex_str)[::-1]


def calculate_merkle_root_from_transactions(coinbase_txid: str, transactions: list[dict]) -> str:
    """Calcola la radice dell'albero di Merkle per una lista di ID di transazioni."""
    from binascii import unhexlify, hexlify
    
    # foglie in formato bytes-LE
    # Tutti gli hash devono essere in formato little-endian per il calcolo interno
    # coinbase_txid è già in formato hex big-endian, lo convertiamo in bytes little-endian
    # Gli hash delle transazioni nel template sono in formato hex big-endian, li convertiamo in bytes little-endian
    tx_hashes = [unhexlify(coinbase_txid)[::-1]] + [
        unhexlify(tx["hash"])[::-1] for tx in transactions
    ]

    while len(tx_hashes) > 1:
        if len(tx_hashes) % 2:
            tx_hashes.append(tx_hashes[-1])
        tx_hashes = [
            double_sha256(tx_hashes[i] + tx_hashes[i+1])
            for i in range(0, len(tx_hashes), 2)
        ]

    return hexlify(tx_hashes[0][::-1]).decode()


def build_block_header(version_be_hex: str, prev_hash_le_hex: str, merkle_root_le: bytes,
                       ntime_be_hex: str, nbits_be_hex: str, nonce_be_hex: str) -> bytes:
    """Assembla l'header a 80 B pronto per l'hash (tutti campi LE)."""
    parts = [
        be_hex_to_le_bytes(version_be_hex),        # Version   (4 B LE)
        bytes.fromhex(prev_hash_le_hex),           # PrevHash  (32 B LE)
        merkle_root_le,                            # MerkleRoot(32 B LE)
        be_hex_to_le_bytes(ntime_be_hex),          # nTime     (4 B LE)
        be_hex_to_le_bytes(nbits_be_hex),          # nBits     (4 B LE)
        be_hex_to_le_bytes(nonce_be_hex),          # Nonce     (4 B LE)
    ]
    return b"".join(parts)

###############################################################################
# Main workflow                                                               
###############################################################################

def load_json(path: str):
    return json.loads(Path(path).read_text())


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    log = logging.getLogger("sender")

    # ─ 1. Carica artefatti (server ↔ miner) ──────────────────────────────────
    job = load_json("job.json")           # notify generato dal server
    sol = load_json("solution.json")      # share trovata dal miner
    tmpl = load_json("template.json")     # getblocktemplate originario

    # ─ 2. Ricostruisci la coinbase grezza ────────────────────────────────────
    coinbase_hex = job["coinb1"] + EXTRANONCE1 + sol["params"][2] + job["coinb2"]
    coinbase_txid = double_sha256(bytes.fromhex(coinbase_hex))[::-1].hex()

    # ─ 3. Merkle‑root (little‑endian) ────────────────────────────────────────
    merkle_root_hex = calculate_merkle_root_from_transactions(coinbase_txid, tmpl["transactions"])
    # Il merkle_root_hex è già in formato corretto (big-endian), lo convertiamo in little-endian
    merkle_root_le = bytes.fromhex(merkle_root_hex)[::-1]

    # ─ 4. Header da 80 B (little‑endian) e hash di blocco ────────────────────
    header_bytes = build_block_header(
        job["version"],           # version big‑endian nel job
        job["prevhash"],          # già little‑endian
        merkle_root_le,
        sol["params"][3],         # nTime usato dal miner (BE)
        job["nbits"],             # nBits dal job (BE)
        sol["params"][4]          # Nonce trovato (BE)
    )
    header_hex = header_bytes.hex()
    block_hash = double_sha256(header_bytes)[::-1].hex()

    log.info("Header  : %s", header_hex)
    log.info("Blocco  : %s", block_hash)

    # ─ 5. Serializza il blocco completo ──────────────────────────────────────
    raw_block_hex = serialize_block(header_hex, coinbase_hex, tmpl["transactions"])

    # ─ 6. Scrivi rebuildblock.json con le sole info richieste ───────────────
    minimal = {
        "hash": block_hash,
        "header": header_hex,
        "serialized_block": raw_block_hex
    }
    Path("rebuildblock.json").write_text(json.dumps(minimal, indent=2))
    log.info("Creato rebuildblock.json (hash, header, serialized_block)")

    # ─ 7. (Opzionale) invia il blocco al nodo regtest ───────────────────────
    rpc = connect_rpc()
    submit_block(rpc, raw_block_hex)


if __name__ == "__main__":
    main()
