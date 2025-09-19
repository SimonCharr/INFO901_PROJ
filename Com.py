# Com.py - Version sans variables de classe
import threading
from threading import Lock, Thread, Event, Semaphore
from time import sleep
import queue
import os
import tempfile
import json
from pyeventbus3.pyeventbus3 import *
from messages import (BroadcastMessage, MessageTo, SyncRequest, SyncRelease, 
                     BroadcastSyncMessage, SendToSyncMessage, SyncAckMessage)

class Mailbox:
    """
    Boîte aux lettres pour stocker les messages asynchrones
    """
    def __init__(self):
        self.messages = queue.Queue()
    
    def addMessage(self, message):
        """Ajoute un message à la boîte aux lettres"""
        self.messages.put(message)
    
    def getMessage(self):
        """Récupère le prochain message (bloquant si vide)"""
        return self.messages.get()
    
    def getMsg(self):
        """Alias pour getMessage()"""
        return self.getMessage()
    
    def isEmpty(self):
        """Vérifie si la boîte aux lettres est vide"""
        return self.messages.empty()

class Com:
    """
    Classe communicateur (middleware) qui gère:
    - Attribution automatique d'IDs sans variables de classe
    - Horloge de Lamport
    - Communication asynchrone et synchrone
    - Section critique distribuée
    - Synchronisation par barrière
    """
    
    def __init__(self):
        # Attribution automatique d'ID via fichier temporaire
        self.myId = self._get_next_process_id()
        
        # Découverte du nombre total de processus
        self.total_processes = self._discover_process_count()
        
        # Horloge de Lamport protégée par sémaphore
        self.lamport_clock = 0
        self.clock_semaphore = Semaphore(1)
        
        # Boîte aux lettres pour messages asynchrones
        self.mailbox = Mailbox()
        
        # Gestion du jeton pour section critique
        self.token_held = False
        self.request_pending = False
        self.token_event = Event()
        self.token_lock = Lock()
        
        # Synchronisation via fichier partagé
        self.sync_event = Event()
        self.sync_file_path = os.path.join(tempfile.gettempdir(), 'com_sync_counter.json')
        
        # Communication synchrone
        self.sync_comm_events = {}
        self.sync_comm_lock = Lock()
        
        # Thread pour gestion du jeton
        self.token_thread = None
        self.alive = True
        
        # S'enregistrer sur le bus
        PyBus.Instance().register(self, self)
        
        # Le processus 0 démarre le jeton après un délai
        if self.myId == 0:
            self._start_token_management()
        
        print(f"📋 P{self.myId}: Communicateur initialisé ({self.total_processes} processus)")
    
    def _get_next_process_id(self):
        """
        Attribution automatique d'ID sans variable de classe
        Utilise un fichier temporaire pour la coordination
        """
        id_file_path = os.path.join(tempfile.gettempdir(), 'com_process_counter.txt')
        
        # Lock sur fichier pour éviter les conflits
        lock_file_path = id_file_path + '.lock'
        
        # Attendre que le lock soit disponible
        while os.path.exists(lock_file_path):
            sleep(0.01)
        
        try:
            # Créer le lock
            with open(lock_file_path, 'w') as f:
                f.write('locked')
            
            # Lire le compteur actuel
            if os.path.exists(id_file_path):
                with open(id_file_path, 'r') as f:
                    current_id = int(f.read().strip())
            else:
                current_id = 0
            
            # Incrémenter et sauvegarder
            next_id = current_id + 1
            with open(id_file_path, 'w') as f:
                f.write(str(next_id))
            
            return current_id
            
        finally:
            # Libérer le lock
            if os.path.exists(lock_file_path):
                os.remove(lock_file_path)
    
    def _discover_process_count(self):
        """
        Découverte automatique du nombre de processus
        Utilise une variable d'environnement ou valeur par défaut
        """
        return int(os.environ.get('NB_PROCESSES', 3))
    
    def _get_sync_counter(self):
        """Lit le compteur de synchronisation depuis le fichier"""
        try:
            if os.path.exists(self.sync_file_path):
                with open(self.sync_file_path, 'r') as f:
                    data = json.load(f)
                return data.get('counter', 0)
            return 0
        except:
            return 0
    
    def _increment_sync_counter(self):
        """Incrémente le compteur de synchronisation dans le fichier"""
        lock_path = self.sync_file_path + '.lock'
        
        # Attendre le lock
        while os.path.exists(lock_path):
            sleep(0.01)
        
        try:
            # Créer le lock
            with open(lock_path, 'w') as f:
                f.write('locked')
            
            # Lire, incrémenter, écrire
            counter = self._get_sync_counter() + 1
            with open(self.sync_file_path, 'w') as f:
                json.dump({'counter': counter}, f)
            
            return counter
            
        finally:
            if os.path.exists(lock_path):
                os.remove(lock_path)
    
    def _reset_sync_counter(self):
        """Remet le compteur de synchronisation à zéro"""
        try:
            if os.path.exists(self.sync_file_path):
                os.remove(self.sync_file_path)
        except:
            pass
    
    def getNbProcess(self):
        """Retourne le nombre total de processus"""
        return self.total_processes
    
    def getMyId(self):
        """Retourne l'ID de ce processus"""
        return self.myId
    
    def inc_clock(self):
        """
        Méthode publique pour que le processus puisse incrémenter l'horloge
        """
        with self.clock_semaphore:
            self.lamport_clock += 1
            return self.lamport_clock
    
    def _increment_clock_internal(self):
        """Incrémentation interne de l'horloge (pour envoi de messages)"""
        with self.clock_semaphore:
            self.lamport_clock += 1
            return self.lamport_clock
    
    def _update_clock_on_receive(self, received_timestamp):
        """
        Met à jour l'horloge lors de la réception d'un message utilisateur
        """
        with self.clock_semaphore:
            self.lamport_clock = max(self.lamport_clock, received_timestamp) + 1
            return self.lamport_clock
    
    # ========== COMMUNICATION ASYNCHRONE ==========
    
    def broadcast(self, payload):
        """
        Diffuse un objet à tous les autres processus
        """
        timestamp = self._increment_clock_internal()
        message = BroadcastMessage(self.myId, timestamp, payload)
        print(f"📢 P{self.myId}: broadcast '{payload}' (t={timestamp})")
        PyBus.Instance().post(message)
    
    def sendTo(self, payload, dest):
        """
        Envoie un objet au processus de destination
        """
        timestamp = self._increment_clock_internal()
        message = MessageTo(self.myId, timestamp, payload, dest)
        print(f"📬 P{self.myId} → P{dest}: '{payload}' (t={timestamp})")
        PyBus.Instance().post(message)
    
    @subscribe(threadMode=Mode.PARALLEL, onEvent=BroadcastMessage)
    def _on_broadcast_received(self, message):
        """Gestion des messages de diffusion reçus"""
        if message.sender == self.myId:
            return  # Ignore ses propres messages
        
        # Met à jour l'horloge pour les messages utilisateur uniquement
        my_timestamp = self._update_clock_on_receive(message.timestamp)
        print(f"📻 P{self.myId}: reçoit broadcast '{message.payload}' de P{message.sender} (t={my_timestamp})")
        
        # Ajouter à la boîte aux lettres
        self.mailbox.addMessage(message)
    
    @subscribe(threadMode=Mode.PARALLEL, onEvent=MessageTo)
    def _on_message_to_received(self, message):
        """Gestion des messages directs reçus"""
        if not hasattr(message, 'to') or message.to != self.myId:
            return  # Pas pour nous
        
        # Vérifier si c'est un message système (jeton)
        if hasattr(message, 'payload') and message.payload == 'TOKEN':
            self._handle_token(message)
            return
        
        # Message utilisateur normal
        my_timestamp = self._update_clock_on_receive(message.timestamp)
        print(f"📨 P{self.myId}: reçoit '{message.payload}' de P{message.sender} (t={my_timestamp})")
        
        # Ajouter à la boîte aux lettres
        self.mailbox.addMessage(message)
    
    # ========== SECTION CRITIQUE DISTRIBUÉE ==========
    
    def _start_token_management(self):
        """Démarre la gestion du jeton (appelé par le processus 0)"""
        def token_manager():
            sleep(1.0)  # Laisser le temps aux autres de se connecter
            # Créer et envoyer le jeton initial seulement si personne ne l'a demandé
            next_id = (self.myId + 1) % self.getNbProcess()
            token_msg = MessageTo(self.myId, 0, 'TOKEN', next_id)
            print(f"🎯 P{self.myId}: lance le jeton initial")
            PyBus.Instance().post(token_msg)
        
        self.token_thread = Thread(target=token_manager, daemon=True)
        self.token_thread.start()
    
    def _handle_token(self, token_message):
        """Gestion de la réception du jeton"""
        with self.token_lock:
            if self.request_pending:
                # On attendait le jeton
                print(f"🔑 P{self.myId}: OBTIENT le jeton")
                self.token_held = True
                self.token_event.set()
            else:
                # Ne faire circuler le jeton que périodiquement pour éviter la surcharge
                self._pass_token_delayed()
    
    def _pass_token_delayed(self):
        """Fait circuler le jeton avec un délai pour éviter la surcharge"""
        def delayed_pass():
            sleep(0.2)  # Délai plus court
            # Toujours faire circuler le jeton, même si on a une demande pending
            # Car quelqu'un d'autre peut l'attendre
            next_id = (self.myId + 1) % self.getNbProcess()
            token_msg = MessageTo(self.myId, 0, 'TOKEN', next_id)
            # print(f"🔄 P{self.myId}: passe le jeton à P{next_id}")  # Debug si besoin
            PyBus.Instance().post(token_msg)
        
        Thread(target=delayed_pass, daemon=True).start()
    
    def _pass_token(self):
        """Fait circuler le jeton immédiatement"""
        next_id = (self.myId + 1) % self.getNbProcess()
        token_msg = MessageTo(self.myId, 0, 'TOKEN', next_id)
        print(f"🔄 P{self.myId}: passe le jeton à P{next_id}")
        PyBus.Instance().post(token_msg)
    
    def requestSC(self):
        """
        Demande l'accès à la section critique (bloquant)
        """
        print(f"🙋 P{self.myId}: demande la section critique")
        with self.token_lock:
            if self.token_held:
                return  # On a déjà le jeton
            self.request_pending = True
            self.token_event.clear()
        
        # Attendre le jeton
        self.token_event.wait()
        print(f"✅ P{self.myId}: section critique accordée")
    
    def releaseSC(self):
        """
        Libère la section critique
        """
        print(f"🔓 P{self.myId}: libère la section critique")
        with self.token_lock:
            self.token_held = False
            self.request_pending = False
            self.token_event.clear()
            self._pass_token()
    
    # ========== SYNCHRONISATION ==========
    
    def synchronize(self):
        """
        Synchronisation par barrière centralisée
        Tous les processus doivent appeler cette méthode pour continuer
        """
        print(f"⏸️ P{self.myId}: demande synchronisation")
        
        # Envoyer une demande de synchronisation au coordinateur (P0)
        if self.myId != 0:
            timestamp = self._increment_clock_internal()
            sync_msg = SyncRequest(self.myId, timestamp, 'SYNC_REQ', 0)
            PyBus.Instance().post(sync_msg)
        else:
            # P0 se compte lui-même
            self._handle_sync_request()
        
        # Attendre la libération
        self.sync_event.wait()
        self.sync_event.clear()
        print(f"▶️ P{self.myId}: synchronisation terminée")
    
    def _handle_sync_request(self):
        """Gestion des demandes de synchronisation (P0 uniquement)"""
        counter = self._increment_sync_counter()
        print(f"🔄 P0: {counter}/{self.getNbProcess()} processus synchronisés")
        
        if counter >= self.getNbProcess():
            # Tous les processus sont arrivés à la barrière
            print(f"✅ P0: libère la synchronisation")
            timestamp = self._increment_clock_internal()
            release_msg = SyncRelease(self.myId, timestamp, 'SYNC_RELEASE')
            PyBus.Instance().post(release_msg)
            self._reset_sync_counter()  # Reset pour la prochaine fois
    
    @subscribe(threadMode=Mode.PARALLEL, onEvent=SyncRequest)
    def _on_sync_request(self, message):
        """Réception des demandes de synchronisation"""
        if message.to != self.myId or self.myId != 0:
            return  # Seul P0 traite les demandes
        
        # Mettre à jour l'horloge
        self._update_clock_on_receive(message.timestamp)
        self._handle_sync_request()
    
    @subscribe(threadMode=Mode.PARALLEL, onEvent=SyncRelease)
    def _on_sync_release(self, message):
        """Réception du signal de libération de synchronisation"""
        # Mettre à jour l'horloge
        self._update_clock_on_receive(message.timestamp)
        self.sync_event.set()
    
    def _cleanup(self):
        """Nettoyage des ressources"""
        self.alive = False
        if self.token_thread and self.token_thread.is_alive():
            self.token_thread.join(timeout=1)
        PyBus.Instance().unregister(self)
        
        # Nettoyage des fichiers temporaires si on est le dernier
        if self.myId == 0:
            try:
                if os.path.exists(self.sync_file_path):
                    os.remove(self.sync_file_path)
            except:
                pass
    
    # ========== COMMUNICATION SYNCHRONE ==========
    
    def broadcastSync(self, payload, sender_id):
        """
        Communication synchrone par diffusion
        Si ce processus est l'expéditeur, diffuse et attend les accusés
        Sinon, attend de recevoir le message
        """
        if self.myId == sender_id:
            # Ce processus diffuse
            print(f"📢🔒 P{self.myId}: diffusion synchrone '{payload}'")
            
            # Créer les événements d'attente pour chaque destinataire
            ack_events = []
            for dest_id in range(self.getNbProcess()):
                if dest_id != self.myId:
                    event_key = f"broadcast_ack_{self.myId}_{dest_id}"
                    event = Event()
                    with self.sync_comm_lock:
                        self.sync_comm_events[event_key] = event
                    ack_events.append(event)
            
            # Envoyer le message
            timestamp = self._increment_clock_internal()
            sync_broadcast = BroadcastSyncMessage(self.myId, timestamp, payload, sender_id)
            PyBus.Instance().post(sync_broadcast)
            
            # Attendre tous les accusés de réception
            for event in ack_events:
                event.wait()
            
            print(f"✅ P{self.myId}: diffusion synchrone terminée")
        else:
            # Ce processus attend de recevoir
            event_key = f"broadcast_sync_{sender_id}"
            event = Event()
            with self.sync_comm_lock:
                self.sync_comm_events[event_key] = event
            
            print(f"⏳ P{self.myId}: attend diffusion synchrone de P{sender_id}")
            event.wait()
            print(f"📨 P{self.myId}: diffusion synchrone reçue de P{sender_id}")
    
    def sendToSync(self, payload, dest):
        """
        Envoi synchrone vers un destinataire spécifique
        Bloque jusqu'à ce que le destinataire reçoive
        """
        print(f"📬🔒 P{self.myId} → P{dest}: envoi synchrone '{payload}'")
        
        # Créer l'événement d'attente
        event_key = f"sendto_ack_{self.myId}_{dest}"
        event = Event()
        with self.sync_comm_lock:
            self.sync_comm_events[event_key] = event
        
        # Envoyer le message
        timestamp = self._increment_clock_internal()
        sync_msg = SendToSyncMessage(self.myId, timestamp, payload, dest)
        PyBus.Instance().post(sync_msg)
        
        # Attendre l'accusé de réception
        event.wait()
        print(f"✅ P{self.myId}: envoi synchrone vers P{dest} terminé")
    
    def recevFromSync(self, sender):
        """
        Réception synchrone depuis un expéditeur spécifique
        Bloque jusqu'à recevoir le message
        """
        print(f"⏳ P{self.myId}: attend réception synchrone de P{sender}")
        
        # Créer l'événement d'attente
        event_key = f"receive_sync_{sender}_{self.myId}"
        event = Event()
        with self.sync_comm_lock:
            self.sync_comm_events[event_key] = event
        
        # Attendre le message
        event.wait()
        print(f"📨 P{self.myId}: réception synchrone de P{sender} terminée")
    
    # ========== GESTIONNAIRES DES MESSAGES SYNCHRONES ==========
    
    @subscribe(threadMode=Mode.PARALLEL, onEvent=BroadcastSyncMessage)
    def _on_broadcast_sync_received(self, message):
        """Gestion des messages de diffusion synchrone"""
        if message.sender == self.myId:
            return  # Ignore ses propres messages
        
        # Mettre à jour l'horloge
        my_timestamp = self._update_clock_on_receive(message.timestamp)
        print(f"📻🔒 P{self.myId}: reçoit diffusion synchrone '{message.payload}' de P{message.sender}")
        
        # Ajouter à la boîte aux lettres
        self.mailbox.addMessage(message)
        
        # Déclencher l'événement d'attente
        event_key = f"broadcast_sync_{message.original_sender}"
        with self.sync_comm_lock:
            if event_key in self.sync_comm_events:
                self.sync_comm_events[event_key].set()
                del self.sync_comm_events[event_key]
        
        # Envoyer un accusé de réception
        ack_msg = SyncAckMessage(self.myId, 0, 'BROADCAST_ACK', message.original_sender)
        PyBus.Instance().post(ack_msg)
    
    @subscribe(threadMode=Mode.PARALLEL, onEvent=SendToSyncMessage)
    def _on_sendto_sync_received(self, message):
        """Gestion des messages d'envoi synchrone"""
        if message.to != self.myId:
            return  # Pas pour nous
        
        # Mettre à jour l'horloge
        my_timestamp = self._update_clock_on_receive(message.timestamp)
        print(f"📨🔒 P{self.myId}: reçoit envoi synchrone '{message.payload}' de P{message.sender}")
        
        # Ajouter à la boîte aux lettres
        self.mailbox.addMessage(message)
        
        # Déclencher l'événement d'attente pour recevFromSync
        event_key = f"receive_sync_{message.sender}_{self.myId}"
        with self.sync_comm_lock:
            if event_key in self.sync_comm_events:
                self.sync_comm_events[event_key].set()
                del self.sync_comm_events[event_key]
        
        # Envoyer un accusé de réception
        ack_msg = SyncAckMessage(self.myId, 0, 'SENDTO_ACK', message.sender)
        PyBus.Instance().post(ack_msg)
    
    @subscribe(threadMode=Mode.PARALLEL, onEvent=SyncAckMessage)
    def _on_sync_ack_received(self, message):
        """Gestion des accusés de réception synchrones"""
        if message.to != self.myId:
            return  # Pas pour nous
        
        print(f"✅ P{self.myId}: reçoit ACK de P{message.sender}")
        
        # Déclencher l'événement d'attente approprié
        if message.payload == 'BROADCAST_ACK':
            event_key = f"broadcast_ack_{self.myId}_{message.sender}"
        elif message.payload == 'SENDTO_ACK':
            event_key = f"sendto_ack_{self.myId}_{message.sender}"
        else:
            return
        
        with self.sync_comm_lock:
            if event_key in self.sync_comm_events:
                self.sync_comm_events[event_key].set()
                del self.sync_comm_events[event_key]