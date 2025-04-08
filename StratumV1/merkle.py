import json
import hashlib
from bitcoin_rpc import connect_rpc, get_block_template

def hash256(data: bytes) -> str:
    """
    Calcola il doppio SHA256 (hash256) su dati in formato bytes e restituisce il risultato in esadecimale.
    """
    return hashlib.sha256(hashlib.sha256(data).digest()).hexdigest()

def build_merkle_tree(leaves):
    """
    Costruisce l'albero Merkle dato un elenco di foglie (hash in esadecimale).
    Restituisce una lista di livelli, dove il primo livello sono le foglie e l'ultimo è il livello con il Merkle root.
    """
    tree = []
    current_level = leaves[:]  # Copia delle foglie
    tree.append(current_level)
    while len(current_level) > 1:
        # Se il numero di elementi è dispari, duplico l'ultimo elemento
        if len(current_level) % 2 == 1:
            current_level.append(current_level[-1])
        next_level = []
        for i in range(0, len(current_level), 2):
            left = bytes.fromhex(current_level[i])
            right = bytes.fromhex(current_level[i+1])
            parent = hash256(left + right)
            next_level.append(parent)
        current_level = next_level
        tree.append(current_level)
    return tree

def extract_merkle_branch(tree, index):
    """
    Estrae la Merkle branch per una foglia all'indice 'index'.
    La branch è l'insieme dei "sibling hash" necessari per ricostruire il Merkle root.
    """
    branch = []
    for level in tree[:-1]:  # Escludiamo il livello radice
        if index % 2 == 0:
            sibling_index = index + 1
        else:
            sibling_index = index - 1
        branch.append(level[sibling_index])
        index //= 2  # Aggiorna l'indice per il livello superiore
    return branch

def main():
    # Collega il server al nodo Bitcoin e ottieni il block template
    block_template = get_block_template(["segwit"])
    print("Block Template ricevuto:")
    print(json.dumps(block_template, indent=2))
    
    # Ottieni la lista delle transazioni dal template.
    # Nota: In un blocco reale la lista contiene la coinbase (in posizione 0) e le transazioni dal mempool.
    txs = block_template.get("transactions", [])
    if not txs:
        print("Nessuna transazione trovata nel template. Assicurati che il nodo restituisca la coinbase e le altre transazioni.")
        return
    
    # Estrai l'hash (txid) di ogni transazione per creare le foglie dell'albero Merkle.
    leaves = [tx["txid"] for tx in txs]
    print("\nNumero di transazioni (foglie):", len(leaves))
    
    # Costruisci l'albero Merkle
    tree = build_merkle_tree(leaves)
    merkle_root = tree[-1][0]
    print("\nMerkle Root calcolato:")
    print(merkle_root)
    
    # Estrai la Merkle branch per la prima transazione (indice 0, che corrisponde alla coinbase)
    branch = extract_merkle_branch(tree, 0)
    print("\nMerkle Branch per la foglia con indice 0:")
    for lvl, h in enumerate(branch):
        print(f"Livello {lvl}: {h}")
    
    # Per verificare la branch, il miner può ricostruire la radice partendo da leaves[0]:
    computed = leaves[0]
    index = 0
    for sibling in branch:
        if index % 2 == 0:
            # La foglia è a sinistra, concatenare: computed || sibling
            combined = bytes.fromhex(computed) + bytes.fromhex(sibling)
        else:
            # La foglia è a destra, concatenare: sibling || computed
            combined = bytes.fromhex(sibling) + bytes.fromhex(computed)
        computed = hash256(combined)
        index //= 2
    print("\nMerkle Root ricostruito dalla branch:")
    print(computed)
    if computed == merkle_root:
        print("La Merkle branch è corretta!")
    else:
        print("Errore: la Merkle branch non ricostruisce correttamente il Merkle root.")

if __name__ == "__main__":
    main()
