import struct, random, time, hashlib
from binascii import hexlify, unhexlify
import config

# Questo modulo contiene le funzioni necessarie per il processo di mining Bitcoin
# Si occupa di trovare un nonce valido che produca un hash del blocco inferiore al target

def double_sha256(data: bytes) -> bytes:
    """
    Esegue il doppio SHA-256 su un dato, una funzione di hash fondamentale in Bitcoin.
    
    Args:
        data: I dati in formato bytes su cui calcolare l'hash
        
    Returns:
        bytes: Il risultato del doppio hash SHA-256
        
    Note:
        Questa funzione è il cuore dell'algoritmo di mining: l'hash del blocco
        deve essere inferiore al target di difficoltà per essere considerato valido.
    """
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()

def mine_block(header_hex, target_hex, nonce_mode="incremental"):
    """
    Esegue il processo di mining su un blocco Bitcoin cercando un nonce valido.
    
    Args:
        header_hex: L'header del blocco in formato esadecimale (80 byte senza nonce finale)
        target_hex: Il target di difficoltà in formato esadecimale
        nonce_mode: La modalità di ricerca del nonce ("incremental", "random" o "mixed")
        
    Returns:
        tuple: (header_completo, nonce_valido, hashrate) se il mining ha successo
        
    Raises:
        ValueError: Se la modalità di mining specificata non è valida
        
    Note:
        Il mining è il processo di ricerca di un nonce che, aggiunto all'header del blocco,
        produce un hash inferiore al target di difficoltà. Questo processo richiede
        molti tentativi (proof-of-work) e garantisce la sicurezza della blockchain.
    """
    # Mostra l'inizio del processo di mining con la modalità selezionata
    print(f"\n=== Inizio del Mining | Modalità: {nonce_mode} ===", end="\n\n")

    # Converte il target da esadecimale a intero per confronti più veloci
    target = int(target_hex, 16)
    
    # Estrae i componenti dell'header del blocco dal formato esadecimale
    version = unhexlify(header_hex[:8])              # Versione (4 byte)
    prev_hash = unhexlify(header_hex[8:72])          # Hash del blocco precedente (32 byte)
    merkle_root = unhexlify(header_hex[72:136])      # Merkle root (32 byte)
    timestamp_bytes = unhexlify(header_hex[136:144]) # Timestamp (4 byte)
    bits = unhexlify(header_hex[144:152])            # Bits/Target (4 byte)

    # Estrae il timestamp corrente dall'header (formato little-endian)
    current_timestamp = struct.unpack("<I", timestamp_bytes)[0]
    
    # Inizializza i contatori di tempo
    last_timestamp_update = time.time()  # Tempo dell'ultimo aggiornamento del timestamp
    start_time = time.time()             # Tempo di inizio del mining

    # Inizializza i contatori per le statistiche
    attempts = 0                         # Numero totale di tentativi
    last_hashrate_update = start_time    # Tempo dell'ultimo calcolo dell'hashrate
    last_hashrate_attempts = 0           # Tentativi all'ultimo calcolo dell'hashrate

    # Inizializza il nonce in base alla modalità selezionata
    if nonce_mode == "incremental":
        nonce = 0                                # Parte da 0 e incrementa sequenzialmente
    elif nonce_mode == "random" or nonce_mode == "mixed":
        nonce = random.randint(0, 0xFFFFFFFF)    # Sceglie un valore casuale tra 0 e 2^32-1
    else:
        # Modalità non valida
        raise ValueError("Modalità di mining non valida. Scegli tra 'incremental', 'random' o 'mixed'.")

    # Prepara la parte fissa dell'header (tutto tranne il nonce)
    base_header = version + prev_hash + merkle_root + timestamp_bytes + bits

    # Loop principale di mining - continua finché non trova un hash valido
    while True:
        # Aggiorna il timestamp se è trascorso l'intervallo configurato
        # Questo è importante per mantenere il blocco "fresco" durante mining prolungati
        if config.TIMESTAMP_UPDATE_INTERVAL > 0 and time.time() - last_timestamp_update >= config.TIMESTAMP_UPDATE_INTERVAL:
            current_timestamp = int(time.time())  # Nuovo timestamp corrente
            timestamp_bytes = struct.pack("<I", current_timestamp)  # Converte in bytes (little-endian)
            last_timestamp_update = time.time()  # Aggiorna il tempo dell'ultimo aggiornamento
            # Ricostruisce l'header base con il nuovo timestamp
            base_header = version + prev_hash + merkle_root + timestamp_bytes + bits
            # Se non è il primo aggiornamento, torna indietro di una riga prima di stampare
            if last_timestamp_update > start_time +1:
                print("\033[1A", end="")  # Torna indietro di una riga 
            print(f"\033[K\rTimestamp aggiornato: {current_timestamp}", end="\r\n")

        # Crea l'header completo aggiungendo il nonce corrente
        full_header = base_header + struct.pack("<I", nonce)  # Aggiunge il nonce (4 byte, little-endian)
        # Calcola l'hash dell'header completo (questo è il cuore del mining)
        block_hash = double_sha256(full_header)

        # Incrementa il contatore dei tentativi
        attempts += 1
        
        # Ogni 250.000 tentativi, aggiorna le statistiche e mostra lo stato
        if attempts % 250000 == 0:
            current_time = time.time()
            elapsed = current_time - last_hashrate_update  # Tempo trascorso dall'ultimo aggiornamento
            
            # Calcola l'hashrate corrente (hash al secondo)
            # Formula: (tentativi_attuali - tentativi_precedenti) / tempo_trascorso
            current_hashrate = (attempts - last_hashrate_attempts) / elapsed
            # Aggiorna i riferimenti per il calcolo dell'hashrate
            last_hashrate_update = current_time
            last_hashrate_attempts = attempts

            # Visualizza lo stato del mining con sequenze ANSI per aggiornare la console
            # \033[K cancella la riga corrente, \r riporta il cursore all'inizio della riga
            print("\033[K\r----- Stato Mining -----", end="\r\n")
            print(f"\033[K\rTentativi: {attempts:,}", end="\r\n")  # Formatta con separatori di migliaia
            print(f"\033[K\rNonce: {nonce}", end="\r\n")
            # Nota: l'hash viene invertito ([::-1]) perché Bitcoin visualizza gli hash in big-endian
            print(f"\033[K\rHash: {block_hash[::-1].hex()}", end="\r\n")
            print(f"\033[K\rHashrate: {current_hashrate/1000:,.2f} kH/s", end="\r\n")  # Hashrate [kH/s]
            print("\033[K\r------------------------", end="\r\n")
            print("\033[6F", end="")  # Sposta il cursore 6 righe in su per sovrascrivere le stesse righe

        # Verifica se l'hash trovato è valido (inferiore al target)
        # Gli hash in Bitcoin sono interpretati come numeri little-endian
        if int.from_bytes(block_hash, 'little') < target:
            # Calcola il tempo totale di mining e l'hashrate medio
            mining_time = time.time() - start_time
            hashrate = attempts / mining_time if mining_time > 0 else 0

            # Pulisce le righe di stato precedenti
            print("\033[K\r\n" * 6, end="")
            # Mostra i risultati del mining riuscito
            print(f"\033[K\rBlocco trovato!", end="\r\n")
            print(f"\033[K\rNonce valido: {nonce}", end="\r\n")
            print(f"\033[K\rHash del blocco: {block_hash[::-1].hex()}", end="\r\n")
            print(f"\033[K\rTentativi totali: {attempts:,}", end="\r\n")
            print(f"\033[K\rTempo impiegato: {mining_time:.2f} secondi", end="\r\n")
            print(f"\033[K\rHashrate: {hashrate/1000:.2f} kH/s")

            # Restituisce l'header completo, il nonce trovato e l'hashrate medio
            return hexlify(full_header).decode(), nonce, hashrate

        # Se l'hash non è valido, prova con un nuovo nonce in base alla modalità selezionata
        if nonce_mode == "incremental" or nonce_mode == "mixed":
            # Incrementa il nonce e gestisce l'overflow (torna a 0 dopo 2^32-1)
            nonce = (nonce + 1) % 0x100000000  # 0x100000000 = 2^32
        elif nonce_mode == "random":
            # Sceglie un nuovo nonce casuale
            nonce = random.randint(0, 0xFFFFFFFF)
