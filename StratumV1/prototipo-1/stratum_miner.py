"""Server Stratum V1 minimale che invia un job pre-generato (job.json)
   e salva ogni share ricevuta in un file JSON **nella directory corrente**.

   Flusso:
   - mining.subscribe ? mining.set_difficulty ? mining.notify
   - accetta mining.authorize senza autentica reale
   - persiste share_<timestamp>.json nella cwd

   Avvio:
       python stratum_json_server.py [--host 0.0.0.0] [--port 3333]
"""

import argparse
import json
import logging
import os
import socket
import threading
import time
from datetime import datetime
from main import EXTRANONCE1

# ----------------------------------------------------------------
#  Configurazione
# ----------------------------------------------------------------
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 3333
DIFF         = 1000                     # difficoltà share fissa

EXTRANONCE2_SIZE = 4                 # byte di extranonce2
JOB_JSON     = "job.json"            # job da inviare
SHARE_DIR    = "."                  # directory corrente

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)s | %(threadName)s | %(message)s")
log = logging.getLogger("StratumJSON")

# la cwd esiste sempre, ma manteniamo la chiamata per simmetria
os.makedirs(SHARE_DIR, exist_ok=True)


# ----------------------------------------------------------------
#  Utility
# ----------------------------------------------------------------

def send_json(conn_file, obj):
    """Invia un JSON + newline."""
    conn_file.write((json.dumps(obj) + "\n").encode("utf-8"))
    conn_file.flush()


def load_job(path: str = JOB_JSON):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_share(params: list[str]):
    """Salva i parametri di mining.submit in solution.json nella cwd."""
    if len(params) < 5:
        return
    share = {
        "worker":      params[0],
        "job_id":      params[1],
        "extranonce2": params[2],
        "ntime":       params[3],
        "nonce":       params[4],
        "received_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    fname = os.path.join(SHARE_DIR, "solution.json")
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(share, f, indent=2)
    log.info("Share salvata in %s", fname)
    
# ----------------------------------------------------------------
#  Gestione client
# ----------------------------------------------------------------

def handle_client(conn: socket.socket, addr):
    log.info("Miner connesso da %s:%d", *addr)
    conn_file = conn.makefile("rwb")
    try:
        # 1) subscribe
        line = conn_file.readline().decode("utf-8")
        if not line:
            raise ConnectionError("Connessione chiusa in subscribe")
        msg = json.loads(line.strip())
        if msg.get("method") != "mining.subscribe":
            raise ConnectionError("Primo msg non è mining.subscribe")
        
        sub_resp = {
            "id": msg.get("id"),
            "result": [
                [["mining.set_difficulty", "diff_sub"], ["mining.notify", "job_sub"]],
                EXTRANONCE1, # big-endian
                EXTRANONCE2_SIZE,
            ],
            "error": None,
        }
        send_json(conn_file, sub_resp)

        # 2) authorize/configure loop
        while True:
            line = conn_file.readline().decode("utf-8")
            if not line:
                raise ConnectionError("Disconnessione prima di authorize")
            msg = json.loads(line.strip())
            method = msg.get("method")
            if method == "mining.configure":
                send_json(conn_file, {"id": msg.get("id"), "result": {"version-rolling": True}, "error": None})
                continue
            if method == "mining.authorize":
                send_json(conn_file, {"id": msg.get("id"), "result": True, "error": None})
                break

        # 3) invio job
        send_json(conn_file, {"id": None, "method": "mining.set_difficulty", "params": [DIFF]})
        job = load_job()
        notify = {
            "id": None,
            "method": "mining.notify",
            "params": [
                job["job_id"], job["prevhash"], job["coinb1"], job["coinb2"],
                job["merkle_branch"], job["version"], job["nbits"], job["ntime"], job["clean_jobs"],
            ],
        }
        send_json(conn_file, notify)
        log.info("Job %s inviato", job["job_id"])

        # 4) ciclo submit
        while True:
            line = conn_file.readline().decode("utf-8")
            if not line:
                log.info("Miner %s disconnesso", addr)
                break
            msg = json.loads(line.strip())
            if msg.get("method") == "mining.submit":
                params = msg.get("params", [])
                save_share(params)
                send_json(conn_file, {"id": msg.get("id"), "result": True, "error": None})
            else:
                log.debug("Msg ignorato: %s", msg)

    except Exception as e:
        log.warning("Connessione interrotta: %s", e)
    finally:
        try:
            conn_file.close()
            conn.close()
        except Exception:
            pass

# ----------------------------------------------------------------
#  Main
# ----------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description="Server Stratum V1 con job statico JSON")
    p.add_argument("--host", default=DEFAULT_HOST, help="Bind address")
    p.add_argument("--port", type=int, default=DEFAULT_PORT, help="Porta di ascolto")
    args = p.parse_args()

    if not os.path.isfile(JOB_JSON):
        raise SystemExit(f"File {JOB_JSON} mancante.")

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((args.host, args.port))
    srv.listen()
    log.info("Server in ascolto su %s:%d", args.host, args.port)

    try:
        while True:
            conn, addr = srv.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        log.info("Shutdown per CTRL+C...")
    finally:
        srv.close()

if __name__ == "__main__":
    main()













