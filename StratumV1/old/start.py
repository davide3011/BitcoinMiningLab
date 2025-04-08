import subprocess
import signal
import time
import logging
import sys

# Configurazione del logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Start")

# Lista dei processi avviati
processes = []

def start_process(script_name):
    """Avvia un processo e stampa direttamente l'output nel terminale."""
    logger.info(f"Avviando {script_name}...")
    process = subprocess.Popen(
        [sys.executable, script_name],  # Usa Python corretto
        stdout=None,  # Permette la visualizzazione immediata
        stderr=None,  # Stampa anche gli errori nel terminale
        text=True
    )
    processes.append(process)
    return process

def terminate_processes():
    """Termina tutti i processi avviati."""
    logger.info("Terminazione di tutti i processi...")
    for process in processes:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
    logger.info("Tutti i processi sono stati terminati.")

def signal_handler(sig, frame):
    """Gestisce il segnale di interruzione (CTRL+C)."""
    logger.info("CTRL+C rilevato. Arresto dei processi...")
    terminate_processes()
    exit(0)

if __name__ == "__main__":
    # Imposta il gestore del segnale per la chiusura con CTRL+C
    signal.signal(signal.SIGINT, signal_handler)

    print("Avvio del mining...")
    
    # Avvia il client Stratum
    client_process = start_process("stratum_client.py")
    time.sleep(2)  # Attendi che il client si connetta

    # Avvia il miner
    miner_process = start_process("miner.py")

    # Attendi che i processi terminino
    try:
        client_process.wait()
        miner_process.wait()
    except KeyboardInterrupt:
        signal_handler(None, None)
