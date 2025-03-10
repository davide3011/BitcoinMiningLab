"""
Modulo di configurazione per il nodo Bitcoin e il processo di mining.
Definisce le variabili necessarie per la connessione RPC, l'indirizzo del wallet,
il fattore di difficoltà e la modalità di calcolo del nonce.
"""

# ---------------------------
# Configurazione RPC
# ---------------------------
RPC_USER = "..."                  # Username per l'autenticazione RPC
RPC_PASSWORD = "..."              # Password per l'autenticazione RPC
RPC_HOST = "..."                  # Indirizzo IP del nodo
RPC_PORT = 8332                   # Porta RPC del nodo

# ---------------------------
# Configurazione Wallet
# ---------------------------
WALLET_ADDRESS = "..."            # Indirizzo del wallet del miner

# ---------------------------
# Parametri Mining
# ---------------------------
DIFFICULTY_FACTOR = 10000000      # Fattore per modificare la difficoltà di mining
NONCE_MODE = "incremental"        # Modalità di aggiornamento del nonce:
                                  # "incremental"  -> incremento sequenziale
                                  # "random"       -> scelta casuale ad ogni iterazione
                                  # "mixed"        -> inizialmente casuale, poi incrementale
