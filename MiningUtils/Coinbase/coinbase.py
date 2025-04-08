from bitcoinrpc.authproxy import AuthServiceProxy
import requests
import json
import struct
import hashlib

#################################################
# Configurazioni
#################################################

RPC_USER = '...'
RPC_PASSWORD = '...'
RPC_HOST = '...'
RPC_PORT = '8332'

COINBASE_ADDRESS = '...'
COINBASE_MESSAGE = '/Ciao sono davide3011/'

# Extranonce values for coinbase construction
EXTRANONCE1 = '12345678'  # 8 bytes
EXTRANONCE2 = 'abcd'      # 4 bytes

EXTRANONCE_PLACEHOLDER = b"{{extranonce}}"

#################################################
# Funzioni RPC Bitcoin
#################################################

def connect_rpc():
    """
    Crea una connessione RPC al nodo Bitcoin utilizzando i parametri di configurazione.
    Returns:
        AuthServiceProxy: Un'istanza del proxy per le chiamate RPC.
    """
    connection_url = f"http://{RPC_USER}:{RPC_PASSWORD}@{RPC_HOST}:{RPC_PORT}"
    return AuthServiceProxy(connection_url)

def rpc_call(method, params=None):
    """
    Esegue una chiamata RPC al nodo Bitcoin.
    Args:
        method (str): Il metodo RPC da chiamare.
        params (list, optional): I parametri da passare al metodo. Default è None.
    Returns:
        Il risultato della chiamata RPC.
    """
    if params is None:
        params = []
    connection_url = f"http://{RPC_USER}:{RPC_PASSWORD}@{RPC_HOST}:{RPC_PORT}"
    proxy = AuthServiceProxy(connection_url)
    return proxy.__getattr__(method)(*params)

def get_block_template(rules=None):
    """
    Ottiene un template per un nuovo blocco dal nodo Bitcoin.
    Args:
        rules (list, optional): Le regole da applicare per la generazione del template.
                               Default è ["segwit"].
    Returns:
        dict: Il template del blocco.
    """
    if rules is None:
        rules = ["segwit"]
    
    rpc = connect_rpc()
    return rpc.getblocktemplate({"rules": rules})

#################################################
# Funzioni di utilità
#################################################

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
    return bech32_polymod(bech32_hrp_expand(hrp) + data) == 1

def bech32_decode(bech):
    """
    Decodifica un indirizzo Bech32.
    Args:
        bech (str): L'indirizzo in formato Bech32.
    Returns:
        tuple: (hrp, data) se la decodifica ha successo, (None, None) altrimenti.
    """
    CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
    if ((any(ord(x) < 33 or ord(x) > 126 for x in bech)) or
            (bech.lower() != bech and bech.upper() != bech)):
        return (None, None)
    bech = bech.lower()
    pos = bech.rfind('1')
    if pos < 1 or pos + 7 > len(bech) or len(bech) > 90:
        return (None, None)
    hrp = bech[:pos]
    data = [CHARSET.find(x) for x in bech[pos+1:]]
    if any(x == -1 for x in data):
        return (None, None)
    if not bech32_verify_checksum(hrp, data):
        return (None, None)
    return (hrp, data[:-6])

def convertbits(data, frombits, tobits, pad=True):
    """
    Converte una sequenza di bit da una dimensione all'altra.
    Args:
        data (list): I dati da convertire.
        frombits (int): La dimensione originale dei bit.
        tobits (int): La dimensione finale dei bit.
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

def address_to_scriptPubKey(address):
    """
    Converte un indirizzo Bitcoin in scriptPubKey.
    Args:
        address (str): L'indirizzo Bitcoin.
    Returns:
        str: Lo scriptPubKey in formato esadecimale.
    """
    # Verifica se è un indirizzo Bech32 (Segwit)
    if address.startswith('bc1') or address.startswith('tb1'):
        hrp, data = bech32_decode(address)
        if hrp is None:
            raise ValueError("Indirizzo Bech32 non valido")
        
        # Estrai il witness program
        witness_version = data[0]
        witness_program = convertbits(data[1:], 5, 8, False)
        
        if witness_version == 0 and len(witness_program) == 20:
            # P2WPKH
            return f"0014{bytes(witness_program).hex()}"
        elif witness_version == 0 and len(witness_program) == 32:
            # P2WSH
            return f"0020{bytes(witness_program).hex()}"
        else:
            raise ValueError("Tipo di indirizzo Bech32 non supportato")
    
    # Verifica se è un indirizzo Base58
    try:
        decoded = base58_decode(address)
        
        # Verifica il checksum
        if len(decoded) < 5:
            raise ValueError("Indirizzo Base58 troppo corto")
        
        payload = decoded[:-4]
        checksum = decoded[-4:]
        calculated_checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
        
        if checksum != calculated_checksum:
            raise ValueError("Checksum dell'indirizzo Base58 non valido")
        
        # Determina il tipo di indirizzo
        version = payload[0]
        pubkey_hash = payload[1:]
        
        if version == 0x00:  # P2PKH mainnet
            return f"76a914{pubkey_hash.hex()}88ac"
        elif version == 0x05:  # P2SH mainnet
            return f"a914{pubkey_hash.hex()}87"
        elif version == 0x6f:  # P2PKH testnet
            return f"76a914{pubkey_hash.hex()}88ac"
        elif version == 0xc4:  # P2SH testnet
            return f"a914{pubkey_hash.hex()}87"
        else:
            raise ValueError(f"Versione dell'indirizzo Base58 non supportata: {version}")
    
    except Exception as e:
        raise ValueError(f"Errore nella decodifica dell'indirizzo: {e}")

##########################################
# Costruzione della coinbase transaction
##########################################

def build_coinbase_tx(coinbase_value: int, coinbase_address: str, coinbase_message: str, block_template: dict) -> str:
    """
    Costruisce la coinbase transaction usando i parametri del block template.

    Se "!segwit" è presente in block_template["rules"], forziamo la modalità legacy
    anche se c'è "default_witness_commitment". Altrimenti, se "segwit" è
    presente o se troviamo "default_witness_commitment", costruiamo segwit.
    """
    # 1. Determiniamo se segwit è effettivamente attivo:
    rules = block_template.get("rules", [])
    if "!segwit" in rules:
        segwit_active = False
    else:
        # In regtest potrebbe esserci "segwit", "taproot", "csv"...
        # oppure semplicemente la presenza di "default_witness_commitment"
        # Indicherebbe un nodo che si aspetta il witness. Flessibilità:
        segwit_active = ("segwit" in rules) or ("default_witness_commitment" in block_template)

    # 2. Versione
    version = struct.pack("<I", 2)

    # 3. Input count: sempre 1 per la coinbase
    input_count = encode_varint(1)

    # 4. Prevout nullo (32 zero bytes + 0xffffffff)
    prevout = b'\x00' * 32 + b'\xff\xff\xff\xff'

    # 5. Blocco height
    block_height = block_template.get("height", 0)
    if block_height == 0:
        height_bytes = b'\x00'
    else:
        height_bytes = block_height.to_bytes((block_height.bit_length() + 7) // 8, 'little')

    # 6. Costruisce lo scriptSig: push(height) || EXTRANONCE_PLACEHOLDER || push(coinbase_message)
    height_push = push_data(height_bytes)
    msg_bytes = coinbase_message.encode('utf8')
    msg_push = push_data(msg_bytes)
    
    # Sostituisci il placeholder con extranonce1 e extranonce2
    extranonce1 = EXTRANONCE1.encode('utf8')
    extranonce2 = EXTRANONCE2.encode('utf8')
    extranonce = extranonce1 + extranonce2
    
    scriptSig = height_push + extranonce + msg_push
    scriptSig_length = encode_varint(len(scriptSig))

    sequence = b'\xff\xff\xff\xff'
    coinbase_input = prevout + scriptSig_length + scriptSig + sequence

    # 7. Output(s)
    outputs = b""
    output_value = struct.pack("<Q", coinbase_value)
    address_script_hex = address_to_scriptPubKey(coinbase_address)
    address_script = bytes.fromhex(address_script_hex)
    address_script_length = encode_varint(len(address_script))
    output1 = output_value + address_script_length + address_script
    outputs += output1

    if segwit_active and "default_witness_commitment" in block_template:
        # Aggiungi witness commitment come secondo output
        wc_hex = block_template["default_witness_commitment"]
        wc_script = bytes([0x6a, 0x24]) + bytes.fromhex("aa21a9ed") + bytes.fromhex(wc_hex)
        wc_script_length = encode_varint(len(wc_script))
        wc_value = struct.pack("<Q", 0)
        output2 = wc_value + wc_script_length + wc_script
        outputs += output2
        output_count = encode_varint(2)
    else:
        output_count = encode_varint(1)

    # 8. Locktime = 0
    locktime = b'\x00\x00\x00\x00'

    # 9. Costruiamo la transazione
    if segwit_active:
        # marker (0x00) e flag (0x01) e witness vuoto per coinbase
        marker_flag = b'\x00\x01'
        witness_count = encode_varint(0)
        tx = version + marker_flag + input_count + coinbase_input + output_count + outputs + witness_count + locktime
    else:
        # legacy
        tx = version + input_count + coinbase_input + output_count + outputs + locktime

    return tx.hex()
    
def split_coinbase(tx_hex: str) -> (str, str, str, str):
    """
    Divide la coinbase transaction in:
    - coinb1: parte iniziale prima dell'extranonce
    - extranonce1: prima parte dell'extranonce (da config)
    - extranonce2: seconda parte dell'extranonce (da config)
    - coinb2: parte finale dopo l'extranonce
    """
    # Estrai extranonce1 e extranonce2 dalla transazione
    extranonce1_hex = EXTRANONCE1.encode('utf8').hex()
    extranonce2_hex = EXTRANONCE2.encode('utf8').hex()
    
    # Trova le posizioni dei componenti
    start_extranonce = tx_hex.find(extranonce1_hex)
    if start_extranonce == -1:
        raise ValueError("Extranonce1 non trovato nella coinbase")
        
    end_extranonce = start_extranonce + len(extranonce1_hex) + len(extranonce2_hex)
    
    # Estrai i componenti
    coinb1 = tx_hex[:start_extranonce]
    extranonce1 = tx_hex[start_extranonce:start_extranonce + len(extranonce1_hex)]
    extranonce2 = tx_hex[start_extranonce + len(extranonce1_hex):end_extranonce]
    coinb2 = tx_hex[end_extranonce:]
    
    return coinb1, extranonce1, extranonce2, coinb2

###############################################################
# Main: chiamata al nodo e costruzione della coinbase
###############################################################

def main():
    rpc = connect_rpc()
    try:
        block_template = rpc.getblocktemplate({"rules": ["segwit"]})
        print("Block Template ottenuto:")
        print(json.dumps({k: v for k, v in block_template.items() if k != 'transactions'}, indent=4))

        coinbase_value = block_template["coinbasevalue"]
        raw_coinbase_tx = build_coinbase_tx(
            coinbase_value,
            COINBASE_ADDRESS,
            COINBASE_MESSAGE,
            block_template
        )

        # Dividi la coinbase nei suoi componenti
        coinb1, extranonce1, extranonce2, coinb2 = split_coinbase(raw_coinbase_tx)
        print("\nCoinbase completa e componenti:")
        print(f"\nCoinbase (hex): {raw_coinbase_tx}\n")
        print(f"coinb1: {coinb1}")
        print(f"extranonce1: {extranonce1}")
        print(f"extranonce2: {extranonce2}")
        print(f"coinb2: {coinb2}\n")

    except Exception as e:
        print(f"Errore durante l'operazione RPC: {e}")
        raise

if __name__ == "__main__":
    main()
