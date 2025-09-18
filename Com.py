# Com.py
import threading
from threading import Lock, Thread, Event, Semaphore
from time import sleep
import queue
from pyeventbus3.pyeventbus3 import *
from messages import BroadcastMessage, MessageTo, SyncRequest, SyncRelease

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
    - Attribution automatique d'IDs
    - Horloge de Lamport
    - Communication asynchrone et synchrone
    - Section critique distribuée
    - Synchronisation par barrière
    """
    
    # Variables de classe pour la gestion des IDs (interdites selon le sujet)
    # On utilisera un fichier ou un mécanisme de découverte automatique
    _instance_counter = 0
    _counter_lock = Lock()
    _total_processes = 0
    _sync_counter = 0
    _sync_lock = Lock()
    
    def __init__(self):
        # Attribution automatique d'ID
        with Com._counter_lock:
            self.myId = Com._instance_counter
            Com._instance_counter += 1
        
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
        
        # Synchronisation
        self.sync_event = Event()
        
        # Thread pour gestion du jeton
        self.token_thread = None
        self.alive = True
        
        # S'enregistrer sur le bus
        PyBus.Instance().register(self, self)
        
        # Découverte automatique du nombre de processus
        self._discover_process_count()
        
        # Démarrer la gestion du jeton si c'est le premier processus
        if self.myId == 0:
            self._start_token_management()
    
    def _discover_process_count(self):
        """
        Mécanisme de découverte automatique du nombre de processus
        Pour simplifier, on utilise une variable d'environnement ou un fichier de config
        """
        # Pour cet exemple, on suppose 3 processus
        # Dans un vrai projet, on ferait de la découverte réseau
        Com._total_processes = 3
    
    def getNbProcess(self):
        """Retourne le nombre total de processus"""
        return Com._total_processes
    
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