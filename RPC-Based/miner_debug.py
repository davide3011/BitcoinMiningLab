from bitcoinrpc.authproxy import AuthServiceProxy
import struct
import hashlib
import os
from binascii import unhexlify, hexlify

# Configurazione RPC
RPC_USER = "..."
RPC_PASSWORD = "..."
RPC_HOST = "..."
RPC_PORT = "..."

# Indirizzo del miner
MINER_ADDRESS = "........"


# =============================================================================
#                          FUNZIONI DI SUPPORTO
# =============================================================================

def test_rpc_connection():
    """ Verifica la connessione al nodo Bitcoin. """
    print("=== STEP 1: Verifichiamo la connessione RPC ===")
    url = f"http://{RPC_USER}:{RPC_PASSWORD}@{RPC_HOST}:{RPC_PORT}"
    print(f"🔄 Tentativo di connessione al nodo Bitcoin su: {url}")
    try:
        rpc = connect_rpc()
        info = rpc.getblockchaininfo()
        print("\n✅ Connessione riuscita!")
        print(f"🌎 Chain: {info['chain']}")
        print(f"⛏️ Blocchi: {info['blocks']}")
        print(f"⚡ Difficoltà: {info['difficulty']}")
    except Exception as e:
        print(f"\n❌ Errore di connessione: {str(e)}")
        raise

def connect_rpc():
    """ Connette al nodo Bitcoin tramite RPC. """
    url = f"http://{RPC_USER}:{RPC_PASSWORD}@{RPC_HOST}:{RPC_PORT}"
    return AuthServiceProxy(url)

def double_sha256(data):
    """ Esegue il doppio SHA-256 su un dato. """
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()

def decode_nbits(nBits: int) -> str:
    """ Decodifica nBits in un target a 256-bit in formato esadecimale. """
    exponent = (nBits >> 24) & 0xff
    significand = nBits & 0x007fffff
    target = significand << (8 * (exponent - 3))
    return f"{target:064x}"

# =============================================================================
#                      FUNZIONI PRINCIPALI DEL MINER
# =============================================================================

def get_block_template():
    """ Richiede un template di blocco al nodo (con regole SegWit). """
    print("\n=== STEP 2: Ottenere il template del blocco ===")
    rpc = connect_rpc()
    try:
        print("\n🔄 Richiedendo il template del blocco (rules=segwit)...")
        template = rpc.getblocktemplate({"rules": ["segwit"]})
        print("\n✅ Template del blocco ottenuto con successo!")
        print(f"📏 Altezza del blocco: {template['height']}")
        print(f"🔗 Blocco precedente: {template['previousblockhash']}")
        print(f"💰 Ricompensa: {template['coinbasevalue']} satoshi")
        print(f"🎯 Target: {template['target']}")
        print(f"⚡ Bits: {template['bits']}")
        print(f"📦 Transazioni incluse: {len(template['transactions'])}")
        return template
    except Exception as e:
        print(f"\n❌ Errore nel recupero del template: {str(e)}")
        return None

def ensure_witness_data(template):
    """
    Controlla se le transazioni nel template contengono witness.
    Se il campo 'data' non presenta witness, recupera i byte completi dal nodo.
    Esclude le transazioni già confermate in un blocco.
    """
    rpc = connect_rpc()
    corrected_txs = []

    try:
        mempool_info = rpc.getrawmempool(True)  # Otteniamo anche i wtxid
    except Exception as e:
        print(f"❌ Errore nel recupero della mempool: {e}")
        mempool_info = {}

    for tx in template["transactions"]:
        raw = tx["data"]
        txid = tx["txid"]  # 🔹 Ora usiamo `txid`, NON `hash`

        # Controlliamo se il txid è nella mempool
        if txid in mempool_info:
            wtxid = mempool_info[txid].get("wtxid", txid)  # Se non esiste wtxid, usa txid
            print(f"🔹 TXID {txid} corrisponde a WTXID {wtxid}")
        else:
            print(f"⚠️ La transazione {txid} non è nella mempool, potrebbe essere confermata o rimossa.")
            wtxid = txid  # Se non la troviamo, proviamo con il txid normale

        # 🔹 Recuperiamo la transazione completa
        try:
            raw_tx_full = rpc.getrawtransaction(txid, False)  # Proviamo con il TXID
            if raw_tx_full:
                raw = raw_tx_full
        except Exception as e:
            print(f"⚠️ Impossibile recuperare raw witness di {txid}: {e}")

        corrected_txs.append({"hash": txid, "data": raw})

    template["transactions"] = corrected_txs

def encode_varint(value):
    """
    Codifica un numero come VarInt (CompactSize Unsigned Integer).
    
    - Se value < 0xfd → 1 byte
    - Se value ≤ 0xffff → 3 byte con prefisso 0xfd
    - Se value ≤ 0xffffffff → 5 byte con prefisso 0xfe
    - Se value ≤ 0xffffffffffffffff → 9 byte con prefisso 0xff
    """
    if value < 0xfd:
        return f"{value:02x}"  # 1 byte diretto
    elif value <= 0xffff:
        return f"fd{value.to_bytes(2, 'little').hex()}"
    elif value <= 0xffffffff:
        return f"fe{value.to_bytes(4, 'little').hex()}"
    else:
        return f"ff{value.to_bytes(8, 'little').hex()}"
    
def tx_encode_coinbase_height(height):
    """ Codifica l'altezza del blocco nel formato richiesto da BIP34 in VarInt. """
    if height < 1:
        raise ValueError("L'altezza del blocco deve essere maggiore di 0")

    # Determina quanti byte servono per rappresentare l'altezza
    height_bytes = height.to_bytes((height.bit_length() + 7) // 8, 'little')

    # Opcode PUSH per il numero di byte che compongono l'altezza
    push_opcode = bytes([len(height_bytes)])

    print(f"🔍 DEBUG: Altezza Blocco = {height}")
    print(f"🔍 DEBUG: Altezza LE Hex = {height_bytes.hex()}")
    print(f"🔍 DEBUG: Opcode Push Hex = {push_opcode.hex()}")

    return push_opcode.hex() + height_bytes.hex()

def build_coinbase_transaction(template):
    """
    Crea la transazione coinbase con un output di ricompensa e, se presente,
    un OP_RETURN per il witness commitment.
    """
    print(f"\n=== STEP 3: Creare la transazione coinbase ===")
    height = template["height"]
    reward = template["coinbasevalue"]
    witness_commitment_hex = template.get("default_witness_commitment", "")

    print(f"\n🔨 Creazione coinbase TX per il blocco #{height}...")

    # ✅ 1) Codifica l'altezza del blocco nel formato richiesto da BIP34
    script_sig_hex = tx_encode_coinbase_height(height)

    # ✅ 2) Generiamo una extranonce (4 byte casuali)
    extranonce = os.urandom(4).hex()
    script_sig_hex += extranonce  # Uniamo height (BIP34) con extranonce

    print(f"🔍 DEBUG: Altezza Blocco = {height}")
    print(f"🔍 DEBUG: Extranonce = {extranonce}")
    print(f"🔹 ScriptSig (BIP34 height + extranonce): {script_sig_hex}")

    # ✅ 3) Recuperiamo lo scriptPubKey del miner
    rpc = connect_rpc()
    miner_script_pubkey = rpc.getaddressinfo(MINER_ADDRESS)["scriptPubKey"]
    print(f"🔍 DEBUG: Miner scriptPubKey = {miner_script_pubkey}")

    # ✅ 4) Campi fissi della coinbase transaction
    tx_version = "01000000"  # Versione 1 per compatibilità
    prev_hash = "00" * 32  # Coinbase ha prev_hash nullo
    prev_index = "ffffffff"  # Coinbase ha prev_index nullo
    sequence = "ffffffff"  # Sequence number
    script_len = encode_varint(len(script_sig_hex) // 2)  # Numero di byte effettivo
    locktime = "00000000"

    # ✅ 5) Creare output per la ricompensa del miner
    outputs_hex = ""
    output_count_int = 0

    satoshis_reward = struct.pack("<Q", reward).hex()
    miner_script_len = encode_varint(len(miner_script_pubkey) // 2)
    outputs_hex += satoshis_reward + miner_script_len + miner_script_pubkey
    output_count_int += 1

    print(f"🔍 DEBUG: Ricompensa Miner = {reward} satoshi")

    # ✅ 6) Se il blocco contiene transazioni SegWit, aggiungiamo il Witness Commitment (BIP141)
    if witness_commitment_hex and len(witness_commitment_hex) == 64:
        print("✅ Il blocco contiene transazioni SegWit, aggiungiamo il witness commitment.")

        # OP_RETURN (0x6a) + Lunghezza dati (0x24) + Testa fissa 0xaa21a9ed + Witness Commitment (32-byte)
        witness_commitment_script = "6a24aa21a9ed" + witness_commitment_hex

        # Aggiungiamo l'output del witness commitment
        zero_value = "00" * 8  # 0-value OP_RETURN
        wc_len = encode_varint(len(witness_commitment_script) // 2)
        outputs_hex += zero_value + wc_len + witness_commitment_script
        output_count_int += 1

        print(f"🔍 DEBUG: Witness Commitment Hex = {witness_commitment_hex}")
        print(f"🔍 DEBUG: Witness Commitment Script = {witness_commitment_script}")
    else:
        print("⚠️ Il blocco non contiene transazioni SegWit, nessun Witness Commitment richiesto.")

    # ✅ 7) Encode output count come VarInt
    output_count_hex = encode_varint(output_count_int)

    # ✅ 8) Serializzazione finale della coinbase transaction
    coinbase_tx = (
        f"{tx_version}01{prev_hash}{prev_index}{script_len}{script_sig_hex}{sequence}{output_count_hex}{outputs_hex}{locktime}"
    )

    print(f"\n✅ Coinbase TX creata:")
    print(f"🔍 DEBUG: Versione TX = {tx_version}")
    print(f"🔍 DEBUG: Prev Hash = {prev_hash}")
    print(f"🔍 DEBUG: Prev Index = {prev_index}")
    print(f"🔍 DEBUG: ScriptSig Length = {script_len}")
    print(f"🔍 DEBUG: ScriptSig = {script_sig_hex}")
    print(f"🔍 DEBUG: Sequence = {sequence}")
    print(f"🔍 DEBUG: Output Count = {output_count_hex}")
    print(f"🔍 DEBUG: Outputs Hex = {outputs_hex}")
    print(f"🔍 DEBUG: Locktime = {locktime}")
    print(f"🔍 DEBUG: Coinbase TX Hex = {coinbase_tx}\n")

    return coinbase_tx

def calculate_merkle_root(coinbase_tx, transactions):
    """
    Calcola il Merkle Root del blocco usando:
    - Hash della coinbase (sempre il primo)
    - Hash delle altre transazioni incluse nel template
    """
    print("\n=== STEP 5: Calcolare il Merkle Root ===")
    print("\n🔢 Calcolando il Merkle Root...")

    # 1) Calcola l'hash della coinbase transaction (in little-endian)
    coinbase_hash = double_sha256(unhexlify(coinbase_tx))[::-1].hex()
    print(f"🔹 Hash della coinbase: {coinbase_hash}")

    # 2) Se il template non fornisce txid, calcoliamolo
    tx_hashes = [coinbase_hash]

    for tx in transactions:
        try:
            # Se "hash" è disponibile, usiamo quello
            if "hash" in tx:
                tx_hashes.append(tx["hash"])
            else:
                # Se "hash" non c'è, calcoliamo il txid manualmente
                raw_tx = unhexlify(tx["data"])
                txid = double_sha256(raw_tx)[::-1].hex()
                tx_hashes.append(txid)
        except KeyError as e:
            print(f"⚠️ Errore: transazione senza campo '{e}', dati: {tx}")

    # 3) Convertiamo gli hash in formato bytes e li invertiamo (little-endian)
    tx_hashes = [unhexlify(tx)[::-1] for tx in tx_hashes]

    # 4) Calcoliamo il Merkle Root
    while len(tx_hashes) > 1:
        new_level = []
        if len(tx_hashes) % 2 == 1:
            tx_hashes.append(tx_hashes[-1])  # Duplicazione dell'ultimo hash se dispari

        for i in range(0, len(tx_hashes), 2):
            left = tx_hashes[i]
            right = tx_hashes[i+1]
            pair_hash = double_sha256(left + right)
            new_level.append(pair_hash)

        tx_hashes = new_level

    # 5) Convertiamo il Merkle Root in formato esadecimale big-endian
    merkle_root = hexlify(tx_hashes[0][::-1]).decode()
    print(f"\n✅ Merkle Root calcolato: {merkle_root}")
    
    return merkle_root

def build_block_header(version, prev_hash, merkle_root, timestamp, bits, nonce):
    """ Costruisce i 80 byte di header del blocco e li ritorna in hex. """
    print("\n=== STEP 6: Costruire l'header del blocco ===")
    print("\n📦 Costruendo l'header del blocco...")

    header = (
        struct.pack("<I", version) +
        unhexlify(prev_hash)[::-1] +
        unhexlify(merkle_root)[::-1] +
        struct.pack("<I", timestamp) +
        unhexlify(bits)[::-1] +
        struct.pack("<I", nonce)
    )

    header_hex = hexlify(header).decode()
    print(f"\n✅ Header del blocco costruito con successo!")
    print(f"📝 Header HEX: {header_hex}")
    return header_hex

def mine_block(header_hex, target_hex):
    """ Esegue il mining cercando un nonce che soddisfi l'hash < target. """
    print("\n=== STEP 7: Inizio del Mining ===")
    print("\n⛏️ Iniziando il mining...")

    nonce = 0
    target = int(target_hex, 16)

    # header_hex[:152] = i primi 76 byte (in hex) => 38 byte in bin. Ultimi 4 byte = nonce
    # 80 byte totali = 160 hex chars, di cui 8 (4 byte) per il nonce
    # offset del nonce in hex = 152
    while nonce <= 0xFFFFFFFF:
        # Aggiorna i 4 byte finali del nonce
        full_header = header_hex[:152] + struct.pack("<I", nonce).hex()

        # Calcola l'hash
        block_hash = double_sha256(unhexlify(full_header))[::-1].hex()

        if nonce % 1000 == 0:
            print(f"🔍 Nonce: {nonce} | Hash: {block_hash}")

        if int(block_hash, 16) < target:
            print(f"\n✅ Blocco trovato! 🎉")
            print(f"🔢 Nonce valido: {nonce}")
            print(f"🔗 Hash del blocco: {block_hash}")
            return full_header, nonce

        nonce += 1

    print("\n❌ Non è stato trovato un hash valido.")
    return None, None

def submit_block_header(header_hex):
    """
    Invia solo l'header del blocco al nodo Bitcoin per verificare se è valido.
    """
    print("\n=== TEST: Invio dell'header del blocco al nodo ===")

    rpc = connect_rpc()
    try:
        result = rpc.submitheader(header_hex)  # Chiamata RPC

        if result is None:
            print("\n✅ Header accettato dal nodo! Il blocco è collegato correttamente.")
            return True  # Header valido, possiamo procedere con submitblock
        else:
            print(f"\n❌ Errore nell'invio dell'header: {result}")
            return False  # Header non valido, qualcosa non va
    except Exception as e:
        print(f"\n❌ Errore RPC in submitheader: {str(e)}")
        return False

def serialize_block(header_hex, coinbase_tx, transactions):
    """
    Serializza l'intero blocco in formato:
      [block_header 80 byte] +
      [varint(num_tx)] +
      [coinbase_tx in raw hex] +
      [altri tx in raw hex (completi di witness se necessario)]
    """
    print("\n=== STEP 8: Serializzazione del blocco ===")
    print("\n🚀 Serializzando il blocco...")

    num_tx = len(transactions) + 1  # coinbase + transazioni
    num_tx_bytes = unhexlify(encode_varint(num_tx))  # CORRETTO: usa encode_varint

    try:
        transactions_hex = b''.join(unhexlify(tx["data"]) for tx in transactions)
    except Exception as e:
        print(f"❌ Errore nella serializzazione delle transazioni: {e}")
        return None

    block_bytes = (
        unhexlify(header_hex) +
        num_tx_bytes +
        unhexlify(coinbase_tx) +
        transactions_hex
    )

    block_hex = hexlify(block_bytes).decode()
    
    print(f"\n✅ Blocco serializzato correttamente!")
    print(f"🔍 DEBUG: Numero transazioni = {num_tx}")
    print(f"🔍 DEBUG: Blocco HEX:\n{block_hex[:100]}...")  # Stampiamo solo i primi 100 caratteri per evitare troppa lunghezza
    
    return block_hex

def submit_block(serialized_block):
    """ Invia il blocco minato al nodo. """
    print("\n=== STEP 9: Invio del blocco al nodo Bitcoin ===")
    print("\n🚀 Inviando il blocco al nodo Bitcoin...")

    if not serialized_block:
        print("❌ Blocco non serializzato correttamente. Annullando l'invio.")
        return

    rpc = connect_rpc()
    try:
        result = rpc.submitblock(serialized_block)
        if result is None:
            print("\n✅ Blocco accettato nella blockchain! 🎉")
        else:
            print(f"\n❌ Errore nell'invio del blocco: {result}")
    except Exception as e:
        print(f"\n❌ Errore RPC durante submitblock: {e}")


# =============================================================================
#                               MAIN SCRIPT
# =============================================================================
if __name__ == "__main__":
    # STEP 1) TEST RPC
    test_rpc_connection()

    # STEP 2) GET BLOCK TEMPLATE
    template = get_block_template()
    if not template:
        print("\n❌ ERRORE: Impossibile ottenere il template del blocco. Terminazione.")
        exit(1)

    # Passo intermedio: assicurarsi di avere la raw tx con witness (se necessarie).
    ensure_witness_data(template)  # <-- se "template['transactions']" già fosse OK, non farà danni

    # STEP 3) COSTRUISCI COINBASE
    coinbase_tx = build_coinbase_transaction(template)

    # 🔹 DEBUG: Verifica altezza e coinbase TX
    print(f"\n🔍 DEBUG: Altezza Blocco dal Template: {template['height']}")
    print(f"🔍 DEBUG: Coinbase TX HEX = {coinbase_tx}")

    # STEP 4) DECODIFICA TARGET
    nBits_int = int(template["bits"], 16)  # '0x207fffff' -> int
    target_256bit = decode_nbits(nBits_int)
    print(f"\n=== STEP 4: Decodifica Target da nBits ===")
    print(f"🎯 Target decodificato: {target_256bit}")

    # STEP 5) CALCOLA MERKLE ROOT
    merkle_root = calculate_merkle_root(coinbase_tx, template["transactions"])

    # 🔹 DEBUG: Confronto Merkle Root
    print(f"\n🔍 DEBUG: Merkle Root calcolato = {merkle_root}")
    print(f"🔍 DEBUG: Merkle Root atteso dal nodo = {template.get('merkleroot', 'N/A')}")

    # A volte compare "merkleroot" nel template per check. Se c'è, confrontiamo:
    if "merkleroot" in template and merkle_root != template["merkleroot"]:
        print("⚠️ ATTENZIONE: Il Merkle Root calcolato NON corrisponde a quello atteso dal nodo!")

    # STEP 6) COSTRUISCI HEADER
    version = template["version"]
    prev_hash = template["previousblockhash"]
    curtime = template["curtime"]
    bits = template["bits"]
    header_hex = build_block_header(version, prev_hash, merkle_root, curtime, bits, 0)

    # STEP 7) MINING
    mined_header_hex, nonce = mine_block(header_hex, template["target"])
    if not mined_header_hex:
        print("\n❌ ERRORE: Nessun hash valido trovato! Mining fallito.")
        exit(1)

    # 🔹 DEBUG: Blocco minato con successo
    final_hash = double_sha256(unhexlify(mined_header_hex))[::-1].hex()
    print(f"\n✅ Blocco minato con successo!")
    print(f"   🔢 Nonce trovato: {nonce}")
    print(f"   🔗 Hash valido:   {final_hash}")

    # STEP 8) PRIMA VERIFICHIAMO L'HEADER
    header_ok = submit_block_header(mined_header_hex)

    # Se l'header è accettato, serializziamo il blocco e lo inviamo
    if header_ok:
        print("\n=== HEADER VERIFICATO! Procediamo con il blocco intero ===")

        # DEBUG: Verifica se le transazioni sono incluse correttamente
        print(f"\n🔍 Debug: Numero di transazioni nel blocco = {len(template['transactions'])}")
        for i, tx in enumerate(template["transactions"]):
            print(f"🔹 TX {i+1} - Hash: {tx.get('hash', 'MISSING')}, Data length: {len(tx.get('data', '')) if 'data' in tx else 'MISSING'}")

        # STEP 8) SERIALIZZA IL BLOCCO
        serialized_block = serialize_block(mined_header_hex, coinbase_tx, template["transactions"])

        # 🔹 DEBUG: Mostra primi 100 caratteri del blocco
        print(f"\n🔍 DEBUG: Blocco serializzato HEX:\n{serialized_block[:100]}...")

        # STEP 9) SUBMIT BLOCCO COMPLETO
        print("\n🚀 DEBUG: Invio blocco HEX:\n", serialized_block, "...")
        submit_block(serialized_block)
    else:
        print("\n❌ L'header non è valido, blocco scartato!")
        exit(1)
