import struct, hashlib, os
from binascii import unhexlify, hexlify

# Questo modulo contiene le funzioni necessarie per costruire un blocco Bitcoin completo
# Ogni funzione gestisce un aspetto specifico della creazione del blocco, dalla transazione coinbase
# fino alla serializzazione finale del blocco completo

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

def build_coinbase_transaction(template, miner_script_pubkey, coinbase_message=None):
    """
    Crea la transazione coinbase con un output di ricompensa e, se presente, un OP_RETURN per il witness commitment.
    
    Args:
        template: Dizionario contenente i dati del template del blocco (altezza, valore della ricompensa, ecc.)
        miner_script_pubkey: Script in formato hex che definisce a chi va la ricompensa (indirizzo del miner)
        coinbase_message: Messaggio opzionale da includere nella transazione coinbase
        
    Returns:
        str: La transazione coinbase serializzata in formato esadecimale
        
    Raises:
        ValueError: Se lo scriptSig supera i 100 byte di lunghezza
    
    Note:
        La transazione coinbase è la prima transazione in ogni blocco e ha caratteristiche speciali:
        1. Non ha input reali (usa un input fittizio con hash tutto zero)
        2. Crea nuovi bitcoin come ricompensa per il miner
        3. Può contenere dati arbitrari nello scriptSig
        4. Dal BIP34, deve includere l'altezza del blocco come primo elemento dello scriptSig
        5. Può includere un witness commitment per supportare Segwit (BIP141)
    """
    # Estrae i dati necessari dal template
    height = template["height"]  # Altezza del blocco corrente
    reward = template["coinbasevalue"]  # Valore della ricompensa in satoshi
    witness_commitment_hex = template.get("default_witness_commitment", "")  # Commitment per Segwit (opzionale)

    # PARTE 1: Costruzione dello scriptSig (script di firma dell'input)
    # Codifica l'altezza del blocco in formato BIP34 (obbligatorio dal 2012)
    script_sig_hex = tx_encode_coinbase_height(height)
    
    # Aggiunge il messaggio personalizzato se presente
    if coinbase_message:
        # Aggiunge un byte di separazione (OP_RETURN = 0x6a) tra l'altezza e il messaggio
        message_bytes = coinbase_message.encode('utf-8')  # Converte il messaggio in bytes
        script_sig_hex += "6a"  # OP_RETURN come separatore
        script_sig_hex += f"{len(message_bytes):02x}"  # Pushdata per la lunghezza del messaggio
        script_sig_hex += message_bytes.hex()  # Aggiunge il messaggio in formato hex
    
    # Aggiunge una extranonce casuale (utile per aumentare l'entropia durante il mining)
    script_sig_hex += os.urandom(4).hex()

    # Verifica che lo scriptSig non superi i 100 byte (limite pratico)
    total_length = len(script_sig_hex) // 2  # Converti da esadecimale a byte
    if total_length > 100:
        raise ValueError(f"ScriptSig troppo lungo ({total_length} byte). Max consentito: 100 byte")

    # PARTE 2: Costruzione dell'header della transazione
    tx_version = "01000000"  # Versione 1 della transazione in little-endian
    # La coinbase ha un input speciale con hash tutto zero e indice 0xFFFFFFFF
    prev_hash = "00" * 32  # Hash dell'output precedente (tutto zero per coinbase)
    prev_index = "ffffffff"  # Indice dell'output precedente (0xFFFFFFFF per coinbase)
    sequence = "ffffffff"  # Sequence number (valore standard)
    locktime = "00000000"  # Locktime (0 = nessun lock)
    
    # Calcola la lunghezza dello scriptSig in formato VarInt
    script_len = encode_varint(len(script_sig_hex) // 2)

    # PARTE 3: Costruzione degli output
    # Output 1: Ricompensa per il miner
    satoshis_reward = struct.pack("<Q", reward).hex()  # Valore in satoshi (formato little-endian)
    miner_script_len = encode_varint(len(miner_script_pubkey) // 2)  # Lunghezza dello script in VarInt
    outputs_hex = satoshis_reward + miner_script_len + miner_script_pubkey  # Output completo
    output_count = 1  # Inizialmente abbiamo solo l'output della ricompensa

    # Output 2 (opzionale): Witness Commitment per Segwit
    if witness_commitment_hex and len(witness_commitment_hex) == 64:
        # Crea uno script OP_RETURN con il witness commitment
        # 6a = OP_RETURN, 24 = lunghezza (36 byte), aa21a9ed = marker per witness commitment
        witness_commitment_script = "6a24aa21a9ed" + witness_commitment_hex
        # Aggiunge un output con valore 0 e lo script del witness commitment
        outputs_hex += "00" * 8  # 0 satoshi
        outputs_hex += encode_varint(len(witness_commitment_script) // 2)  # Lunghezza script
        outputs_hex += witness_commitment_script  # Script completo
        output_count += 1  # Incrementa il contatore degli output

    # PARTE 4: Serializzazione della transazione coinbase completa
    return (
        # Formato: version + input_count + inputs + output_count + outputs + locktime
        f"{tx_version}01{prev_hash}{prev_index}{script_len}{script_sig_hex}{sequence}"
        f"{encode_varint(output_count)}{outputs_hex}{locktime}"
    )

def calculate_merkle_root(coinbase_tx, transactions):
    """
    Calcola il Merkle Root del blocco a partire dalla transazione coinbase e dalle altre transazioni.
    
    Args:
        coinbase_tx: La transazione coinbase serializzata in formato esadecimale
        transactions: Lista di transazioni (ogni transazione è un dizionario con 'hash' o 'data')
        
    Returns:
        str: Il Merkle Root in formato esadecimale
    
    Note:
        Il Merkle Root è un hash che riassume tutte le transazioni del blocco in un unico valore.
        Viene calcolato costruendo un albero binario (Merkle Tree) dove:
        1. Le foglie sono gli hash delle transazioni
        2. I nodi interni sono gli hash della concatenazione dei loro figli
        3. La radice dell'albero è il Merkle Root
        
        Se il numero di nodi a un livello è dispari, l'ultimo nodo viene duplicato.
        Questo garantisce che ogni blocco abbia un Merkle Root unico e permette di verificare
        l'appartenenza di una transazione al blocco senza scaricare tutte le transazioni (SPV).
    """
    # Calcola l'hash della transazione coinbase
    # Nota: gli hash in Bitcoin sono memorizzati in little-endian, quindi invertiamo l'ordine dei byte
    coinbase_hash = double_sha256(unhexlify(coinbase_tx))[::-1].hex()
    
    # Crea la lista di tutti gli hash delle transazioni, iniziando con la coinbase
    tx_hashes = [coinbase_hash] + [
        # Se la transazione ha già un hash, lo usa; altrimenti lo calcola dai dati
        tx["hash"] if "hash" in tx else double_sha256(unhexlify(tx["data"]))[::-1].hex()
        for tx in transactions
    ]

    # Converti tutti gli hash in formato bytes e inverti in little-endian per il calcolo
    tx_hashes = [unhexlify(tx)[::-1] for tx in tx_hashes]

    # Calcolo del Merkle Root con algoritmo iterativo
    while len(tx_hashes) > 1:
        # Se il numero di hash è dispari, duplica l'ultimo hash
        if len(tx_hashes) % 2 == 1:
            tx_hashes.append(tx_hashes[-1])  # Padding se dispari
            
        # Calcola il livello successivo dell'albero combinando coppie di hash
        tx_hashes = [double_sha256(tx_hashes[i] + tx_hashes[i + 1]) for i in range(0, len(tx_hashes), 2)]

    # Converti il Merkle Root finale in formato esadecimale (invertendo di nuovo in big-endian)
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