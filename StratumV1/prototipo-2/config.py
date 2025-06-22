"""
Modulo di configurazione.
Definisce le variabili necessarie per la connessione RPC, 
l'indirizzo del wallet e il fattore di difficoltà.
"""

# ---------------------------
# Configurazione RPC
# ---------------------------
RPC_USER = "..."                         # Username per l'autenticazione RPC
RPC_PASSWORD = "..."                     # Password per l'autenticazione RPC
RPC_HOST = "127.0.0.1"                   # Indirizzo IP del nodo
RPC_PORT = 18443                         # Porta RPC del nodo

# ---------------------------
# Configurazione Wallet
# ---------------------------
WALLET_ADDRESS = "..."                   # Indirizzo del wallet del miner

# ---------------------------
# Parametri Mining
# ---------------------------
DIFFICULTY_FACTOR = 0                    # Fattore per modificare la difficoltà di mining

TIMESTAMP_UPDATE_INTERVAL = 30           # Intervallo in secondi per l'aggiornamento del timestamp durante il mining

# ---------------------------
# Messaggio Coinbase
# ---------------------------
COINBASE_MESSAGE = "/Ciao sono Davide/"  # Messaggio personalizzato da includere nella coinbase transaction
