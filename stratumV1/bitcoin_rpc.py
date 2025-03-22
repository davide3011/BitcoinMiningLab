# bitcoin_rpc.py
# Modulo per la gestione delle connessioni RPC al nodo Bitcoin

from bitcoinrpc.authproxy import AuthServiceProxy
import config

def connect_rpc():
    """
    Crea una connessione RPC al nodo Bitcoin utilizzando i parametri di configurazione.
    
    Returns:
        AuthServiceProxy: Un'istanza del proxy per le chiamate RPC.
    """
    connection_url = f"http://{config.RPC_USER}:{config.RPC_PASSWORD}@{config.RPC_HOST}:{config.RPC_PORT}"
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
    connection_url = f"http://{config.RPC_USER}:{config.RPC_PASSWORD}@{config.RPC_HOST}:{config.RPC_PORT}"
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