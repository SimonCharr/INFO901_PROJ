# messages.py

class LamportMessage:
    """
    Classe de base pour tous les messages avec estampillage de Lamport
    Chaque message contient un expéditeur, un timestamp et un contenu
    """
    def __init__(self, sender, timestamp, payload):
        self.sender = sender        # ID du processus qui envoie
        self.timestamp = timestamp  # Horloge de Lamport au moment de l'envoi
        self.payload = payload      # Contenu du message (peut être n'importe quoi)
    
    def getSender(self):
        """Retourne l'ID de l'expéditeur"""
        return self.sender
    
    def getTimestamp(self):
        """Retourne le timestamp"""
        return self.timestamp
    
    def getPayload(self):
        """Retourne le contenu du message"""
        return self.payload

class BroadcastMessage(LamportMessage):
    """
    Message diffusé à tous les processus
    Hérite de LamportMessage, pas de champs supplémentaires nécessaires
    """
    pass

class MessageTo(LamportMessage):
    """
    Message destiné à un processus spécifique
    Ajoute un champ 'to' pour identifier le destinataire
    """
    def __init__(self, sender, timestamp, payload, to):
        super().__init__(sender, timestamp, payload)
        self.to = to  # ID du processus destinataire

class TokenMessage(MessageTo):
    """
    Message spécial pour le jeton (section critique)
    En pratique, on utilise directement MessageTo avec payload='TOKEN'
    """
    pass

# ========== Messages pour la synchronisation ==========

class SyncRequest(MessageTo):
    """
    Demande de synchronisation envoyée au coordinateur
    Utilisée dans le protocole de barrière centralisée
    """
    pass

class SyncRelease(BroadcastMessage):
    """
    Signal de libération de la synchronisation
    Diffusé par le coordinateur quand tous les processus sont prêts
    """
    pass

# ========== Messages pour la communication synchrone ==========

class BroadcastSyncMessage(LamportMessage):
    """
    Message de diffusion synchrone
    """
    def __init__(self, sender, timestamp, payload, original_sender):
        super().__init__(sender, timestamp, payload)
        self.original_sender = original_sender

class SendToSyncMessage(MessageTo):
    """
    Message d'envoi synchrone vers un destinataire spécifique
    """
    pass

class SyncAckMessage(MessageTo):
    """
    Accusé de réception pour la communication synchrone
    """
    def __init__(self, sender, timestamp, ack_type, to, original_sender=None):
        super().__init__(sender, timestamp, ack_type, to)
        self.original_sender = original_sender