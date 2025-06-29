from bitcoinrpc.authproxy import AuthServiceProxy
import config
import logging
from typing import Tuple, Optional

# Questo modulo gestisce la comunicazione con il nodo Bitcoin tramite chiamate RPC (Remote Procedure Call)
# Fornisce funzioni per ottenere dati dalla blockchain, richiedere template di blocchi e inviare blocchi minati

log = logging.getLogger(__name__)

def connect_rpc():
    """
    Crea una connessione RPC al nodo Bitcoin utilizzando le credenziali configurate.
    
    Returns:
        AuthServiceProxy: Un oggetto proxy che permette di effettuare chiamate RPC al nodo Bitcoin
        
    Note:
        Le chiamate RPC (Remote Procedure Call) permettono di comunicare con un nodo Bitcoin
        e di accedere alle sue funzionalità come se fossero funzioni locali.
        Le credenziali di autenticazione sono prese dal modulo config.
    """
    return AuthServiceProxy(f"http://{config.RPC_USER}:{config.RPC_PASSWORD}@{config.RPC_HOST}:{config.RPC_PORT}")


def get_block_template(rpc):
    """
    Richiede un template di blocco al nodo Bitcoin con supporto per le regole SegWit.
    
    Args:
        rpc: Connessione RPC al nodo Bitcoin
        
    Returns:
        dict: Template del blocco contenente transazioni, target di difficoltà e altri metadati,
              oppure None in caso di errore
        
    Note:
        Il template del blocco contiene tutte le informazioni necessarie per costruire un blocco valido:
        - Transazioni da includere nel blocco
        - Hash del blocco precedente
        - Difficoltà target
        - Altezza del blocco
        - Timestamp corrente
        - Valore della ricompensa (coinbase)
        
        Specificando "segwit" nelle regole, richiediamo un template compatibile con
        Segregated Witness (BIP141), che permette di includere transazioni SegWit nel blocco.
    """
    try:
        # Richiede il template specificando il supporto per SegWit
        tpl = rpc.getblocktemplate({"rules": ["segwit"]})
        log.debug("Template ricevuto - altezza %d, %d tx",
                  tpl.get("height"), len(tpl["transactions"]))
        return tpl
    except Exception as e:
        # Gestisce eventuali errori durante la richiesta
        log.error("Errore RPC getblocktemplate: %s", e)
        return None
