import logging
import struct
from binascii import unhexlify, hexlify
from utils import double_sha256, encode_varint

log = logging.getLogger(__name__)

def tx_encode_coinbase_height(height: int) -> str:
    """Codifica l'altezza del blocco secondo BIP34 per la coinbase."""
    if height < 0:
        raise ValueError("L'altezza del blocco deve essere maggiore o uguale a 0.")
    if height == 0:
        return "00"
    result = bytearray()
    v = height
    while v:
        result.append(v & 0xff)
        v >>= 8
    if result and (result[-1] & 0x80):
        result.append(0x00)
    return f"{len(result):02x}" + result.hex()

def is_segwit_tx(raw_hex: str) -> bool:
    """Ritorna True se la transazione è in formato SegWit."""
    return len(raw_hex) >= 12 and raw_hex[8:12] == "0001"

def build_coinbase_transaction(template, miner_script_pubkey, extranonce1, extranonce2, coinbase_message=None):
    """Costruisce una transazione coinbase per il mining."""
    height  = template["height"]
    reward  = template["coinbasevalue"]
    wc_raw  = template.get("default_witness_commitment")          # può essere script o sola radice
    segwit  = bool(wc_raw)

    tx_version = "01000000"
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

    txid = double_sha256(unhexlify(core))[::-1].hex()            # converte in big-endian
    hash = double_sha256(unhexlify(coinbase_hex))[::-1].hex()    # converte in big-endian

    return coinbase_hex, txid, hash

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

def build_block_header(version_hex, prev_hash_le, merkle_root_le, timestamp_hex, bits_hex, nonce_hex):
    """
    Costruisce l'header del blocco (80 byte) in formato esadecimale.
    Tutti i parametri sono già in formato esadecimale little-endian.
    """
    # Concatena tutti i campi già in formato esadecimale little-endian
    header_hex = (
        version_hex +      # Version (4 byte, little-endian)
        prev_hash_le +     # Previous Block Hash (32 byte, little-endian)
        merkle_root_le +   # Merkle Root (32 byte, little-endian)
        timestamp_hex +    # Timestamp (4 byte, little-endian)
        bits_hex +         # Bits/Target (4 byte, little-endian)
        nonce_hex          # Nonce (4 byte, little-endian)
    )
    return header_hex

def serialize_block(header_hex, coinbase_tx, transactions):
    """Serializza il blocco completo nel formato Bitcoin."""
    log.debug("Serializzazione del blocco avviata")
    
    num_tx = len(transactions) + 1
    num_tx_hex = encode_varint(num_tx)

    try:
        transactions_hex = "".join(tx["data"] for tx in transactions)
    except KeyError:
        log.exception("Una transazione manca del campo 'data'")
        return None

    block_hex = header_hex + num_tx_hex + coinbase_tx + transactions_hex
    log.info("Blocco serializzato correttamente - %d transazioni totali", num_tx)
    log.debug("Blocco HEX: %s", block_hex)
    
    return block_hex
