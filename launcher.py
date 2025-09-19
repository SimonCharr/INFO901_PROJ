# Launcher.py - Version sans warnings de dépréciation
import os
from time import sleep
from threading import Thread
from Com import Com

class Process(Thread):
    """
    Processus utilisant le middleware Com pour toutes les communications
    """
    
    def __init__(self, name):
        Thread.__init__(self)
        
        # Créer le communicateur (middleware)
        self.com = Com()
        
        # Récupérer les infos du communicateur
        self.nbProcess = self.com.getNbProcess()
        self.myId = self.com.getMyId()
        self.name = name  # Utiliser l'attribut name directement
        
        self.alive = True
        self.start()
    
    def run(self):
        """
        Démonstration complète des fonctionnalités du middleware
        """
        loop = 0
        print(f"🚀 {self.name} (ID={self.myId}) démarré")
        
        while self.alive and loop < 15:  # 15 cycles pour voir toutes les fonctionnalités
            sleep(1.5)  # Pause pour lisibilité
            
            try:
                # ========== PHASE 1: Communication asynchrone ==========
                
                if loop == 1 and self.myId == 0:
                    print(f"\n=== PHASE 1: Communication asynchrone ===")
                    self.com.broadcast("Hello tout le monde !")
                
                if loop == 2 and self.myId == 1:
                    self.com.sendTo("Message privé pour P2", 2)
                
                if loop == 3 and self.myId == 2:
                    # Lire les messages reçus
                    if not self.com.mailbox.isEmpty():
                        msg = self.com.mailbox.getMessage()
                        print(f"📧 {self.name}: lu message '{msg.payload}' de P{msg.sender}")
                
                # ========== PHASE 2: Section critique ==========
                
                if loop == 5 and self.myId == 0:
                    print(f"\n=== PHASE 2: Section critique ===")
                
                if loop == 6:
                    if self.myId == 2:  # P2 demande en premier
                        print(f"🙋 {self.name}: demande section critique")
                        self.com.requestSC()
                        print(f"🔥 {self.name}: TRAVAILLE en section critique")
                        sleep(2)  # Simulation du travail
                        print(f"✅ {self.name}: travail terminé")
                        self.com.releaseSC()
                
                if loop == 8:
                    if self.myId == 1:  # P1 demande ensuite
                        print(f"🙋 {self.name}: demande section critique")
                        self.com.requestSC()
                        print(f"🔥 {self.name}: TRAVAILLE en section critique")
                        sleep(1.5)  # Simulation du travail
                        print(f"✅ {self.name}: travail terminé")
                        self.com.releaseSC()
                
                # ========== PHASE 3: Synchronisation ==========
                
                if loop == 10:
                    if self.myId == 0:
                        print(f"\n=== PHASE 3: Synchronisation par barrière ===")
                    print(f"⏸️ {self.name}: arrive à la barrière de synchronisation")
                    self.com.synchronize()
                    print(f"🎉 {self.name}: synchronisation terminée, on continue !")
                
                # ========== PHASE 4: Test de l'horloge ==========
                
                if loop == 12 and self.myId == 1:
                    print(f"\n=== PHASE 4: Test horloge de Lamport ===")
                    # Incrémenter manuellement l'horloge
                    old_clock = self.com.lamport_clock
                    new_clock = self.com.inc_clock()
                    print(f"🕒 {self.name}: horloge {old_clock} → {new_clock}")
                    
                    # Envoyer un message pour voir l'effet
                    self.com.sendTo("Test horloge", 0)
                
                # ========== PHASE 5: Communication synchrone (si implémentée) ==========
                
                if loop == 14:
                    if self.myId == 0:
                        print(f"\n=== PHASE 5: Communication synchrone ===")
                        try:
                            # Test broadcastSync si disponible
                            self.com.broadcastSync("Message synchrone de P0", 0)
                        except Exception as e:
                            print(f"⚠️ Communication synchrone pas encore implémentée: {e}")
                
            except Exception as e:
                print(f"❌ {self.name}: Erreur loop {loop}: {e}")
            
            loop += 1
        
        print(f"🛑 {self.name}: terminé")
    
    def stop(self):
        """Arrête proprement le processus"""
        self.alive = False
        
    def waitStopped(self):
        """Attend que le processus se termine"""
        self.join()

def launch(nbProcess=3, runningTime=25):
    """
    Lance l'expérience avec le middleware Com
    
    Args:
        nbProcess (int): Nombre de processus à lancer (défaut: 3)
        runningTime (int): Durée en secondes (défaut: 25)
    """
    # Configurer le nombre de processus via variable d'environnement
    os.environ['NB_PROCESSES'] = str(nbProcess)
    
    print("🎯" + "="*60)
    print(f"🚀 DÉMARRAGE DE {nbProcess} PROCESSUS AVEC MIDDLEWARE COM")
    print("🎯" + "="*60)
    print()
    
    # Créer et démarrer tous les processus
    processes = []
    for i in range(nbProcess):
        process_name = f"P{i}"
        print(f"📦 Création du processus {process_name}")
        processes.append(Process(process_name))
        sleep(0.3)  # Délai entre les créations pour éviter les conflits d'ID
    
    print(f"\n✅ {nbProcess} processus créés et démarrés")
    print(f"⏱️ Expérience en cours pendant {runningTime} secondes...\n")
    
    # Laisser tourner
    try:
        sleep(runningTime)
    except KeyboardInterrupt:
        print("\n⚠️ Interruption manuelle détectée")
    
    # Arrêt propre
    print("\n" + "="*60)
    print("🛑 ARRÊT EN COURS...")
    print("="*60)
    
    # Demander l'arrêt
    for p in processes:
        p.stop()
    
    # Attendre la fin
    for p in processes:
        p.waitStopped()
    
    # Nettoyage des fichiers temporaires
    _cleanup_temp_files()
    
    print("✅ Tous les processus sont terminés")
    print("🎉 EXPÉRIENCE TERMINÉE\n")

def _cleanup_temp_files():
    """Nettoie les fichiers temporaires créés"""
    import tempfile
    temp_dir = tempfile.gettempdir()
    
    files_to_clean = [
        'com_process_counter.txt',
        'com_process_counter.txt.lock',
        'com_sync_counter.json',
        'com_sync_counter.json.lock'
    ]
    
    for filename in files_to_clean:
        filepath = os.path.join(temp_dir, filename)
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except:
            pass  # Ignorer les erreurs de nettoyage

if __name__ == '__main__':
    print("🔬 Test du middleware Com avec communication distribuée")
    print("📋 Fonctionnalités testées:")
    print("   • Communication asynchrone (broadcast, sendTo)")
    print("   • Section critique distribuée par jeton")
    print("   • Synchronisation par barrière")
    print("   • Horloge de Lamport")
    print("   • Boîte aux lettres")
    print("   • Attribution automatique d'IDs (sans variables de classe)")
    print()
    
    # Configuration par défaut
    NB_PROCESSES = 3
    RUNNING_TIME = 30  # 30 secondes pour voir toutes les phases
    
    try:
        launch(nbProcess=NB_PROCESSES, runningTime=RUNNING_TIME)
    except Exception as e:
        print(f"❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()