import socket, time, logging, json, os, threading

# -------------------- Configurazione del Logger --------------------
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("StratumClient")

# -------------------- Funzione per Caricare la Configurazione --------------------
def load_config():
    """Carica la configurazione dal file `conf.json`."""
    config_file = "conf.json"
    if not os.path.exists(config_file):
        logger.error(f"? Config file `{config_file}` not found!")
        raise FileNotFoundError(f"{config_file} not found!")
    with open(config_file, "r") as f:
        return json.load(f)

config = load_config()

# -------------------- Parametri dal File di Configurazione --------------------
HOST = config["pool_host"]
PORT = config["pool_port"]
USERNAME = config["username"]
PASSWORD = config["password"]
USER_AGENT = config.get("user_agent", "Miner/1.0")
RECONNECT_DELAY = config.get("reconnect_delay", 5)
JOB_TIMEOUT = config.get("job_timeout", 60)

# -------------------- Variabili Globali --------------------
sock = None
connected = False
stop_flag = False
buffer = b""
extranonce1 = None
extranonce2_size = None
last_job_time = 0
lock = threading.Lock()  # Lock per la gestione sicura della connessione

# -------------------- Funzioni di Connessione e Comunicazione --------------------
def connect_to_pool():
    """Crea la connessione TCP con il pool e gestisce le riconnessioni."""
    global sock, connected
    with lock:
        while not connected and not stop_flag:
            try:
                logger.info(f"Connecting to {HOST}:{PORT}...")
                sock = socket.create_connection((HOST, PORT), timeout=60)
                connected = True
                logger.info("Connection established successfully.")
            except Exception as e:
                logger.error(f"Connection error: {e}. Retrying in {RECONNECT_DELAY} seconds.")
                time.sleep(RECONNECT_DELAY)
                
def send_message(message_dict):
    """Invia un messaggio JSON al pool."""
    global sock, connected
    if not connected:
        logger.warning("Not connected. Attempting reconnection...")
        connect_to_pool()
    
    try:
        message_json = json.dumps(message_dict) + "\n"
        sock.sendall(message_json.encode("utf-8"))
        logger.debug(f"Sent: {message_json.strip()}")
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        connected = False
        connect_to_pool()
        
def receive_messages():
    """Riceve continuamente i messaggi dal pool e li processa."""
    global sock, buffer, connected
    while not stop_flag:
        try:
            if not connected:
                connect_to_pool()
            data = sock.recv(4096)
            if not data:
                logger.warning("Connection closed by the server.")
                connected = False
                connect_to_pool()
                continue
            buffer += data
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                if line:
                    try:
                        message = json.loads(line.decode("utf-8"))
                        handle_message(message)
                    except json.JSONDecodeError:
                        logger.error("Error decoding JSON message.")
        except Exception as e:
            logger.error(f"Error receiving message: {e}")
            connected = False
            connect_to_pool()
        
def handle_message(message):
    """Gestisce i messaggi ricevuti dal pool."""
    global extranonce1, extranonce2_size, last_job_time, connected

    logger.info(f"Message received: {json.dumps(message, indent=4)}")

    if "id" in message:
        if message["id"] == 1 and "result" in message:
            extranonce1, extranonce2_size = message["result"][1:3]
            logger.info(f"Subscription successful. Extranonce1: {extranonce1}, Extranonce2_size: {extranonce2_size}")

        elif message["id"] == 2 and "result" in message:
            if message["result"]:
                logger.info("Authorization successful. Miner ready.")
                connected = True
            else:
                logger.error("Authorization failed! Check username/password.")
                connected = False

    if message.get("method") == "mining.notify":
        logger.info("New job received!")
        save_job_data(message["params"])   
        
# -------------------- Funzioni di Salvataggio del Job --------------------

def save_job_data(job_data):
    """Salva i dati del job ricevuto in `job.json`, sovrascrivendo il file esistente."""
    global last_job_time, extranonce1, extranonce2_size

    if not isinstance(job_data, list) or len(job_data) < 9:
        logger.error(f"Invalid job data! Received: {job_data}")
        return

    job_dict = {
        "job_id": job_data[0],
        "prevhash": job_data[1],
        "coinbase1": job_data[2],
        "coinbase2": job_data[3],
        "merkle_branch": job_data[4],
        "version": job_data[5],
        "nbits": job_data[6],
        "ntime": job_data[7],
        "clean_jobs": job_data[8],
        "extranonce1": extranonce1,
        "extranonce2_size": extranonce2_size
    }

    with open("job.json", "w") as f:
        json.dump(job_dict, f, indent=4)

    last_job_time = time.time()
    logger.info(f"Job received and saved at {time.ctime(last_job_time)}.")
        
# -------------------- Inviare le Richieste --------------------

def subscribe():
    """Invia il messaggio di iscrizione al pool."""
    send_message({"id": 1, "method": "mining.subscribe", "params": [USER_AGENT]})

def authorize():
    """Invia il messaggio di autorizzazione al pool."""
    send_message({"id": 2, "method": "mining.authorize", "params": [USERNAME, PASSWORD]})

# -------------------- Funzione Principale --------------------

def main():
    """Avvia il client Stratum."""
    global last_job_time

    logger.info("Starting Stratum Client...")

    connect_to_pool()
    threading.Thread(target=receive_messages, daemon=True).start()

    subscribe()
    time.sleep(1)
    authorize()

    try:
        while True:
            time.sleep(5)
            if not connected:
                logger.warning("Disconnection detected! Attempting reconnection...")
                connect_to_pool()
                subscribe()
                time.sleep(1)
                authorize()
    except KeyboardInterrupt:
        logger.info("Terminating connection...")
        if sock:
            sock.close()
            logger.info("Connection closed.")

if __name__ == "__main__":
    main()
        
        
