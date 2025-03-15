import struct, random, time
from binascii import hexlify, unhexlify
from block_builder import double_sha256
import config

def mine_block(header_hex, target_hex, nonce_mode="incremental"):
    """
    Esegue il mining cercando un nonce valido rispetto al target.
    
    - `incremental`: parte da 0 e incrementa di 1 fino al massimo valore possibile.
    - `random`: genera un nonce casuale a ogni iterazione.
    - `mixed`: genera un primo nonce casuale, poi incrementa di 1.
    
    Aggiorna il timestamp nell'header del blocco ogni TIMESTAMP_UPDATE_INTERVAL secondi.
    """
    print(f"\n=== Inizio del Mining | Modalità: {nonce_mode} ===")

    target = int(target_hex, 16)
    # Estrai le parti dell'header per poterle aggiornare separatamente
    version = unhexlify(header_hex[:8])
    prev_hash = unhexlify(header_hex[8:72])
    merkle_root = unhexlify(header_hex[72:136])
    timestamp_bytes = unhexlify(header_hex[136:144])
    bits = unhexlify(header_hex[144:152])
    
    # Timestamp iniziale e ultimo aggiornamento
    current_timestamp = struct.unpack("<I", timestamp_bytes)[0]
    last_timestamp_update = time.time()
    
    attempts = 0  # Contatore tentativi

    # Imposta il nonce iniziale in base alla modalità scelta
    if nonce_mode == "incremental":
        nonce = 0
    elif nonce_mode == "random":
        nonce = random.randint(0, 0xFFFFFFFF)
    elif nonce_mode == "mixed":
        nonce = random.randint(0, 0xFFFFFFFF)
    else:
        raise ValueError("Modalità di mining non valida. Scegli tra 'incremental', 'random' o 'mixed'.")

    while True:
        # Controlla se è necessario aggiornare il timestamp
        if config.TIMESTAMP_UPDATE_INTERVAL > 0 and time.time() - last_timestamp_update >= config.TIMESTAMP_UPDATE_INTERVAL:
            current_timestamp = int(time.time())
            timestamp_bytes = struct.pack("<I", current_timestamp)
            last_timestamp_update = time.time()
            print(f"\nTimestamp aggiornato: {current_timestamp}")
        
        # Costruisci l'header completo con il timestamp aggiornato
        base_header = version + prev_hash + merkle_root + timestamp_bytes + bits
        full_header = base_header + struct.pack("<I", nonce)
        block_hash = double_sha256(full_header)[::-1].hex()

        # Stampa i progressi ogni 100.000 tentativi
        attempts += 1
        if attempts % 100000 == 0:
            print(f"Tentativi: {attempts:,} | nonce: {nonce} | Hash: {block_hash}")

        # Verifica se il nonce trovato è valido
        if int(block_hash, 16) < target:
            print(f"\nBlocco trovato!")
            print(f"Nonce valido: {nonce}")
            print(f"Hash del blocco: {block_hash}")
            print(f"Tentativi totali: {attempts:,}")
            return hexlify(full_header).decode(), nonce

        # Aggiorna il nonce in base alla modalità selezionata
        if nonce_mode == "incremental" or nonce_mode == "mixed":
            nonce = (nonce + 1) % 0x100000000  # Mantieni il nonce nei limiti di 32 bit
        elif nonce_mode == "random":
            nonce = random.randint(0, 0xFFFFFFFF)