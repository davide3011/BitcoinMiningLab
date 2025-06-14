import json
import logging
import time
import secrets
from typing import List

from utils import double_sha256, decode_nbits  # funzioni condivise nel progetto
from main import EXTRANONCE1                   # costante definita dal server

log = logging.getLogger(__name__)

JOB_PATH = "job.json"              # file con il notify serializzato
SIZE_EXTRANONCE2 = 4               # lunghezza in byte dell'extranonce2 casuale

# ════════════════════════════════════════════════════════════════════
#  Helper
# ════════════════════════════════════════════════════════════════════

def load_job(path: str = JOB_PATH) -> dict:
    """Carica il job Stratum salvato su disco."""
    with open(path, "r", encoding="utf-8") as f:
        job = json.load(f)
    log.info("Job %s caricato (height = %s)", job["job_id"], job.get("height", "?"))
    return job


def generate_extranonce2(size_bytes: int = SIZE_EXTRANONCE2) -> str:
    """Genera un extranonce2 casuale di *size_bytes* byte, formato hex."""
    return secrets.token_hex(size_bytes)


def build_coinbase(job: dict, extranonce1: str, extranonce2: str) -> str:
    """Assembla coinbase = coinb1 | ex1 | ex2 | coinb2 (hex)."""
    return job["coinb1"] + extranonce1 + extranonce2 + job["coinb2"]


def calc_merkle_root(coinbase_hash_le: bytes, branch_le: List[str]) -> bytes:
    """Calcola la Merkle‑root (little‑endian) usando il branch già LE del job."""
    h = coinbase_hash_le
    for sibling_hex in branch_le:
        h = double_sha256(h + bytes.fromhex(sibling_hex))[::-1]  # output → LE
    return h


def header_bytes(version_be: str, prevhash_le: str, root_le: bytes,
                 ntime: int, nbits_be: str, nonce: int) -> bytes:
    """Serializza l'header (80 byte) pronto per l'hash.

    Tutti gli hash sono già little‑endian (prevhash, merkle_root).
    version, nbits e ntime vengono convertiti localmente.
    """
    return (bytes.fromhex(version_be)[::-1] +                 # Version (LE)
            bytes.fromhex(prevhash_le) +                      # Prev‑hash (LE)
            root_le +                                         # Merkle‑root (LE)
            ntime.to_bytes(4, "little") +                    # Timestamp (LE)
            bytes.fromhex(nbits_be)[::-1] +                   # nBits (LE)
            nonce.to_bytes(4, "little"))                     # Nonce  (LE)

# ════════════════════════════════════════════════════════════════════
#  Main mining routine
# ════════════════════════════════════════════════════════════════════

def mine(job: dict, extranonce1: str, max_nonce: int = 2**32):
    """Brute‑forza il nonce fino a trovare uno share ≤ target."""

    # Target (256‑bit big‑endian): se non fornito nel job lo ricavi da nBits
    target_hex = job.get("target") or decode_nbits(int(job["nbits"], 16))
    target_int = int(target_hex, 16)

    # 1) Extranonce2 casuale e coinbase
    extranonce2 = generate_extranonce2()
    coinbase_hex = build_coinbase(job, extranonce1, extranonce2)
    coinbase_hash_le = double_sha256(bytes.fromhex(coinbase_hex))[::-1]

    # 2) Merkle‑root (LE) a partire dal branch fornito (già LE)
    merkle_root_le = calc_merkle_root(coinbase_hash_le, job["merkle_branch"])

    # 3) Parametri statici dell'header
    version_be   = job["version"].lower()      # es. "20000000"
    prevhash_le  = job["prevhash"].lower()
    nbits_be     = job["nbits"].lower()
    base_ntime   = int(job["ntime"], 16)

    start = time.time()
    for nonce in range(max_nonce):
        ntime = base_ntime + (nonce // 100_000)   # roll del timestamp ogni 100 k tentativi
        header = header_bytes(version_be, prevhash_le, merkle_root_le,
                              ntime, nbits_be, nonce)
        hash_be = double_sha256(header)[::-1]     # ottieni big‑endian per comparazione

        if int.from_bytes(hash_be, "big") <= target_int:
            elapsed = time.time() - start
            log.info("Share trovata in %.2f s — nonce=%08x", elapsed, nonce)

            solution = {
                "method": "mining.submit",
                "params": [
                    "miner.worker",          # worker ID
                    job["job_id"],
                    extranonce2,
                    f"{ntime:08x}",
                    f"{nonce:08x}"
                ]
            }
            debug = {
                "header": header.hex(),
                "hash":   hash_be.hex(),
                "merkle_root_le": merkle_root_le.hex(),
                "merkle_root_be": merkle_root_le[::-1].hex(),
                "coinbase": coinbase_hex,
                "extranonce1": extranonce1,
                "extranonce2": extranonce2,
                "ntime": f"{ntime:08x}",
                "nonce": f"{nonce:08x}"
            }
            return {"solution": solution, "debug": debug}

    return None  # nessun share entro max_nonce

# ════════════════════════════════════════════════════════════════════
#  Persistenza risultati
# ════════════════════════════════════════════════════════════════════

def save_json(obj: dict, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)
    log.info("File %s scritto", path)

# ════════════════════════════════════════════════════════════════════
#  Entry‑point
# ════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s | %(levelname)s | %(message)s")

    job_data = load_job()
    result = mine(job_data, EXTRANONCE1)

    if result:
        save_json(result["solution"], "solution.json")
        save_json(result["debug"],    "block_found.json")
    else:
        log.info("Nessuna soluzione trovata entro il limite di nonce")
