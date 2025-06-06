import struct, logging
from binascii import unhexlify, hexlify
from utils import double_sha256, encode_varint

log = logging.getLogger(__name__)

def tx_encode_coinbase_height(height: int) -> str:
    """
    Codifica l'altezza del blocco secondo BIP34 (formato CScriptNum) per includerla
    nello scriptSig della transazione coinbase.
    Args:
        height: L'altezza del blocco da codificare.
    Returns:
        str: La rappresentazione esadecimale dell'altezza codificata.
    Raises:
        ValueError: Se l'altezza del blocco è minore di 0.
    Note:
        BIP34 richiede che l'altezza del blocco sia inclusa come primo elemento
        nello scriptSig della transazione coinbase.
        Il formato è: [lunghezza in byte dell'altezza] + [altezza in CScriptNum].
        CScriptNum per numeri positivi:
        - Codifica little-endian.
        - Numero minimo di byte.
        - Se il bit più significativo dell'ultimo byte è 1 (cioè >= 0x80),
          e il numero non È zero, aggiungere un byte 0x00 alla fine
          per indicare che È positivo.
        Per altezza 0, il CScriptNum È 0x00 (OP_0), quindi i dati sono b'' e la lunghezza è 0.
    """
    if height < 0:
        raise ValueError("L'altezza del blocco deve essere maggiore o uguale a 0.")
    if height == 0:
        return "00"
    result = bytearray()
    v = height
    while v:
        result.append(v & 0xff)
        v >>= 8
    # Se il bit più significativo dell'ultimo byte è 1, aggiungi un byte 0x00
    if result and (result[-1] & 0x80):
        result.append(0x00)
    return f"{len(result):02x}" + result.hex()

def is_segwit_tx(raw_hex: str) -> bool:
    """
    Ritorna True se la transazione è serializzata in formato SegWit.
    Nei raw tx SegWit, dopo i 4 byte di version compaiono i byte
    marker (0x00) e flag (0x01) => "0001" in esadecimale.
    """
    return len(raw_hex) >= 12 and raw_hex[8:12] == "0001"

def build_coinbase_transaction(template, miner_script_pubkey, extranonce1, extranonce2, coinbase_message=None):
    """Costruisce una transazione coinbase per il mining."""
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
    script_sig += extranonce1 + extranonce2

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
    """Calcola la radice dell'albero di Merkle per una lista di ID di transazioni."""
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
    # Messaggio di alto livello → INFO
    log.info("Serializzazione del blocco avviata")

    # Calcola il numero totale di transazioni (coinbase + transazioni normali)
    num_tx = len(transactions) + 1  # +1 per includere la coinbase
    # Codifica il numero di transazioni in formato VarInt esadecimale
    num_tx_hex = encode_varint(num_tx)

    try:
        # Concatena tutte le transazioni normali in formato esadecimale
        transactions_hex = "".join(tx["data"] for tx in transactions)
    except KeyError as e:
        # Errore operativo → ERROR (stack-trace incluso)
        log.exception("Una transazione manca del campo 'data'")
        return None

    # Assembla il blocco completo: header + contatore tx + coinbase + altre tx
    block_hex = header_hex + num_tx_hex + coinbase_tx + transactions_hex

    # Conferma di successo → INFO
    log.info("Blocco serializzato correttamente - %d transazioni totali", num_tx)

    # Dettaglio verboso (potenzialmente migliaia di caratteri) → DEBUG
    log.debug("Blocco HEX: %s", block_hex)

    # Restituisce il blocco serializzato
    return block_hex
