"""
Modulo di configurazione per il nodo Bitcoin e il processo di mining.
Definisce le variabili necessarie per la connessione RPC, l'indirizzo del wallet,
il fattore di difficoltà e la modalità di calcolo del nonce.
"""

# ---------------------------
# Configurazione RPC
# ---------------------------
RPC_USER = "..."                         # Username per l'autenticazione RPC
RPC_PASSWORD = "..."                     # Password per l'autenticazione RPC
RPC_HOST = "127.0.0.1"                   # Indirizzo IP del nodo
RPC_PORT = 8332                         # Porta RPC del nodo

# ---------------------------
# Configurazione Wallet
# ---------------------------
WALLET_ADDRESS = "bcrt1qdyyh8r60u0fd82lrk9x52skh8j3jh0q3u66a66"                   # Indirizzo del wallet del miner

# ---------------------------
# Parametri Mining
# ---------------------------
DIFFICULTY_FACTOR = 0                    # Fattore per modificare la difficoltà di mining
NONCE_MODE = "mixed"                     # Modalità di aggiornamento del nonce:
                                         # "incremental"  -> incremento sequenziale
                                         # "random"       -> scelta casuale ad ogni iterazione
                                         # "mixed"        -> inizialmente casuale, poi incrementale
TIMESTAMP_UPDATE_INTERVAL = 30           # Intervallo in secondi per l'aggiornamento del timestamp durante il mining

# ---------------------------
# Messaggio Coinbase
# ---------------------------
COINBASE_MESSAGE = "/Ciao sono Davide/"  # Messaggio personalizzato da includere nella coinbase transaction
