import json
import struct
import hashlib
import time
import logging
import os
import socket
import stratum_client

# Configurazione del logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Miner")

def load_config():
    with open("conf.json", "r") as f:
        return json.load(f)

# Carica la configurazione
config = load_config()

# Parametri letti da conf.json
USERNAME = config["username"]

# Funzione per leggere il job dal file JSON
def read_job():
    try:
        with open("job.json", "r") as f:
            job = json.load(f)
        logger.info("Job caricato con successo!")
        return job
    except Exception as e:
        logger.error(f"Errore nel leggere il job: {e}")

# Funzione per il doppio SHA-256
def double_sha256(data):
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()

# Funzione per costruire la coinbase transaction."""
def build_coinbase(job, extranonce1, extranonce2):
    extranonce2_size = job["extranonce2_size"] * 2  # Lunghezza in caratteri esadecimali
    extranonce2 = extranonce2.zfill(extranonce2_size)  # Padding con zeri se necessario
    
    coinbase_hex = job["coinbase1"] + extranonce1 + extranonce2 + job["coinbase2"]
    coinbase_bytes = bytes.fromhex(coinbase_hex)

    return double_sha256(coinbase_bytes).hex()

# Funzione per calcolare la merkle root.
def calculate_merkle_root(job, coinbase_hash):
    merkle_root = bytes.fromhex(coinbase_hash)
    
    for branch in job["merkle_branch"]:
        merkle_root = double_sha256(merkle_root + bytes.fromhex(branch))
    
    return merkle_root.hex()

# Funzione per creare l'header del blocco in formato binario.
def build_block_header(job, merkle_root, nonce):
    header = (
        bytes.fromhex(job["version"])[::-1] +   
        bytes.fromhex(job["prevhash"])[::-1] +  
        bytes.fromhex(merkle_root)[::-1] +      
        bytes.fromhex(job["ntime"])[::-1] +      
        bytes.fromhex(job["nbits"])[::-1] +      
        struct.pack("<I", nonce)                 
    )
    return header
    
# Funzione per convertire nbits in target.
def nbits_to_target(nbits):
    nbits = int(nbits, 16)
    exponent = (nbits >> 24) & 0xFF
    mantissa = nbits & 0xFFFFFF
    return mantissa * (1 << (8 * (exponent - 3)))

# Funzione per inviare la share al pool.
def submit_share(job, nonce, extranonce2):
    worker = USERNAME
    job_id = job["job_id"]
    ntime = job["ntime"]
    nonce_hex = format(nonce, "08x")

    submit_data = {
        "id": 3,
        "method": "mining.submit",
        "params": [worker, job_id, extranonce2, ntime, nonce_hex]
    }

    logger.info(f"Sending share: {json.dumps(submit_data, indent=4)}")

    try:
        stratum_client.send_message(submit_data)
        logger.info("Share inviata con successo!")
    except Exception as e:
        logger.error(f"Errore nell'invio della share: {e}")
    
# Funzione per la ricerca del nonce.
def mine():
    last_job_mtime = 0
    extranonce2_counter = 0
    BATCH_SIZE = 10000  

    while True:
        job_mtime = os.path.getmtime("job.json")
        if job_mtime > last_job_mtime:
            last_job_mtime = job_mtime
            job = read_job()
            if not job:
                logger.warning("Nessun job disponibile, in attesa...")
                time.sleep(1)
                continue

            logger.info("Nuovo job ricevuto! Riparto con il mining.")

            extranonce1 = job["extranonce1"]
            extranonce2_size = job["extranonce2_size"]
            extranonce2_counter = 0  
            
            target_dec = nbits_to_target(job["nbits"])
            logger.info(f"Target Decimale: {target_dec}")

            nonce = 0
            start_time = time.time()
            total_hashes = 0  

            while True:
                for _ in range(BATCH_SIZE):
                    extranonce2 = f"{extranonce2_counter:0{extranonce2_size * 2}x}"
                    coinbase_hash = build_coinbase(job, extranonce1, extranonce2)
                    merkle_root = calculate_merkle_root(job, coinbase_hash)
                    block_header = build_block_header(job, merkle_root, nonce)
                    hash_result = double_sha256(block_header)
                    hash_int = int.from_bytes(hash_result, byteorder="big")

                    if hash_int < target_dec:
                        logger.info(f"SHARE TROVATA! Nonce: {nonce}")
                        logger.info(f"Hash: {hash_result.hex()}")

                        submit_share(job, nonce, extranonce2)
                        extranonce2_counter += 1  # Incrementa solo dopo una share valida

                    nonce += 1

                total_hashes += BATCH_SIZE
                elapsed_time = time.time() - start_time
                hashrate = total_hashes / elapsed_time
                logger.info(f"Hash Rate: {hashrate:.2f} H/s")

        time.sleep(1)

if __name__ == "__main__":
    job = read_job()
    if job:
        mine()  
