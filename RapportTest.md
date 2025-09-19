# Rapport de test - Middleware de communication distribuée

**Nom :** Charrier Simon
**Matière :** INFO901

## 1. Introduction

Ce rapport présente les tests effectués sur l'implémentation d'un middleware de communication distribuée développé en Python. Le middleware, implémenté dans la classe `Com`, fournit des services de communication asynchrone et synchrone, de section critique distribuée, et de synchronisation par barrière pour des processus distribués.

## 2. Architecture testée

### 2.1 Composants principaux

- **Classe Com** : Middleware de communication principal
- **Classe Mailbox** : Gestion des messages asynchrones avec Queue thread-safe  
- **Messages Lamport** : Hiérarchie de classes pour l'estampillage temporel
- **PyEventBus** : Bus de messages pour la communication inter-processus

### 2.2 Fonctionnalités implémentées

- Attribution automatique d'IDs de processus (0, 1, 2...)
- Horloge de Lamport avec sémaphore pour la cohérence temporelle
- Communication asynchrone (broadcast, sendTo) 
- Section critique distribuée par jeton circulant
- Synchronisation par barrière centralisée
- Communication synchrone avec accusés de réception
- Boîte aux lettres pour stockage des messages

## 3. Méthodologie de test

### 3.1 Environnement de test

- **Langage** : Python 3
- **Dépendances** : pyeventbus3
- **Système** : Linux (algoDist environment)
- **Configuration** : 3 processus par défaut (P0, P1, P2)

### 3.2 Types de tests effectués

1. **Test systématique** (`launcher.py`) : Validation séquentielle de chaque fonctionnalité
2. **Test applicatif** (`DiceGame.py`) : Scénario réaliste reproduisant l'exemple du sujet
3. **Tests de robustesse** : Différents nombres de processus et durées

## 4. Résultats des tests

### 4.1 Test systématique (launcher.py)

#### Phase 1 : Communication asynchrone ✅
```
📢 P0: broadcast 'Hello tout le monde !' (t=1)
📻 P1: reçoit broadcast 'Hello tout le monde !' de P0 (t=2)  
📻 P2: reçoit broadcast 'Hello tout le monde !' de P0 (t=2)
```

**Observations :** 
- L'horloge de Lamport fonctionne correctement (incrémentation à l'envoi, maj à la réception)
- Les messages sont bien diffusés à tous les processus destinataires
- La mailbox stocke correctement les messages pour lecture ultérieure

#### Phase 2 : Section critique distribuée ✅
```
🙋 P2: demande la section critique
🔑 P2: OBTIENT le jeton
🔥 P2: TRAVAILLE en section critique  
🔓 P2: libère la section critique
🔄 P2: passe le jeton à P0
```

**Observations :**
- L'exclusion mutuelle est respectée : un seul processus en section critique
- Le jeton circule correctement en anneau (P0→P1→P2→P0)
- Les demandes séquentielles sont bien gérées
- Pas de deadlock observé lors de demandes simultanées

#### Phase 3 : Synchronisation par barrière ✅
```
🔄 P0: 1/3 processus synchronisés
🔄 P0: 2/3 processus synchronisés  
🔄 P0: 3/3 processus synchronisés
✅ P0: libère la synchronisation
```

**Observations :**
- La barrière centralisée fonctionne avec P0 comme coordinateur
- Tous les processus attendent que le dernier arrive
- La libération est simultanée pour tous

#### Phase 4 : Horloge de Lamport ✅
```
🕒 P1: horloge 8 → 9
📬 P1 → P0: 'Test horloge' (t=10)
📨 P0: reçoit 'Test horloge' de P1 (t=11)
```

**Observations :**
- L'incrémentation manuelle fonctionne via `inc_clock()`
- La mise à jour automatique respecte max(local, reçu) + 1
- La cohérence temporelle est préservée

#### Phase 5 : Communication synchrone ✅
```
📢🔒 P0: diffusion synchrone 'Message synchrone de P0'
📻🔒 P1: reçoit diffusion synchrone 'Message synchrone de P0' de P0
✅ P0: reçoit ACK de P1
✅ P0: reçoit ACK de P2  
✅ P0: diffusion synchrone terminée
```

**Observations :**
- Le mécanisme d'accusé de réception fonctionne
- L'expéditeur attend bien tous les ACK avant de continuer
- Pas de deadlock dans la communication synchrone

### 4.2 Test applicatif (DiceGame.py)

#### Scénario du jeu de dés
Le test reproduit le scénario donné dans le sujet avec communication inter-processus puis compétition pour la section critique.

```
=== P0 démarre le jeu ===
📬 P0 → P1: 'j'appelle 2 et je te recontacte après' (t=1)
📧 P1: Lu message de P0: 'j'appelle 2 et je te recontacte après'
💬 P2: Répond à P0  
📬 P2 → P0: 'OK, je suis prêt pour la partie !' (t=4)
```

**Phase de jeu :**
```
🎯 P0: Début de la partie - synchronisation
⏸️ P0: demande synchronisation
🎲 P2: Demande l'accès au dé
🔑 P2: OBTIENT le jeton
🎉 P2: J'ai gagné ! Dé = 4
😞 P0: P2 a eu le jeton en premier
😞 P1: P2 a eu le jeton en premier
```

**Observations :**
- Le scénario complexe fonctionne de bout en bout
- La coordination entre communication asynchrone et synchronisation est correcte
- La compétition pour la section critique produit un gagnant aléatoire
- Les autres processus détectent correctement qu'ils ont perdu

### 4.3 Tests de robustesse

#### Test avec 4 processus
```bash
NB_PROCESSES=4 python3 launcher.py
```
**Résultat :** Attribution correcte des IDs (0,1,2,3), jeton circule sur les 4 processus

#### Test de durée étendue  
**Résultat :** Aucune fuite mémoire détectée, nettoyage automatique des fichiers temporaires