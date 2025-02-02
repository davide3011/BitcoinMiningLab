# BitcoinMiningLab

## Panoramica

Il repository è strutturato in modo modulare per facilitare:
- L'interazione con nodi Bitcoin tramite API RPC.
- La costruzione e validazione di template per la creazione di blocchi.
- La ricerca del nonce corretto e la serializzazione dei blocchi.

**Nota:** Per una descrizione dettagliata del processo RPC (connessione al nodo, costruzione del template, ricerca del nonce, serializzazione e invio del blocco) consulta il README specifico all'interno della cartella [RPC-Based](RPC-Based/README.md).

## Struttura del Repository

- **RPC-Based**  
  Contiene lo script che gestisce l'interazione RPC con il nodo Bitcoin. Tutti i dettagli tecnici e le istruzioni per l'uso si trovano nel README presente in questa cartella.

- **Stratum**  
  Implementazione del protocollo Stratum per il mining Bitcoin. **Attualmente in sviluppo.**  
  Qui verrà fornita una documentazione dettagliata e un README dedicato non appena il lavoro sarà completato.

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
2. **Installa le dipendenze:**
```bash
pip install -r requirements.txt
```
## Licenza
Distribuito sotto la licenza MIT.




   
