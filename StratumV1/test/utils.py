"""Modulo di utilità comune per funzioni condivise nel progetto miner."""

import logging, hashlib, config, time, json
from typing import List
from typing import Tuple
import secrets
log = logging.getLogger(__name__)

def double_sha256(data):
    """Esegue il doppio SHA-256 su un dato."""
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()

def swap_endian(hex_str: str) -> str:
    """Inverte l'ordine dei byte in una stringa esadecimale (cambio endianess)."""
    hex_str = hex_str.strip()

    if len(hex_str) % 2 != 0:
        raise ValueError("La stringa deve avere un numero pari di caratteri (ogni byte = 2 caratteri).")

    return bytes.fromhex(hex_str)[::-1].hex()

def encode_varint(value):
    """Codifica un numero come VarInt secondo il protocollo Bitcoin."""
    thresholds = [(0xfd, ""), (0xffff, "fd"), (0xffffffff, "fe"), (0xffffffffffffffff, "ff")]
    
    for threshold, prefix in thresholds:
        if value <= threshold:
            byte_length = max(1, (threshold.bit_length() + 7) // 8)
            return prefix + value.to_bytes(byte_length, 'little').hex()
            
    raise ValueError("Il valore supera il limite massimo per VarInt (2^64-1)")

def decode_nbits(nBits: int) -> str:
    """Decodifica il campo nBits in un target a 256-bit in formato esadecimale."""
    exponent = (nBits >> 24) & 0xff
    significand = nBits & 0x007fffff
    return f"{(significand << (8 * (exponent - 3))):064x}"

def target_to_nbits(target_hex):
    """Converte un target esadecimale in formato nbits compatto."""
    target_int = int(target_hex, 16)
    if target_int == 0:
        return "00000000"
    
    # Trova il numero di byte necessari
    target_bytes = target_int.to_bytes(32, 'big')
    # Rimuove i byte zero iniziali
    while len(target_bytes) > 1 and target_bytes[0] == 0:
        target_bytes = target_bytes[1:]
    
    # Se il primo byte ha il bit più significativo impostato, aggiungi un byte zero
    if target_bytes[0] & 0x80:
        target_bytes = b'\x00' + target_bytes
    
    # Prendi solo i primi 3 byte per il significand
    if len(target_bytes) > 3:
        significand = int.from_bytes(target_bytes[:3], 'big')
        exponent = len(target_bytes)
    else:
        significand = int.from_bytes(target_bytes, 'big')
        exponent = len(target_bytes)
    
    # Costruisci nbits: exponent (1 byte) + significand (3 byte)
    nbits = (exponent << 24) | significand
    return format(nbits, "08x")

def calculate_target(template, difficulty_factor, network):
    """Calcola il target modificato in base al fattore di difficoltà per qualsiasi network."""
    nBits_int = int(template["bits"], 16)
    original_target = decode_nbits(nBits_int)
    
    if difficulty_factor == 0:
        return original_target
    else:
        max_target = 0x00000000FFFF0000000000000000000000000000000000000000000000000000
        target_value = int(max_target / difficulty_factor)
        max_possible_target = (1 << 256) - 1
        if target_value > max_possible_target:
            target_value = max_possible_target
        return f"{target_value:064x}"

def modifica_target(template, rpc_conn):
    """Modifica il target di mining in base al fattore di difficoltà per qualsiasi network."""
    log = logging.getLogger(__name__)
    blockchain_info = rpc_conn.getblockchaininfo()
    network = blockchain_info.get("chain", "")
    difficulty_factor = float(config.DIFFICULTY_FACTOR)
    
    if difficulty_factor < 0:
        log.error("DIFFICULTY_FACTOR non può essere negativo. Utilizzo target del template.")
        difficulty_factor = 0  # Forza al target del template
    elif difficulty_factor == 0:
        log.info(f"Rete {network} rilevata: utilizzo target del template (DIFFICULTY_FACTOR = 0)")
        difficulty_factor = 0  # Porta pari al template
    else:
        log.info(f"Rete {network} rilevata: utilizzo DIFFICULTY_FACTOR = {difficulty_factor}")
    
    return calculate_target(template, difficulty_factor, network)

def generate_extranonce2(size_bytes):
    """Genera un extranonce2 casuale della dimensione specificata.
    
    Args:
        size_bytes: Dimensione in byte dell'extranonce2 da generare
        
    Returns:
        str: Extranonce2 in formato esadecimale
    """
    # Genera bytes casuali usando secrets.randbits per compatibilità
    random_bits = secrets.randbits(size_bytes * 8)
    extranonce2_hex = f"{random_bits:0{size_bytes*2}x}"
    log.info(f"Extranonce2 generato: {extranonce2_hex} ({size_bytes} byte)")
    return extranonce2_hex

def split_coinbase(coinbase_hex: str, ex1: str, ex2: str) -> Tuple[str, str, str, str]:
    """Restituisce (coinb1, extranonce1, extranonce2, coinb2).

    Il taglio avviene esattamente:
    - coinb1 termina prima del primo byte di extranonce1 (R-1)
    - coinb2 inizia subito dopo l'ultimo byte di extranonce2 (R-2)
    Tutto in esadecimale minuscolo senza prefissi (R-5).
    """
    h = coinbase_hex.lower()
    ex1 = ex1.lower()
    ex2 = ex2.lower()
    idx_ex1 = h.find(ex1)
    if idx_ex1 == -1:
        raise ValueError("extranonce1 non trovato nella coinbase")
    idx_ex2 = idx_ex1 + len(ex1)
    if h[idx_ex2:idx_ex2+len(ex2)] != ex2:
        raise ValueError("extranonce2 non segue immediatamente extranonce1")
    coinb1 = h[:idx_ex1]
    extranonce1 = h[idx_ex1:idx_ex1+len(ex1)]
    extranonce2 = h[idx_ex2:idx_ex2+len(ex2)]
    coinb2 = h[idx_ex2+len(ex2):]
    return coinb1, extranonce1, extranonce2, coinb2

def calculate_merkle_branch(template) -> List[str]:
    """
    Accetta il getblocktemplate (dict o stringa JSON) e restituisce
    il merkle_branch per la `mining.notify` Stratum V1.

    Ritorna una lista di stringhe hex (32 byte ciascuna, **little-endian**),
    pronte per essere inserite nel messaggio Stratum.
    """
    # Se template è una stringa JSON, la convertiamo in dict
    if isinstance(template, str):
        gbt = json.loads(template)
    else:
        # Se è già un dict, lo usiamo direttamente
        gbt = template

    # 1) Hash (txid) delle transazioni ESCLUSA la coinbase (già in little-endian)
    tx_hashes = [bytes.fromhex(tx["hash"][::-1]) for tx in gbt["transactions"]]

    # 2) Inseriamo all’inizio un placeholder di 32 byte a zero: hash della coinbase che il miner genererà.
    layer = [b"\x00" * 32] + tx_hashes
    index = 0            # posizione della coinbase nella lista
    branch: List[bytes] = []

    # 3) Costruzione dell’albero finché non rimane il solo root.
    while len(layer) > 1:
        # Se dispari duplichiamo l’ultimo (rule di Bitcoin e Stratum).
        if len(layer) & 1:
            layer.append(layer[-1])

        # Il nodo “fratello” del coinbase in questo livello:
        sibling_index = index ^ 1
        branch.append(layer[sibling_index])

        # Passo al livello superiore unendo le coppie.
        layer = [double_sha256(layer[i] + layer[i + 1])
                 for i in range(0, len(layer), 2)]
        index //= 2

    # 4) Converto in hex (little-endian) per lo Stratum.
    return [h.hex() for h in branch]

def create_mining_notify_params(template, coinb1, coinb2, merkle_branch):
    """Crea i parametri per il messaggio mining.notify di Stratum v1."""
    
    job_id = format(int(time.time()*1000) & 0xffffffff, "08x")           # Genera job ID univoco basato sul timestamp
    prev_hash_le = swap_endian(template["previousblockhash"])            # Hash del blocco precedente convertito in little-endian    
    version_hex = format(template["version"] & 0xffffffff, "08x")        # Versione del blocco in formato esadecimale
    bits_hex = template["bits"]                                 
    ntime_hex = format(template["curtime"], "08x")                         # Timestamp dal template
    clean_jobs = True                                                    # Flag per indicare che i job precedenti devono essere scartati
    
    return {
        'job_id': job_id,
        'prevhash': prev_hash_le,
        'coinb1': coinb1,
        'coinb2': coinb2,
        'merkle_branch': merkle_branch,
        'version': version_hex,
        'nbits': bits_hex,
        'ntime': ntime_hex,
        'clean_jobs': clean_jobs
    }

def save_job_json(job_data):
    """Salva i dati del job in job.json nella directory corrente."""
    with open("job.json", "w") as f:
        json.dump(job_data, f, indent=2)

def save_template_json(template_data):
    """Salva i dati del template in template.json nella directory corrente."""
    with open("template.json", "w") as f:
        json.dump(template_data, f, indent=2)
