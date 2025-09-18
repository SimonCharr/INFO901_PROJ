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
    
    # ========== SECTION CRITIQUE DISTRIBUÉE ==========
    
    def _start_token_management(self):
        """Démarre la gestion du jeton (appelé par le processus 0)"""
        def token_manager():
            sleep(0.5)  # Laisser le temps aux autres de se connecter
            next_id = (self.myId + 1) % self.getNbProcess()
            # Message système : pas d'impact sur l'horloge
            token_msg = MessageTo(self.myId, 0, 'TOKEN', next_id)
            print(f"🎯 P{self.myId}: lance le jeton initial")
            PyBus.Instance().post(token_msg)
        
        self.token_thread = Thread(target=token_manager)
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
                # Faire circuler le jeton
                self._pass_token()
    
    def _pass_token(self):
        """Fait circuler le jeton au processus suivant"""
        next_id = (self.myId + 1) % self.getNbProcess()
        token_msg = MessageTo(self.myId, 0, 'TOKEN', next_id)
        print(f"🔄 P{self.myId}: passe le jeton à P{next_id}")
        sleep(0.1) 
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
    
    @subscribe(threadMode=Mode.PARALLEL, onEvent=MessageTo)
    def _on_message_to_received(self, message):
        """Gestion des messages directs reçus"""
        if not hasattr(message, 'to') or message.to != self.myId:
            return
        
        # Vérifier si c'est un message système (jeton)
        if hasattr(message, 'payload') and message.payload == 'TOKEN':
            self._handle_token(message)
            return
        
        # Message utilisateur normal
        my_timestamp = self._update_clock_on_receive(message.timestamp)
        print(f"📨 P{self.myId}: reçoit '{message.payload}' de P{message.sender} (t={my_timestamp})")
        
        # Ajouter à la boîte aux lettres
        self.mailbox.addMessage(message)