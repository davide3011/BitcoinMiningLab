from bitcoinrpc.authproxy import AuthServiceProxy
import struct, hashlib, os, random, json
from binascii import unhexlify, hexlify

# ============================================================================
#                      CARICAMENTO PARAMETRI CONFIGURAZIONE
# ============================================================================

def load_config(file_path='conf.json'):
    try:
        with open(file_path, 'r') as file:
            config = json.load(file)
        return config
    except FileNotFoundError:
        print("Errore: Il file di configurazione conf.json non è stato trovato.")
        exit(1)
    except json.JSONDecodeError:
        print("Errore: Il file conf.json contiene un formato non valido.")
        exit(1)
            
# Caricamento configurazione
config = load_config()

RPC_USER = config["rpcuser"]
RPC_PASSWORD = config["rpcpassword"]
RPC_HOST = config["rpcaddress"]
RPC_PORT = config["rpcport"]
MINER_ADDRESS = config["wallet_address"]

# =============================================================================
#                          FUNZIONI DI SUPPORTO
# =============================================================================

def test_rpc_connection():
    """ Verifica la connessione al nodo Bitcoin. """
    print("=== Verifica connessione RPC ===")
    try:
        rpc = connect_rpc()
        info = rpc.getblockchaininfo()
        print("\nConnessione riuscita!")
        print(f"Chain: {info['chain']}")
        print(f"Blocchi: {info['blocks']}")
        print(f"Difficoltà: {info['difficulty']}")
    except Exception as e:
        print(f"\nErrore di connessione: {e}")
        raise

def connect_rpc():
    """ Connette al nodo Bitcoin tramite RPC. """
    return AuthServiceProxy(f"http://{RPC_USER}:{RPC_PASSWORD}@{RPC_HOST}:{RPC_PORT}")

def double_sha256(data):
    """ Esegue il doppio SHA-256 su un dato. """
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()

def decode_nbits(nBits: int) -> str:
    """ Decodifica nBits in un target a 256-bit in formato esadecimale. """
    exponent = (nBits >> 24) & 0xff
    significand = nBits & 0x007fffff
    return f"{(significand << (8 * (exponent - 3))):064x}"
    
def get_block_template(rpc):
    """ Richiede un template di blocco al nodo (con regole SegWit). """
    try:
        return rpc.getblocktemplate({"rules": ["segwit"]})
    except Exception as e:
        print(f"Errore nel recupero del template: {e}")
        return None

def ensure_witness_data(rpc, template):
    """ Controlla e aggiorna le transazioni del template con dati completi. """
    corrected_txs = []
    try:
        mempool_info = rpc.getrawmempool(True)
    except Exception as e:
        print(f"Errore nel recupero della mempool: {e}")
        mempool_info = {}
    
    for tx in template["transactions"]:
        txid = tx["txid"]
        raw = tx["data"]
        
        if txid in mempool_info:
            wtxid = mempool_info[txid].get("wtxid", txid)
        else:
            wtxid = txid  # Usa il txid se il wtxid non è disponibile
        
        try:
            raw_tx_full = rpc.getrawtransaction(txid, False)
            if raw_tx_full:
                raw = raw_tx_full
        except Exception as e:
            print(f"Impossibile recuperare raw witness di {txid}: {e}")
        
        corrected_txs.append({"hash": txid, "data": raw})
    
    template["transactions"] = corrected_txs

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
    
def build_coinbase_transaction(template):
    """Crea la transazione coinbase con un output di ricompensa e, se presente, un OP_RETURN per il witness commitment."""
    height = template["height"]
    reward = template["coinbasevalue"]
    witness_commitment_hex = template.get("default_witness_commitment", "")

    # Codifica l'altezza del blocco in formato BIP34 e aggiunge una extranonce casuale
    script_sig_hex = tx_encode_coinbase_height(height) + os.urandom(4).hex()

    # Recupera lo scriptPubKey del miner
    rpc = connect_rpc()
    miner_script_pubkey = rpc.getaddressinfo(MINER_ADDRESS)["scriptPubKey"]

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
    
def mine_block(header_hex, target_hex, nonce_mode="incremental"):
    """
    Esegue il mining cercando un nonce valido rispetto al target.
    
    - `incremental`: parte da 0 e incrementa di 1 fino al massimo valore possibile.
    - `random`: genera un nonce casuale a ogni iterazione.
    - `mixed`: genera un primo nonce casuale, poi incrementa di 1.
    """
    print(f"\n=== Inizio del Mining | Modalità: {nonce_mode} ===")

    target = int(target_hex, 16)
    base_header = unhexlify(header_hex[:152])  # Parte fissa dell'header
    attempts = 0  # Contatore tentativi

    # Imposta il nonce iniziale in base alla modalità scelta
    if nonce_mode == "incremental":
        nonce = 0
    elif nonce_mode == "random":
        nonce = random.randint(0, 0xFFFFFFFF)
    elif nonce_mode == "mixed":
        nonce = random.randint(0, 0xFFFFFFFF)
    else:
        raise ValueError("Modalità di mining non valida. Scegli tra 'incremental', 'random' o 'mixed'.")

    while True:
        # Aggiorna i 4 byte finali del nonce
        full_header = base_header + struct.pack("<I", nonce)
        block_hash = double_sha256(full_header)[::-1].hex()

        # Stampa i progressi ogni 100.000 tentativi
        attempts += 1
        if attempts % 100000 == 0:
            print(f"Tentativi: {attempts:,} | nonce: {nonce} | Hash: {block_hash}")

        # Verifica se il nonce trovato è valido
        if int(block_hash, 16) < target:
            print(f"\nBlocco trovato!")
            print(f"Nonce valido: {nonce}")
            print(f"Hash del blocco: {block_hash}")
            print(f"Tentativi totali: {attempts:,}")
            return hexlify(full_header).decode(), nonce

        # Aggiorna il nonce in base alla modalità selezionata
        if nonce_mode == "incremental" or nonce_mode == "mixed":
            nonce = (nonce + 1) % 0x100000000  # Mantieni il nonce nei limiti di 32 bit
        elif nonce_mode == "random":
            nonce = random.randint(0, 0xFFFFFFFF)

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

def submit_block(rpc, serialized_block):
    """Invia il blocco minato al nodo Bitcoin."""
    print("\n=== Invio del blocco al nodo Bitcoin ===")
    print("\nInviando il blocco al nodo Bitcoin...")

    if not serialized_block:
        print("Blocco non serializzato correttamente. Annullando l'invio.")
        return

    try:
        result = rpc.submitblock(serialized_block)
        if result is None:
            print("\nBlocco accettato nella blockchain!")
        else:
            print(f"\nErrore nell'invio del blocco: {result}")
    except Exception as e:
        print(f"\nErrore RPC durante submitblock: {e}")
        
# =============================================================================
#                               MAIN SCRIPT
# =============================================================================

if __name__ == "__main__":
    # STEP 1) TEST RPC
    test_rpc_connection()

    # Connessione RPC per evitare chiamate multiple
    rpc = connect_rpc()

    # STEP 2) GET BLOCK TEMPLATE
    template = get_block_template(rpc)
    if not template:
        print("\nERRORE: Impossibile ottenere il template del blocco. Terminazione.")
        exit(1)

    # STEP 3) Assicurarsi di avere transazioni con dati completi
    ensure_witness_data(rpc, template)

    # STEP 4) COSTRUISCI COINBASE
    coinbase_tx = build_coinbase_transaction(template)

    # STEP 5) MODIFICA TARGET
    DIFFICULTY_FACTOR = float(config.get("difficulty_factor", 1.0))

    if DIFFICULTY_FACTOR < 1:
        print("Attenzione: difficulty_factor deve essere >= 1. Impostazione a 1.0")
        DIFFICULTY_FACTOR = 1.0  # Evita errori se viene impostato un valore errato

    nBits_int = int(template["bits"], 16)
    original_target = decode_nbits(nBits_int)  # Target originale
    modified_target_int = int(original_target, 16) // int(DIFFICULTY_FACTOR)  # Target ridotto
    modified_target = f"{modified_target_int:064x}"  # Converti in esadecimale
    print(f"Target originale: {original_target}")
    print(f"Target modificato ({DIFFICULTY_FACTOR}x più difficile): {modified_target}")

    # STEP 6) CALCOLA MERKLE ROOT
    merkle_root = calculate_merkle_root(coinbase_tx, template["transactions"])

    # STEP 7) COSTRUISCI HEADER
    header_hex = build_block_header(template["version"], template["previousblockhash"],
                                    merkle_root, template["curtime"], template["bits"], 0)

    # STEP 8) MINING
    nonce_mode = config.get("nonce_mode", "incremental")  # Legge dal JSON, default "incremental"
    mined_header_hex, nonce = mine_block(header_hex, modified_target, nonce_mode)  # Usa il target modificato
    if not mined_header_hex:
        print("\nERRORE: Nessun hash valido trovato! Mining fallito.")
        exit(1)

    # STEP 9) SERIALIZZA IL BLOCCO
    serialized_block = serialize_block(mined_header_hex, coinbase_tx, template["transactions"])

    # STEP 10) INVIA IL BLOCCO
    submit_block(rpc, serialized_block)
