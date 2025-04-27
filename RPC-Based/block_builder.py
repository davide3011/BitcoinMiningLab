import struct, hashlib, os
from binascii import unhexlify, hexlify

# Questo modulo contiene le funzioni necessarie per costruire un blocco Bitcoin completo
# Ogni funzione gestisce un aspetto specifico della creazione del blocco, dalla transazione coinbase
# fino alla serializzazione finale del blocco completo

EXTRANONCE1 = "1234567890abcdef"
EXTRANONCE2 = "abcdabcd"

def double_sha256(data):
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

def decode_nbits(nBits: int) -> str:
    """ 
    Decodifica il campo nBits (difficoltà compatta) in un target a 256-bit in formato esadecimale.
    
    Args:
        nBits: Valore intero che rappresenta la difficoltà in formato compatto
        
    Returns:
        str: Il target di difficoltà in formato esadecimale a 64 caratteri (256 bit)
    
    Note:
        In Bitcoin, la difficoltà è codificata nel campo 'bits' dell'header del blocco.
        Il formato è compatto: i primi 8 bit rappresentano l'esponente, i restanti 24 bit 
        rappresentano la mantissa (significand). Questa funzione converte questo formato 
        compatto nel target effettivo che l'hash del blocco deve essere inferiore per 
        essere considerato valido.
    """
    # Estrae l'esponente (primi 8 bit)
    exponent = (nBits >> 24) & 0xff
    # Estrae la mantissa (ultimi 24 bit)
    significand = nBits & 0x007fffff
    # Calcola il target effettivo: mantissa * 2^(8*(esponente-3))
    return f"{(significand << (8 * (exponent - 3))):064x}"

def encode_varint(value):
    """
    Codifica un numero come VarInt (CompactSize Unsigned Integer) secondo il protocollo Bitcoin.
    
    Args:
        value: Il valore intero da codificare come VarInt
        
    Returns:
        str: La rappresentazione esadecimale del VarInt
        
    Raises:
        ValueError: Se il valore supera il limite massimo per VarInt (2^64-1)
    
    Note:
        Il formato VarInt in Bitcoin è utilizzato per codificare numeri di lunghezza variabile:
        - Per valori < 0xfd (253): usa 1 byte per il valore stesso
        - Per valori <= 0xffff: usa 0xfd (1 byte) seguito dal valore su 2 byte
        - Per valori <= 0xffffffff: usa 0xfe (1 byte) seguito dal valore su 4 byte
        - Per valori <= 0xffffffffffffffff: usa 0xff (1 byte) seguito dal valore su 8 byte
        Questo permette di risparmiare spazio quando si codificano numeri piccoli.
    """
    # Definisce le soglie e i prefissi per i diversi formati di VarInt
    thresholds = [(0xfd, ""), (0xffff, "fd"), (0xffffffff, "fe"), (0xffffffffffffffff, "ff")]
    
    # Seleziona il formato appropriato in base al valore
    for threshold, prefix in thresholds:
        if value <= threshold:
            # Calcola il numero di byte necessari e codifica il valore in little-endian
            byte_length = max(1, (threshold.bit_length() + 7) // 8)
            return prefix + value.to_bytes(byte_length, 'little').hex()
            
    # Se il valore è troppo grande, solleva un'eccezione
    raise ValueError("Il valore supera il limite massimo per VarInt (2^64-1)")

def tx_encode_coinbase_height(height):
    """
    Codifica l'altezza del blocco secondo BIP34 per includerla nello scriptSig della transazione coinbase.
    
    Args:
        height: L'altezza del blocco da codificare
        
    Returns:
        str: La rappresentazione esadecimale dell'altezza codificata
        
    Raises:
        ValueError: Se l'altezza del blocco è minore di 1
    
    Note:
        BIP34 richiede che l'altezza del blocco sia inclusa come primo elemento nello scriptSig
        della transazione coinbase. Questo serve per evitare collisioni di hash tra blocchi diversi
        che potrebbero altrimenti avere transazioni coinbase identiche.
        
        Il formato è: [lunghezza in byte dell'altezza] + [altezza in little-endian]
    """
    # Verifica che l'altezza sia valida
    if height < 1:
        raise ValueError("L'altezza del blocco deve essere maggiore di 0")

    # Converte l'altezza in bytes (formato little-endian)
    # Il calcolo (height.bit_length() + 7) // 8 determina il numero minimo di byte necessari
    height_bytes = height.to_bytes((height.bit_length() + 7) // 8, 'little')
    
    # Restituisce: [lunghezza in byte dell'altezza in hex] + [altezza in hex]
    return f"{len(height_bytes):02x}" + height_bytes.hex()

def is_segwit_tx(raw_hex: str) -> bool:
    """
    Ritorna True se la transazione è serializzata in formato SegWit.
    Nei raw tx SegWit, dopo i 4 byte di version compaiono i byte
    marker (0x00) e flag (0x01) => "0001" in esadecimale.
    """
    return len(raw_hex) >= 12 and raw_hex[8:12] == "0001"

def build_coinbase_transaction(template, miner_script_pubkey, coinbase_message=None):
    height  = template["height"]
    reward  = template["coinbasevalue"]
    wc_raw  = template.get("default_witness_commitment")          # può essere script o sola radice
    segwit  = bool(wc_raw)

    tx_version = struct.pack("<I", template["version"]).hex()
    parts = [tx_version]
    if segwit:
        parts.append("0001")                                      # marker+flag

    # ---- input coinbase ------------------------------------------------
    parts += ["01", "00"*32, "ffffffff"]

    script_sig = tx_encode_coinbase_height(height)
    if coinbase_message:
        m = coinbase_message.encode()
        script_sig += "6a" + f"{len(m):02x}" + m.hex()
    # Aggiunge extranonce1 e extranonce2 come richiesto dal protocollo Stratum V1
    script_sig += EXTRANONCE1 + EXTRANONCE2

    if len(script_sig)//2 > 100:
        raise ValueError("scriptSig > 100 byte")

    parts.append(encode_varint(len(script_sig)//2) + script_sig)
    parts.append("ffffffff")                                      # sequence

    # ---- outputs -------------------------------------------------------
    outputs = []

    miner_out  = struct.pack("<Q", reward).hex()
    miner_out += encode_varint(len(miner_script_pubkey)//2) + miner_script_pubkey
    outputs.append(miner_out)

    if segwit:
        # wc_script già pronto se inizia con '6a'
        if wc_raw.startswith("6a"):
            wc_script = wc_raw
        else:                                                     # solo radice: costruisci script
            wc_script = "6a24aa21a9ed" + wc_raw
        outputs.append("00"*8 + encode_varint(len(wc_script)//2) + wc_script)

    parts.append(encode_varint(len(outputs)) + "".join(outputs))

    # ---- witness riservato --------------------------------------------
    if segwit:
        parts += ["01", "20", "00"*32]                            # 1 elemento × 32 byte

    parts.append("00000000")                                      # locktime
    coinbase_hex = "".join(parts)

    # ---------- txid legacy (senza marker/flag + witness) ---------------
    if segwit:
        # 1) elimina marker+flag "0001"
        core = tx_version + coinbase_hex[12:]

        # 2) separa locktime (8 hex alla fine)
        locktime = core[-8:]                # "00000000"
        body     = core[:-8]                # tutto tranne il locktime

        # 3) rimuove la witness-stack (68 hex) presente prima del locktime
        body_wo_wit = body[:-68]            # taglia solo i 34 byte di witness

        # 4) ricompone corpo + locktime
        core = body_wo_wit + locktime
    else:
        core = coinbase_hex

    txid = double_sha256(unhexlify(core))[::-1].hex()
    return coinbase_hex, txid

def calculate_merkle_root(coinbase_txid: str, transactions: list[dict]) -> str:
    # foglie in formato bytes-LE
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

def build_block_header(version, prev_hash, merkle_root, timestamp, bits, nonce):
    """
    Costruisce gli 80 byte dell'header del blocco e li restituisce in formato esadecimale.
    
    Args:
        version: Versione del blocco (intero)
        prev_hash: Hash del blocco precedente (stringa esadecimale)
        merkle_root: Merkle root delle transazioni (stringa esadecimale)
        timestamp: Timestamp Unix del blocco (intero)
        bits: Difficoltà target in formato compatto (stringa esadecimale)
        nonce: Nonce utilizzato per il mining (intero)
        
    Returns:
        str: L'header del blocco serializzato in formato esadecimale (160 caratteri = 80 byte)
    
    Note:
        L'header del blocco è composto da 6 campi per un totale di 80 byte:
        1. Version (4 byte): Versione del protocollo
        2. Previous Block Hash (32 byte): Hash del blocco precedente
        3. Merkle Root (32 byte): Hash che riassume tutte le transazioni
        4. Timestamp (4 byte): Ora di creazione del blocco (secondi da epoch Unix)
        5. Bits (4 byte): Difficoltà target in formato compatto
        6. Nonce (4 byte): Valore modificato durante il mining per trovare un hash valido
        
        L'header è ciò che viene effettivamente sottoposto a mining (calcolo ripetuto dell'hash).
    """
    # Costruisce l'header concatenando tutti i campi in formato binario
    header = (
        struct.pack("<I", version) +                # Version (4 byte, little-endian)
        unhexlify(prev_hash)[::-1] +               # Previous Block Hash (32 byte, invertito)
        unhexlify(merkle_root)[::-1] +             # Merkle Root (32 byte, invertito)
        struct.pack("<I", timestamp) +             # Timestamp (4 byte, little-endian)
        unhexlify(bits)[::-1] +                    # Bits/Target (4 byte, invertito)
        struct.pack("<I", nonce)                   # Nonce (4 byte, little-endian)
    )
    # Converte l'header binario in formato esadecimale
    return hexlify(header).decode()

def serialize_block(header_hex, coinbase_tx, transactions):
    """
    Serializza l'intero blocco nel formato richiesto dal protocollo Bitcoin.
    
    Args:
        header_hex: L'header del blocco in formato esadecimale (80 byte)
        coinbase_tx: La transazione coinbase serializzata in formato esadecimale
        transactions: Lista di transazioni da includere nel blocco
        
    Returns:
        str: Il blocco completo serializzato in formato esadecimale, o None in caso di errore
    
    Note:
        Un blocco Bitcoin completo è composto da:
        1. Block Header (80 byte): Contiene metadati e l'hash target per il mining
        2. Transaction Counter: Numero di transazioni in formato VarInt
        3. Transactions: Tutte le transazioni serializzate, iniziando con la coinbase
        
        La struttura completa è quindi:  
        [header][tx_count][coinbase_tx][tx1][tx2]...[txN]
    """
    print("\n=== Serializzazione del blocco ===")
    print("\nSerializzando il blocco...")

    # Calcola il numero totale di transazioni (coinbase + transazioni normali)
    num_tx = len(transactions) + 1  # +1 per includere la coinbase
    # Codifica il numero di transazioni in formato VarInt esadecimale
    num_tx_hex = encode_varint(num_tx)

    try:
        # Concatena tutte le transazioni normali in formato esadecimale
        transactions_hex = "".join(tx["data"] for tx in transactions)
    except KeyError as e:
        # Gestisce l'errore se una transazione non ha il campo 'data' richiesto
        print(f"Errore: una transazione manca del campo '{e}'")
        return None

    # Assembla il blocco completo: header + contatore tx + coinbase + altre tx
    block_hex = header_hex + num_tx_hex + coinbase_tx + transactions_hex

    # Output informativo
    print("\nBlocco serializzato correttamente!")
    print(f"Numero transazioni = {num_tx}")
    print(f"Blocco HEX:\n{block_hex}")

    # Restituisce il blocco serializzato
    return block_hex