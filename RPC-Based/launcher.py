from __future__ import annotations

import argparse
import importlib
import logging
import multiprocessing as mp
import os
import re
import sys
import time
from typing import List

# ---------------------------------------------------------------------------
# SEZIONE CONFIGURABILE
# ---------------------------------------------------------------------------
PATTERNS = {
    # Stato periodico del miner – hashrate istantaneo & tentativi cumulativi
    # Esempio: "Stato mining - hashrate=452.53 kH/s tentativi=905300 ..."
    "status": re.compile(
        r"Stato mining - hashrate=([0-9.]+) kH/s tentativi=(\d+)"
    ),

    # Blocco trovato con dettagli (opzionale)
    "found_stats": re.compile(
        r"Blocco trovato - nonce=\d+ tentativi=(\d+) tempo=([0-9.]+)s hashrate=([0-9.]+) kH/s"
    ),

    # Blocco trovato senza dettagli (fallback)
    "found_simple": re.compile(r"Blocco trovato"),

    # Hash del blocco
    "hash": re.compile(r"Hash del blocco trovato: ([0-9a-fA-F]+)"),

    # Esito submit
    "submit": re.compile(r"Blocco accettato nella blockchain|submitblock ha restituito un errore"),
}

# ---------------------------------------------------------------------------
# PROCESSO WORKER
# ---------------------------------------------------------------------------

def _extranonce2(base: str, idx: int) -> str:
    """Restituisce `base + idx` in esadecimale, mantenendo la stessa larghezza."""
    return f"{int(base, 16) + idx:0{len(base)}x}"

def _worker(idx: int, base_ex2: str, q: mp.Queue):
    """Avvia un processo di mining e inoltra eventi strutturati al supervisore."""
    try:  # pin CPU (best‑effort)
        os.sched_setaffinity(0, {idx})
    except (AttributeError, OSError):
        pass

    # patch al modulo main
    main = importlib.import_module("main")
    main.EXTRANONCE2 = _extranonce2(base_ex2, idx)

    class _QueueHandler(logging.Handler):
        """Invia LogRecord significativi al processo padre via coda."""
        def emit(self, record: logging.LogRecord) -> None:  # noqa: D401
            msg = self.format(record)

            # --------------- metriche periodiche -----------------
            if m := PATTERNS["status"].search(msg):
                rate = float(m.group(1))
                attempts = int(m.group(2))
                q.put(("status", idx, {"rate": rate, "attempts": attempts}))
                return
            # --------------- blocco trovato ----------------------
            if m := PATTERNS["found_stats"].search(msg):
                attempts = int(m.group(1))
                t_sec = float(m.group(2))
                rate = float(m.group(3))
                q.put(("found", idx, {"attempts": attempts, "time": t_sec, "rate": rate}))
                return
            if PATTERNS["found_simple"].search(msg):
                q.put(("found", idx, None))
                return
            # --------------- hash / submit -----------------------
            if m := PATTERNS["hash"].search(msg):
                q.put(("hash", idx, m.group(1)))
                return
            if PATTERNS["submit"].search(msg):
                q.put(("submit", idx, None))
                return
            # tutti gli altri record vengono ignorati (niente log per‑worker)

    _fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    h = _QueueHandler(); h.setFormatter(_fmt)
    logging.basicConfig(level=logging.INFO, handlers=[h])

    try:
        main.main()
    except KeyboardInterrupt:
        pass

# ---------------------------------------------------------------------------
# SUPERVISORE
# ---------------------------------------------------------------------------

def _aggregate(q: mp.Queue, n: int) -> str:
    """Aggrega metriche da tutti i worker e riavvia dopo il submit."""
    rates = [0.0] * n
    attempts = [0] * n

    block_hash: str | None = None
    winner_idx: int | None = None
    winner_attempts: int | None = None

    t_start = time.time()
    last_print = t_start

    while True:
        try:
            tag, idx, val = q.get(timeout=0.5)

            if tag == "status":
                rates[idx] = val["rate"]
                attempts[idx] = val["attempts"]

            elif tag == "found":
                if isinstance(val, dict):
                    winner_idx = idx
                    winner_attempts = val["attempts"]
                    t_found = val["time"]
                    rate_local = val["rate"]
                    print(
                        f"\n[✓] Il worker {idx} ha trovato un blocco in {t_found:.2f}s "
                        f"dopo {winner_attempts:,} tentativi (rate {rate_local:.2f} kH/s). "
                        "In attesa di invio…"
                    )
                else:
                    print(f"\n[✓] Il worker {idx} ha trovato un blocco. In attesa di invio…")

            elif tag == "hash":
                block_hash = val

            elif tag == "submit":
                elapsed = time.time() - t_start
                total_attempts = sum(attempts)
                avg_rate_k = total_attempts / elapsed / 1000 if elapsed else 0.0
                print("\n" + "=" * 78)
                print(
                    f"[✓] Blocco inviato! hash={block_hash or 'N/D'}\n"
                    f"    • Tempo totale:       {elapsed:.1f} s\n"
                    f"    • Hashrate medio:     {avg_rate_k:,.2f} kH/s\n"
                    f"    • Tentativi totali:   {total_attempts:,}\n"
                    + (
                        f"    • Tentativi worker:   {winner_attempts:,} (worker {winner_idx})\n"
                        if winner_attempts is not None else ""
                    )
                )
                print("=" * 78)
                return "restart"
        except Exception:
            pass  # queue empty / timeout

        now = time.time()
        if now - last_print >= 1.0:  # stampa globale ogni secondo
            tot_rate = sum(rates)
            tot_attempts = sum(attempts)
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))
            sys.stdout.write(
                f"\r{ts} | INFO | miner | Stato mining - hashrate={tot_rate:,.2f} kH/s "
                f"tentativi={tot_attempts:,}   "
            )
            sys.stdout.flush()
            last_print = now

# ---------------------------------------------------------------------------
# CICLO DI AVVIO / RIAVVIO
# ---------------------------------------------------------------------------

def launch(n: int, base_ex2: str) -> None:
    # Visualizza l'extranonce2 che ogni processo utilizzerà nella coinbase (solo in debug)
    log = logging.getLogger(__name__)
    log.info("Extranonce2 utilizzati dai processi:")
    for i in range(n):
        extranonce2 = _extranonce2(base_ex2, i)
        log.info(f"  • Processo {i}: extranonce2={extranonce2}")
    
    while True:
        q: mp.Queue = mp.Queue()
        workers = [mp.Process(target=_worker, args=(i, base_ex2, q), daemon=True) for i in range(n)]
        for p in workers:
            p.start()

        try:
            reason = _aggregate(q, n)
        finally:
            for p in workers:
                if p.is_alive():
                    p.terminate()
            for p in workers:
                p.join()

        if reason != "restart":
            break
        print("\nRiavvio dei worker…\n")
        time.sleep(1)

# ---------------------------------------------------------------------------
# ENTRY‑POINT CLI
# ---------------------------------------------------------------------------
def _parse_args():
    # Importa l'EXTRANONCE2 da main.py come valore predefinito
    import main
    default_extranonce2 = main.EXTRANONCE2
        
    parser = argparse.ArgumentParser("Launcher multiprocesso per miner main.py")
    parser.add_argument("-n", "--num-procs", type=int, default=mp.cpu_count(), help="Numero di worker (default: CPU logiche)")
    parser.add_argument("--base-extranonce2", default=default_extranonce2, 
                        help=f"Base esadecimale per EXTRANONCE2 (default: {default_extranonce2})")
    return parser.parse_args()

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    log = logging.getLogger(__name__)
    log.info("Launcher avviato. Parametri e configurazione caricati correttamente.")
    
    # Importa i moduli necessari
    from rpc import connect_rpc, test_rpc_connection, get_block_template
    from block_builder import is_segwit_tx, decode_nbits
    import config
    
    # Inizializza multiprocessing
    mp.set_start_method("spawn", force=True)
    args = _parse_args()
    
    # Testa la connessione RPC
    test_rpc_connection()
    
    # Ottieni una connessione RPC e il template del blocco
    rpc_conn = connect_rpc()
    template = get_block_template(rpc_conn)
    
    if template:
        # Mostra informazioni sulle transazioni
        tot_tx = len(template["transactions"])
        witness_tx = sum(1 for tx in template["transactions"] if is_segwit_tx(tx["data"]))
        legacy_tx = tot_tx - witness_tx
        log.info(f"Transazioni nel template: totali = {tot_tx}  |  legacy = {legacy_tx}  |  segwit = {witness_tx}")
        
        # Mostra il messaggio nella coinbase
        log.info(f"Messaggio nella coinbase: {config.COINBASE_MESSAGE}")
        
        # Calcola e mostra il target modificato
        blockchain_info = rpc_conn.getblockchaininfo()
        network = blockchain_info.get("chain", "")
        difficulty_factor = float(config.DIFFICULTY_FACTOR)
        
        if network == "regtest":
            if difficulty_factor < 0:
                log.warning("DIFFICULTY_FACTOR deve essere >= 0. Impostazione a 0.1")
                difficulty_factor = 0.1
        else:  # testnet o mainnet
            difficulty_factor = 1.0
            log.info(f"Rete {network} rilevata: DIFFICULTY_FACTOR impostato a 1.0")
        
        nBits_int = int(template["bits"], 16)
        original_target = decode_nbits(nBits_int)
        
        if difficulty_factor == 0:
            modified_target = original_target
            log.info("DIFFICULTY_FACTOR = 0: utilizzo il target originale della rete")
        else:
            max_target = 0x00000000FFFF0000000000000000000000000000000000000000000000000000
            target_value = int(max_target / difficulty_factor)
            max_possible_target = (1 << 256) - 1
            if target_value > max_possible_target:
                target_value = max_possible_target
                log.warning("Target calcolato troppo grande. Limitato al massimo valore possibile.")
            modified_target = f"{target_value:064x}"
            log.info(f"Target modificato (difficoltà {difficulty_factor}): {modified_target}")
    
    # Mostra la modalità di mining
    log.info(f"Avvio mining - modalità {config.NONCE_MODE}")
    
    # Avvia il mining multiprocesso
    print(f"\nAvvio mining con {args.num_procs} processi (base extranonce2={args.base_extranonce2})\n")
    launch(args.num_procs, args.base_extranonce2)
    mp.set_start_method("spawn", force=True)
    args = _parse_args()
    print(f"\nAvvio mining con {args.num_procs} processi (base extranonce2={args.base_extranonce2})\n")

    # --- LOG aggiuntivi come richiesto ---
    try:
        import config
        import main
        log = logging.getLogger(__name__)
        # Simula ottenimento template e coinbase come in main.py
        template = getattr(main, "TEMPLATE", None)
        modified_target = getattr(main, "MODIFIED_TARGET", None)
        coinbase_message = getattr(config, "COINBASE_MESSAGE", None)
        if template and isinstance(template, dict) and "transactions" in template:
            tot_tx = len(template["transactions"])
            witness_tx = sum(1 for tx in template["transactions"] if tx.get("data", b"")[:2] == "00")
            legacy_tx = tot_tx - witness_tx
            log.info(f"Transazioni nel template: totali = {tot_tx}  |  legacy = {legacy_tx}  |  segwit = {witness_tx}")
        if coinbase_message:
            log.info(f"Messaggio nella coinbase: {coinbase_message}")
        if modified_target:
            log.info(f"Target modificato: {modified_target}")
    except Exception as e:
        logging.getLogger(__name__).warning(f"Impossibile stampare log aggiuntivi: {e}")

    launch(args.num_procs, args.base_extranonce2)
