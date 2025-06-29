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

def build_coinbase_transaction(template,
                               miner_script_pubkey: str,
                               extranonce1: str,
                               extranonce2: str,
                               ntime: int,
                               bits: str,
                               coinbase_message: str | None = None):
    """
    Costruisce la transazione coinbase in modo compatibile con il
    comportamento del miner Stratum “lucky-miner”.
    
    Ritorna:
        coinbase_hex (str) - transazione completa in hex
        txid         (str) - ID legacy (big-endian)
        hash         (str) - ID segwit (se presente), altrimenti idem txid
    """
    height  = template["height"]                       # altezza blocco
    reward  = template["coinbasevalue"]                # ricompensa in sat
    wc_raw  = template.get("default_witness_commitment")
    segwit  = bool(wc_raw)

    # ---------- intestazione transazione -------------------------------
    tx_version = "01000000"
    parts: list[str] = [tx_version]
    if segwit:
        parts.append("0001")                           # marker + flag

    # ---------- input coinbase -----------------------------------------
    parts += ["01", "00"*32, "ffffffff"]               # 1 input fittizio

    # -- scriptSig -------------------------------------------------------
    #
    # <push(height)> OP_0
    # PUSH4(nTimeLE) PUSH4(bitsLE)
    # PUSH(len(ex1+ex2)) extranonce1 extranonce2
    # PUSH10("ckpool")   PUSHlen(msg)
    #

    height_push = tx_encode_coinbase_height(height)
    op_zero     = "00"

    ntime_le = struct.pack("<I", ntime).hex()
    bits_le  = struct.pack("<I", int(bits, 16)).hex()
    push_ntime = "04" + ntime_le                       # 5 byte
    push_bits  = "04" + bits_le                        # 5 byte

    ex_len   = (len(extranonce1) + len(extranonce2)) // 2
    push_ex  = f"{ex_len:02x}"

    pool_tag_hex  = "636b706f6f6c"                     # 'ckpool'
    push_pool_tag = "0a" + pool_tag_hex                # PUSH10

    msg_hex = ""
    if coinbase_message:
        m = coinbase_message.encode()
        msg_hex = f"{len(m):02x}" + m.hex()

    script_sig = (
        height_push + op_zero +
        push_ntime + push_bits +
        push_ex + extranonce1 + extranonce2 +
        push_pool_tag + msg_hex
    )

    if len(script_sig) // 2 > 100:
        raise ValueError("scriptSig > 100 byte")

    parts.append(encode_varint(len(script_sig)//2) + script_sig)
    parts.append("ffffffff")                           # sequence

    # ---------- outputs -------------------------------------------------
    outputs: list[str] = []

    miner_out  = struct.pack("<Q", reward).hex()
    miner_out += encode_varint(len(miner_script_pubkey)//2) + miner_script_pubkey
    outputs.append(miner_out)

    if segwit:
        # se wc_raw è già uno script completo che inizia con OP_RETURN
        wc_script = wc_raw if wc_raw.startswith("6a") else "6a24aa21a9ed" + wc_raw
        outputs.append("00"*8 + encode_varint(len(wc_script)//2) + wc_script)

    parts.append(encode_varint(len(outputs)) + "".join(outputs))

    # ---------- witness “riservato” ------------------------------------
    if segwit:
        parts += ["01", "20", "00"*32]                 # stack fittizia

    parts.append("00000000")                           # lock-time
    coinbase_hex = "".join(parts)

    # ---------- calcolo TXID legacy ------------------------------------
    if segwit:
        # 1) rimuovi marker+flag
        core = tx_version + coinbase_hex[12:]
        # 2) separa lock-time
        lock = core[-8:]
        body = core[:-8]
        # 3) togli witness (34 byte → 68 hex)
        body_no_wit = body[:-68]
        core = body_no_wit + lock
    else:
        core = coinbase_hex

    txid  = double_sha256(unhexlify(core))[::-1].hex()       # big-endian
    hash = double_sha256(unhexlify(coinbase_hex))[::-1].hex() # big-endian

    return coinbase_hex, txid, hash
