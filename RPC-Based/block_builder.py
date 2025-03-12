import struct, hashlib, os
from binascii import unhexlify, hexlify

def double_sha256(data):
    """ Esegue il doppio SHA-256 su un dato. """
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()

def decode_nbits(nBits: int) -> str:
    """ Decodifica nBits in un target a 256-bit in formato esadecimale. """
    exponent = (nBits >> 24) & 0xff
    significand = nBits & 0x007fffff
    return f"{(significand << (8 * (exponent - 3))):064x}"

def encode_varint(value):
    """Codifica un numero come VarInt (CompactSize Unsigned Integer)."""
    thresholds = [(0xfd, ""), (0xffff, "fd"), (0xffffffff, "fe"), (0xffffffffffffffff, "ff")]
    for threshold, prefix in thresholds:
        if value <= threshold:
            return prefix + value.to_bytes(max(1, (threshold.bit_length() + 7) // 8), 'little').hex()
    raise ValueError("Il valore supera il limite massimo per VarInt")

def tx_encode_coinbase_height(height):
    """Codifica l'altezza del blocco secondo BIP34 in VarInt."""
    if height < 1:
        raise ValueError("L'altezza del blocco deve essere maggiore di 0")

    height_bytes = height.to_bytes((height.bit_length() + 7) // 8, 'little')
    return f"{len(height_bytes):02x}" + height_bytes.hex()

def build_coinbase_transaction(template, miner_script_pubkey):
    """Crea la transazione coinbase con un output di ricompensa e, se presente, un OP_RETURN per il witness commitment."""
    height = template["height"]
    reward = template["coinbasevalue"]
    witness_commitment_hex = template.get("default_witness_commitment", "")

    # Codifica l'altezza del blocco in formato BIP34 e aggiunge una extranonce casuale
    script_sig_hex = tx_encode_coinbase_height(height) + os.urandom(4).hex()

    # Costruzione della transazione coinbase
    tx_version = "01000000"
    prev_hash, prev_index, sequence, locktime = "00" * 32, "ffffffff", "ffffffff", "00000000"
    script_len = encode_varint(len(script_sig_hex) // 2)

    # Creazione output per la ricompensa del miner
    satoshis_reward = struct.pack("<Q", reward).hex()
    miner_script_len = encode_varint(len(miner_script_pubkey) // 2)
    outputs_hex = satoshis_reward + miner_script_len + miner_script_pubkey
    output_count = 1

    # Aggiunta del Witness Commitment se presente
    if witness_commitment_hex and len(witness_commitment_hex) == 64:
        witness_commitment_script = "6a24aa21a9ed" + witness_commitment_hex
        outputs_hex += "00" * 8 + encode_varint(len(witness_commitment_script) // 2) + witness_commitment_script
        output_count += 1

    # Serializzazione della coinbase transaction
    return (
        f"{tx_version}01{prev_hash}{prev_index}{script_len}{script_sig_hex}{sequence}"
        f"{encode_varint(output_count)}{outputs_hex}{locktime}"
    )

def calculate_merkle_root(coinbase_tx, transactions):
    """Calcola il Merkle Root del blocco."""
    coinbase_hash = double_sha256(unhexlify(coinbase_tx))[::-1].hex()
    tx_hashes = [coinbase_hash] + [
        tx["hash"] if "hash" in tx else double_sha256(unhexlify(tx["data"]))[::-1].hex()
        for tx in transactions
    ]

    # Converti gli hash in formato bytes e inverti in little-endian
    tx_hashes = [unhexlify(tx)[::-1] for tx in tx_hashes]

    # Calcolo del Merkle Root iterativo
    while len(tx_hashes) > 1:
        tx_hashes += [tx_hashes[-1]] if len(tx_hashes) % 2 == 1 else []  # Padding se dispari
        tx_hashes = [double_sha256(tx_hashes[i] + tx_hashes[i + 1]) for i in range(0, len(tx_hashes), 2)]

    return hexlify(tx_hashes[0][::-1]).decode()

def build_block_header(version, prev_hash, merkle_root, timestamp, bits, nonce):
    """Costruisce gli 80 byte dell'header del blocco e li restituisce in formato hex."""
    header = (
        struct.pack("<I", version) +
        unhexlify(prev_hash)[::-1] +
        unhexlify(merkle_root)[::-1] +
        struct.pack("<I", timestamp) +
        unhexlify(bits)[::-1] +
        struct.pack("<I", nonce)
    )
    return hexlify(header).decode()

def serialize_block(header_hex, coinbase_tx, transactions):
    """Serializza l'intero blocco nel formato richiesto dal protocollo Bitcoin."""
    print("\n=== Serializzazione del blocco ===")
    print("\nSerializzando il blocco...")

    num_tx = len(transactions) + 1  # Include la coinbase
    num_tx_hex = encode_varint(num_tx)  # Già in formato hex

    try:
        transactions_hex = "".join(tx["data"] for tx in transactions)
    except KeyError as e:
        print(f"Errore: una transazione manca del campo '{e}'")
        return None

    block_hex = header_hex + num_tx_hex + coinbase_tx + transactions_hex

    print("\nBlocco serializzato correttamente!")
    print(f"Numero transazioni = {num_tx}")
    print(f"Blocco HEX:\n{block_hex}")

    return block_hex