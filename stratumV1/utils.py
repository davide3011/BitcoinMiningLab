# utils.py
# Modulo contenente funzioni di utilità per la gestione di indirizzi Bitcoin e altre operazioni

import struct
import hashlib

def encode_varint(i):
    """
    Codifica un intero come varint secondo lo standard Bitcoin.
    
    Args:
        i (int): L'intero da codificare.
    
    Returns:
        bytes: La rappresentazione varint dell'intero.
    """
    if i < 0xfd:
        return bytes([i])
    elif i <= 0xffff:
        return b'\xfd' + struct.pack("<H", i)
    elif i <= 0xffffffff:
        return b'\xfe' + struct.pack("<I", i)
    else:
        return b'\xff' + struct.pack("<Q", i)

def push_data(data: bytes) -> bytes:
    """
    Costruisce l'operazione PUSH per i dati secondo lo standard Bitcoin.
    
    Args:
        data (bytes): I dati da inserire nell'operazione PUSH.
    
    Returns:
        bytes: L'operazione PUSH completa.
    """
    if len(data) < 0x4c:
        return bytes([len(data)]) + data
    elif len(data) <= 0xff:
        return b'\x4c' + bytes([len(data)]) + data
    elif len(data) <= 0xffff:
        return b'\x4d' + struct.pack("<H", len(data)) + data
    else:
        return b'\x4e' + struct.pack("<I", len(data)) + data

# Funzioni per la decodifica degli indirizzi Bitcoin

def base58_decode(s: str) -> bytes:
    """
    Decodifica un indirizzo Base58.
    
    Args:
        s (str): L'indirizzo in formato Base58.
    
    Returns:
        bytes: L'indirizzo decodificato.
    """
    alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    num = 0
    for char in s:
        num *= 58
        num += alphabet.index(char)
    combined = num.to_bytes((num.bit_length() + 7) // 8, 'big')
    # Aggiunge eventuali byte zero iniziali (gli '1' in Base58)
    n_pad = 0
    for char in s:
        if char == '1':
            n_pad += 1
        else:
            break
    return b'\x00' * n_pad + combined

# Costanti e funzioni per Bech32
CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"

def bech32_hrp_expand(hrp):
    """
    Espande l'HRP (Human-Readable Part) per il calcolo del checksum Bech32.
    
    Args:
        hrp (str): La parte leggibile dell'indirizzo Bech32.
    
    Returns:
        list: L'HRP espanso per il calcolo del checksum.
    """
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]

def bech32_polymod(values):
    """
    Calcola il polinomio di checksum Bech32.
    
    Args:
        values (list): I valori per il calcolo del checksum.
    
    Returns:
        int: Il risultato del calcolo del polinomio.
    """
    generator = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]
    chk = 1
    for v in values:
        top = chk >> 25
        chk = (chk & 0x1ffffff) << 5 ^ v
        for i in range(5):
            chk ^= generator[i] if ((top >> i) & 1) else 0
    return chk

def bech32_verify_checksum(hrp, data):
    """
    Verifica il checksum di un indirizzo Bech32.
    
    Args:
        hrp (str): La parte leggibile dell'indirizzo.
        data (list): I dati dell'indirizzo.
    
    Returns:
        bool: True se il checksum è valido, False altrimenti.
    """
    combined = bech32_hrp_expand(hrp) + data
    return bech32_polymod(combined) == 1

def bech32_decode(bech: str) -> (str, [int]):
    """
    Decodifica un indirizzo Bech32 e restituisce l'HRP e i dati.
    
    Args:
        bech (str): L'indirizzo Bech32 da decodificare.
    
    Returns:
        tuple: Una tupla contenente l'HRP e i dati decodificati.
    """
    if any(ord(c) < 33 or ord(c) > 126 for c in bech):
        return (None, None)
    bech = bech.lower()
    pos = bech.rfind('1')
    if pos < 1 or pos + 7 > len(bech) or len(bech) > 90:
        return (None, None)
    hrp = bech[:pos]
    data = []
    for c in bech[pos+1:]:
        d = CHARSET.find(c)
        if d == -1:
            return (None, None)
        data.append(d)
    if not bech32_verify_checksum(hrp, data):
        return (None, None)
    return (hrp, data[:-6])

def convertbits(data, frombits, tobits, pad=True):
    """
    Conversione generale di base in potenza di 2.
    
    Args:
        data (list): I dati da convertire.
        frombits (int): Il numero di bit della base di partenza.
        tobits (int): Il numero di bit della base di arrivo.
        pad (bool): Se True, aggiunge padding se necessario.
    
    Returns:
        list: I dati convertiti.
    """
    acc = 0
    bits = 0
    ret = []
    maxv = (1 << tobits) - 1
    max_acc = (1 << (frombits + tobits - 1)) - 1
    for value in data:
        if value < 0 or (value >> frombits):
            return None
        acc = ((acc << frombits) | value) & max_acc
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad:
        if bits:
            ret.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        return None
    return ret

def address_to_scriptPubKey(address: str) -> str:
    """
    Converte un indirizzo Bitcoin (legacy o bech32) nello scriptPubKey.
    
    Args:
        address (str): L'indirizzo Bitcoin da convertire.
    
    Returns:
        str: Lo scriptPubKey in formato esadecimale.
    
    Raises:
        ValueError: Se il formato dell'indirizzo non è riconosciuto o supportato.
    """
    if address[0] in "13":
        # Legacy P2PKH
        decoded = base58_decode(address)
        return "76a914" + decoded[1:21].hex() + "88ac"
    elif address.lower().startswith(("bc1", "tb1", "bcrt1")):
        # Bech32: decodifica e costruisce scriptPubKey P2WPKH o P2WSH
        hrp, data = bech32_decode(address)
        if hrp is None or data is None or len(data) < 1:
            raise ValueError("Indirizzo bech32 non valido")
        witver = data[0]
        witprog = bytes(convertbits(data[1:], 5, 8, False))
        if witver != 0 or len(witprog) not in (20, 32):
            raise ValueError("Indirizzo bech32 non supportato")
        # OP_0 + <push del witness program>
        push_opcode = bytes([len(witprog)]) if len(witprog) < 76 else b'\x4c' + bytes([len(witprog)])
        return "00" + push_opcode.hex() + witprog.hex()
    else:
        raise ValueError("Formato indirizzo non riconosciuto")