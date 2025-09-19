# Middleware Com - Communication Distribuée

Implémentation d'un middleware Python pour la communication entre processus distribués.

## Vue d'ensemble

Le middleware `Com` sépare clairement les fonctionnalités de communication du code applicatif des processus. Chaque processus instancie un communicateur qui gère automatiquement l'attribution d'ID, l'horloge de Lamport, et tous les mécanismes de communication.

## Attribution automatique d'IDs

La classe `Com` attribue automatiquement des IDs consécutifs (0, 1, 2...) sans utiliser de variables de classe.

- `_get_next_process_id()` : Utilise un fichier temporaire avec système de verrous pour coordination
- `_discover_process_count()` : Lit le nombre total depuis une variable d'environnement
- `getNbProcess()` et `getMyId()` : Méthodes d'accès publiques

## Horloge de Lamport

L'horloge de Lamport est implémentée avec protection par sémaphore pour garantir la thread-safety.

- `inc_clock()` : Méthode publique permettant au processus d'incrémenter l'horloge
- `_increment_clock_internal()` : Incrémentation automatique lors de l'envoi de messages
- `_update_clock_on_receive()` : Mise à jour selon la règle max(local, reçu) + 1
- Protection par `clock_semaphore` pour éviter les accès concurrents

## Boîte aux lettres

La classe `Mailbox` fournit une interface thread-safe pour stocker les messages asynchrones.

- `addMessage()` : Ajout de messages dans une `Queue` Python
- `getMessage()` / `getMsg()` : Récupération bloquante des messages
- `isEmpty()` : Vérification de l'état de la boîte
- Tous les messages utilisateur sont automatiquement stockés pour consultation

## Communication asynchrone

Implémentation des méthodes demandées dans le sujet pour la communication non-bloquante.

- `broadcast(payload)` : Diffuse un objet à tous les autres processus
- `sendTo(payload, dest)` : Envoie un objet au processus spécifié
- `_on_broadcast_received()` : Gestionnaire automatique des messages de diffusion
- `_on_message_to_received()` : Gestionnaire avec filtrage par destinataire

## Section critique distribuée

Le système utilise un jeton circulant géré par un thread séparé.

- `requestSC()` : Demande bloquante d'accès à la section critique
- `releaseSC()` : Libération et transmission du jeton au processus suivant
- `_handle_token()` : Logique de décision (garder ou faire circuler le jeton)
- `_start_token_management()` : Thread dédié lancé par le processus 0
- Le jeton (messages TOKEN) est traité comme message système et n'impacte pas l'horloge

## Synchronisation par barrière

Mécanisme centralisé où tous les processus doivent appeler la méthode pour débloquer l'ensemble.

- `synchronize()` : Méthode bloquante publique
- `_handle_sync_request()` : Comptage des processus arrivés (P0 coordinateur)
- `_increment_sync_counter()` : Compteur partagé via fichier JSON avec verrous
- Utilise les messages `SyncRequest` et `SyncRelease` pour la coordination

## Communication synchrone

Implémentation des trois méthodes demandées avec mécanisme d'accusés de réception.

- `broadcastSync(payload, sender_id)` : L'expéditeur diffuse et attend tous les ACK
- `sendToSync(payload, dest)` : Envoi avec attente d'accusé du destinataire  
- `recevFromSync(sender)` : Réception bloquante depuis un expéditeur spécifique
- Utilise des `Event` Python et des messages `SyncAckMessage` pour la synchronisation

## Gestion des messages

Distinction claire entre messages système et utilisateur :

- **Messages utilisateur** : Impactent l'horloge de Lamport (BroadcastMessage, MessageTo)
- **Messages système** : timestamp=0, pas d'effet sur l'horloge (TOKEN, ACK)
- Hiérarchie de classes héritant de `LamportMessage` pour l'estampillage

## Architecture technique

### Thread-safety
Toutes les structures partagées sont protégées :
- Sémaphore pour l'horloge de Lamport
- Locks pour les événements de communication synchrone
- Queue thread-safe pour la mailbox

### PyEventBus
Utilisation du pattern publish/subscribe pour le transport des messages entre processus avec mode `PARALLEL` pour le traitement concurrent.

### Fichiers temporaires
Remplacement des variables de classe par des fichiers avec verrous pour la coordination (IDs, compteurs de synchronisation).

## Tests

```bash
# Test standard (3 processus par défaut)
python3 launcher.py

# Test avec nombre personnalisé
NB_PROCESSES=4 python3 launcher.py

# Exemple applicatif (jeu de dés)
python3 DiceGame.py
```

Les tests valident toutes les fonctionnalités : communication asynchrone et synchrone, section critique, synchronisation, horloge de Lamport, et attribution d'IDs.

## Installation

```bash
pip install pyeventbus3
```