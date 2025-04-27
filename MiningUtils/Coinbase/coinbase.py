# ---------------------------------------------------------------------------
# PARAMETRI DI CONFIGURAZIONE
# ---------------------------------------------------------------------------
RPC_USER        = "..."                # Username per l'autenticazione RPC
RPC_PASSWORD    = "..."                # Password per l'autenticazione RPC
RPC_HOST        = "..."                # Indirizzo IP del nodo
RPC_PORT        = 8332                 # Porta RPC del nodo

WALLET_ADDRESS  = "..."                # Indirizzo di payout

COINBASE_MESSAGE = "/Ciao sono Davide/"

# Extranonce
EXTRANONCE1     = "1234567890abcdef"
EXTRANONCE2     = "abcdabcd"

# ---------------------------------------------------------------------------
# IMPORT
# ---------------------------------------------------------------------------
import os, struct, hashlib, sys
from binascii import unhexlify, hexlify
from typing import Optional, Tuple

try:
    from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
except ImportError:
    sys.exit("[ERRORE] python-bitcoinrpc non installato - pip install python-bitcoinrpc")

# ---------------------------------------------------------------------------
# FUNZIONI DI SUPPORTO – HASHING & CODIFICA
# ---------------------------------------------------------------------------

def double_sha256(data: bytes) -> bytes:
    """Applica SHA-256 due volte (funzione hash cardine in Bitcoin)."""
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def encode_varint(value: int) -> str:
    """Codifica un intero come *CompactSize Unsigned Integer* (BIP‑32)."""
    if value < 0xfd:
        return value.to_bytes(1, "little").hex()
    elif value <= 0xffff:
        return "fd" + value.to_bytes(2, "little").hex()
    elif value <= 0xffffffff:
        return "fe" + value.to_bytes(4, "little").hex()
    elif value <= 0xffffffffffffffff:
        return "ff" + value.to_bytes(8, "little").hex()
    raise ValueError("VarInt oltre 8 byte non supportato")


def tx_encode_coinbase_height(height: int) -> str:
    """Codifica l'altezza del blocco secondo BIP-34."""
    if height < 1:
        raise ValueError("L'altezza del blocco deve essere >= 1")
    hb = height.to_bytes((height.bit_length() + 7) // 8, "little")
    return f"{len(hb):02x}" + hb.hex()

# ---------------------------------------------------------------------------
# SPLIT DELLA COINBASE (STRATUM)
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# COSTRUZIONE COINBASE TRANSACTION
# ---------------------------------------------------------------------------

def build_coinbase_transaction(template: dict, miner_script_pubkey: str,
                               message: str,
                               extranonce1: Optional[str] = None,
                               extranonce2: Optional[str] = None) -> Tuple[str, str]:
    """Restituisce (coinbase_hex, txid_legacy)."""
    height   = template["height"]
    reward   = template["coinbasevalue"]        # in satoshi
    wc_raw   = template.get("default_witness_commitment")
    segwit   = bool(wc_raw)

    version = template["version"]
    version_hex = struct.pack("<I", version).hex()
    parts = [version_hex]                         # versione
    if segwit:
        parts.append("0001")

    # ----- Input coinbase ---------------------------------------------------
    parts += ["01", "00"*32, "ffffffff"]

    script_sig = tx_encode_coinbase_height(height)

    if message:
        m = message.encode()
        script_sig += "6a" + f"{len(m):02x}" + m.hex()

    script_sig += EXTRANONCE1 + EXTRANONCE2

    if len(script_sig)//2 > 100:
        raise ValueError("scriptSig supera 100 byte - riduci il messaggio o gli extranonce")

    parts.append(encode_varint(len(script_sig)//2) + script_sig)
    parts.append("ffffffff")

    # ----- Outputs ---------------------------------------------------------
    outputs = []
    miner_out  = struct.pack("<Q", reward).hex()
    miner_out += encode_varint(len(miner_script_pubkey)//2) + miner_script_pubkey
    outputs.append(miner_out)

    if segwit:
        wc_script = wc_raw if wc_raw.startswith("6a") else "6a24aa21a9ed" + wc_raw
        outputs.append("00"*8 + encode_varint(len(wc_script)//2) + wc_script)

    parts.append(encode_varint(len(outputs)) + "".join(outputs))

    if segwit:
        parts += ["01", "20", "00"*32]

    parts.append("00000000")

    coinbase_hex = "".join(parts)

    # ----- TxID legacy -----------------------------------------------------
    if segwit:
        core = coinbase_hex[:8] + coinbase_hex[12:]  # rimuove marker+flag
        locktime = core[-8:]
        body     = core[:-8]
        body_wo_wit = body[:-68]                    # elimina witness
        core = body_wo_wit + locktime
    else:
        core = coinbase_hex
    txid = double_sha256(unhexlify(core))[::-1].hex()
    return coinbase_hex, txid

# ---------------------------------------------------------------------------
# RPC LAYER
# ---------------------------------------------------------------------------

def rpc_connect() -> AuthServiceProxy:
    return AuthServiceProxy(f"http://{RPC_USER}:{RPC_PASSWORD}@{RPC_HOST}:{RPC_PORT}")

def fetch_block_template(rpc) -> dict:
    return rpc.getblocktemplate({"rules": ["segwit"]})

def get_script_pubkey(rpc, addr: str) -> str:
    return rpc.getaddressinfo(addr)["scriptPubKey"]

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    print("\n=== COSTRUZIONE COINBASE ===")
    try:
        rpc = rpc_connect()
        template = fetch_block_template(rpc)
    except (ConnectionError, JSONRPCException, Exception) as e:
        sys.exit(f"[ERRORE RPC] {e}")

    miner_script = get_script_pubkey(rpc, WALLET_ADDRESS)

    coinbase_hex, txid = build_coinbase_transaction(
        template, miner_script, COINBASE_MESSAGE, EXTRANONCE1, EXTRANONCE2
    )

    # Calcolo dimensioni extranonce in byte
    ex1_bytes = len(EXTRANONCE1) // 2
    ex2_bytes = len(EXTRANONCE2) // 2

    # Output principale -----------------------------------------------------
    print(f"Altezza blocco  : {template['height']}")
    print(f"Reward (sat)    : {template['coinbasevalue']}")
    print(f"SegWit attivo?  : {'Sì' if template.get('default_witness_commitment') else 'No'}")
    print(f"Extranonce1 (byte): {ex1_bytes}")
    print(f"Extranonce2 (byte): {ex2_bytes}")
    print("\n--- COINBASE COMPLETA ---")
    print("\ncoinbase_hex   =", coinbase_hex)
    print("\ncoinbase_txid  =", txid)

    # Split Stratum ---------------------------------------------------------
    try:
        coinb1, ex1, ex2, coinb2 = split_coinbase(coinbase_hex, EXTRANONCE1, EXTRANONCE2)
    except ValueError as e:
        print(f"[Split] Errore: {e}")
        return

    print("\n--- SPLIT STRATUM ---")
    print("\ncoinbase1      =", coinb1)
    print("\nextranonce1    =", ex1)
    print("\nextranonce2    =", ex2)
    print("\ncoinbase2      =", coinb2)

if __name__ == "__main__":
    main()

