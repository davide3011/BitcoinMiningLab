import struct, random
from binascii import hexlify, unhexlify
from block_builder import double_sha256

def mine_block(header_hex, target_hex, nonce_mode="incremental"):
    """
    Esegue il mining cercando un nonce valido rispetto al target.
    
    - `incremental`: parte da 0 e incrementa di 1 fino al massimo valore possibile.
    - `random`: genera un nonce casuale a ogni iterazione.
    - `mixed`: genera un primo nonce casuale, poi incrementa di 1.
    """
    print(f"\n=== Inizio del Mining | Modalità: {nonce_mode} ===")

    target = int(target_hex, 16)
    base_header = unhexlify(header_hex[:152])  # Parte fissa dell'header
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
        # Aggiorna i 4 byte finali del nonce
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