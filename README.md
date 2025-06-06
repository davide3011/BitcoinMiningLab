# BitcoinMiningLab

## Panoramica

Questo repository è dedicato allo sviluppo, allo studio e all'implementazione pratica dei principali protocolli di mining Bitcoin. La struttura è modulare per facilitare:

- Interazione con nodi Bitcoin tramite API RPC.

- Implementazione del protocollo Stratum V1 (server e client).

- Costruzione di strumenti e script mirati per operazioni specifiche come la generazione della coinbase e del merkle branch.

## Struttura del Repository

- **GetBlockTemplate**: Contiene un programma completo che interagisce con il nodo Bitcoin tramite RPC:

   - Richiesta del block template (getblocktemplate).

   - Costruzione e serializzazione del blocco.

   - Ricerca del nonce e invio al nodo.

Consulta il README all'interno della cartella per dettagli tecnici approfonditi e istruzioni d'uso.

- **Stratum-V1** (in sviluppo): Implementazione completa del protocollo Stratum V1, che include:

   - Server Stratum per fornire lavoro ai miner e ricevere submission valide.

   - Client Stratum per simulare il comportamento di un miner.

Documentazione e dettagli tecnici saranno resi disponibili man mano che il progetto progredisce.

- **MiningUtils**: Contiene script specifici e modulari utili per diverse fasi del mining, tra cui:

   - Costruzione corretta della transazione coinbase conforme al protocollo Stratum.

   - Generazione del merkle branch per il job Stratum.

## Prerequisiti

Assicurati di avere installato:
- Python 3.9+
- Dipendenze elencate nel file `requirements.txt`
- Accesso a un nodo Bitcoin configurato per accettare connessioni RPC

## Installazione

1. **Clona il repository:**
   ```bash
   git clone https://github.com/davide3011/BitcoinMiningLab.git
   cd BitcoinMiningLab
   ```
2. **Installa le dipendenze:**+
```bash
pip install -r requirements.txt
```
## Licenza

Distribuito sotto la licenza MIT.




   
