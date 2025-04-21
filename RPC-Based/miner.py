import struct, random, time, hashlib
from binascii import hexlify, unhexlify
import config

"""
Modulo di mining per il processo di proof-of-work di Bitcoin.
Implementa le funzioni necessarie per eseguire il mining di blocchi Bitcoin,
includendo l'algoritmo di hashing SHA-256 e la ricerca del nonce valido.
"""

# ---------------------------------------------------------------------------
# utility
# ---------------------------------------------------------------------------

def double_sha256(data: bytes) -> bytes:
    """
    Esegue il doppio SHA-256 su un dato, una funzione di hash fondamentale in Bitcoin.
    
    Args:
        data: I dati in formato bytes su cui calcolare l'hash
        
    Returns:
        bytes: Il risultato del doppio hash SHA-256 (prima si applica SHA-256, poi si applica 
               nuovamente SHA-256 sul risultato)
    
    Note:
        Questa funzione è utilizzata in molti contesti in Bitcoin, come il calcolo 
        dell'hash del blocco, l'hash delle transazioni e il calcolo del merkle root.
    """
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()

def _midstate(prefix: bytes) -> "hashlib._Hash":
    """
    Restituisce un contesto SHA-256 inizializzato con i primi 76 byte dell'header del blocco.
    
    Args:
        prefix: I primi 76 byte dell'header del blocco (tutti i campi tranne il nonce)
        
    Returns:
        hashlib._Hash: Un oggetto hash SHA-256 inizializzato con il prefisso
        
    Note:
        Questa funzione di ottimizzazione permette di calcolare l'hash solo una volta per i byte
        che non cambiano durante il mining, migliorando significativamente le prestazioni.
    """
    h = hashlib.sha256()
    h.update(prefix)
    return h

# ---------------------------------------------------------------------------
# mining
# ---------------------------------------------------------------------------

def mine_block(header_hex: str, target_hex: str, nonce_mode: str = "incremental"):
    """
    Esegue il processo di mining (proof-of-work) cercando un nonce valido per l'header del blocco.
    
    Args:
        header_hex: L'header del blocco in formato esadecimale (senza nonce)
        target_hex: Il target di difficoltà in formato esadecimale
        nonce_mode: La modalità di ricerca del nonce ("incremental", "random" o "mixed")
        
    Returns:
        tuple: Una tupla contenente (header_hex_completo, nonce_valido, hashrate_medio)
            - header_hex_completo: L'header completo del blocco con il nonce valido
            - nonce_valido: Il nonce che ha prodotto un hash valido
            - hashrate_medio: La velocità media di hash durante il mining (hash/secondo)
    
    Note:
        Il processo di mining consiste nel trovare un nonce tale che l'hash dell'header
        del blocco sia inferiore al target di difficoltà. Questo è il cuore del meccanismo
        di proof-of-work di Bitcoin. La funzione supporta diverse strategie di ricerca del nonce:
        - "incremental": Incrementa il nonce da 0 fino a trovare una soluzione
        - "random": Genera nonce casuali
        - "mixed": Combina approcci incrementali e casuali
    """

    print(f"\n=== Inizio del Mining | Modalità: {nonce_mode} ===\n")

    # ---- decodifica header (80 B) ----
    # Converte le parti dell'header da esadecimale a bytes
    version   = unhexlify(header_hex[0:8])      # Versione del blocco (4 byte)
    prev_hash = unhexlify(header_hex[8:72])     # Hash del blocco precedente (32 byte)
    merkle    = unhexlify(header_hex[72:136])   # Merkle root delle transazioni (32 byte)
    ts_bytes  = unhexlify(header_hex[136:144])  # Timestamp (4 byte)
    bits      = unhexlify(header_hex[144:152])  # Target di difficoltà in formato compatto (4 byte)

    # Combina i primi 76 byte dell'header (tutti i campi tranne il nonce)
    base76 = version + prev_hash + merkle + ts_bytes + bits
    # Calcola lo stato intermedio dell'hash SHA-256 per ottimizzare il mining
    mid    = _midstate(base76)

    # Crea un header mutabile con spazio per il nonce (byte 76-79)
    header = bytearray(base76 + b"\x00\x00\x00\x00")
    # Crea una vista di memoria per accedere direttamente ai byte del nonce
    nonce_view = memoryview(header)[76:]

    # ---- target big‑endian (per confronto bytes) ----
    # Converte il target da esadecimale a bytes in formato big-endian per confronto diretto
    target_be = int(target_hex, 16).to_bytes(32, "big")

    # ---- nonce iniziale ----
    # Inizializza il nonce in base alla modalità di mining selezionata
    if nonce_mode == "incremental":
        nonce = 0                                # Inizia da 0 e incrementa
    elif nonce_mode in ("random", "mixed"):
        nonce = random.randint(0, 0xFFFFFFFF)    # Inizia da un valore casuale
    else:
        raise ValueError("Modalità di mining non valida. Scegli tra 'incremental', 'random' o 'mixed'.")

    # Inizializza contatori e timer per statistiche e aggiornamenti
    attempts, start_t = 0, time.time()           # Contatore tentativi e tempo iniziale
    last_rate_t, last_rate_n = start_t, 0        # Timer per calcolo hashrate
    last_tsu = start_t                           # Timer per aggiornamento timestamp

    # Costanti per ottimizzazione e logging
    BATCH   = 8           # Numero di nonce da provare per iterazione
    LOG_INT = 1_000_000   # Intervallo di tentativi tra un log e l'altro

    # Crea un contesto SHA-256 vuoto da riutilizzare (ottimizzazione)
    sha2ctx = hashlib.sha256()  # contesto vuoto da copiare (leggermente più veloce)

    while True:
        # ---- aggiornamento timestamp ----
        # Aggiorna periodicamente il timestamp per mantenere il blocco "fresco"
        if config.TIMESTAMP_UPDATE_INTERVAL and (time.time() - last_tsu) >= config.TIMESTAMP_UPDATE_INTERVAL:
            # Crea un nuovo timestamp (tempo corrente)
            ts_bytes = struct.pack("<I", int(time.time()))
            # Aggiorna il timestamp nell'header (byte 68-71)
            header[68:72] = ts_bytes
            # Ricostruisce il prefisso dell'header con il nuovo timestamp
            base76 = version + prev_hash + merkle + ts_bytes + bits
            # Ricalcola lo stato intermedio dell'hash
            mid = _midstate(base76)
            # Aggiorna l'header completo
            header[:76] = base76
            # Aggiorna il timer dell'ultimo aggiornamento timestamp
            last_tsu = time.time()
            # Mostra messaggio di aggiornamento (con controllo cursore ANSI)
            print(f"\033[1A\033[K\rTimestamp aggiornato: {int.from_bytes(ts_bytes, 'little')}")

        # ---- batch di BATCH nonce ----
        # Prova un batch di nonce in sequenza per ottimizzare le prestazioni
        for i in range(BATCH):
            # Calcola il nonce corrente (con overflow a 32 bit)
            n = (nonce + i) & 0xFFFFFFFF
            # Inserisce il nonce nell'header (byte 76-79)
            struct.pack_into("<I", header, 76, n)
            # Calcola il primo hash SHA-256 partendo dallo stato intermedio
            h1 = mid.copy(); h1.update(nonce_view)
            d1 = h1.digest()
            # Calcola il secondo hash SHA-256 (double SHA-256)
            h2 = sha2ctx.copy(); h2.update(d1)
            digest = h2.digest()

            # Confronta l'hash ottenuto con il target (invertendo l'hash in little-endian)
            if digest[::-1] < target_be:
                # Calcola statistiche finali
                total = time.time() - start_t
                hashrate = (attempts + i + 1) / total if total else 0
                # Mostra informazioni sul blocco trovato
                print("\033[K\rBlocco trovato!")
                print(f"\033[K\rNonce: {n}")
                print(f"\033[K\rHash: {digest[::-1].hex()}")
                print(f"\033[K\rTentativi: {attempts + i + 1:,}")
                print(f"\033[K\rTempo: {total:.2f}s | Hashrate medio: {hashrate/1000:.2f} kH/s")
                # Ritorna l'header completo, il nonce valido e l'hashrate medio
                return hexlify(bytes(header)).decode(), n, hashrate

        # Aggiorna il contatore dei tentativi e il nonce base per il prossimo batch
        attempts += BATCH
        nonce = (nonce + BATCH) & 0xFFFFFFFF  # Incrementa con overflow a 32 bit

        # ---- log periodico ----
        # Mostra periodicamente lo stato del mining e le statistiche
        if attempts % LOG_INT == 0:
            # Calcola l'hashrate corrente
            now = time.time()
            rate = (attempts - last_rate_n) / (now - last_rate_t)
            last_rate_t, last_rate_n = now, attempts
            # Calcola l'hash corrente per debug
            struct.pack_into("<I", header, 76, nonce)
            tmp = mid.copy(); tmp.update(nonce_view)
            dbg_hash = double_sha256(tmp.digest())
            # Mostra lo stato del mining (con controllo cursore ANSI)
            print("\033[K\r----- Stato Mining -----")
            print(f"\033[K\rTentativi: {attempts:,}")
            print(f"\033[K\rNonce: {nonce}")
            print(f"\033[K\rHash: {dbg_hash[::-1].hex()}")
            print(f"\033[K\rHashrate: {rate/1000:,.2f} kH/s")
            print("\033[5F", end="")  # Sposta il cursore 5 righe in alto per sovrascrivere
