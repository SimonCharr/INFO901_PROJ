# DiceGame.py - Exemple style "jeu de dés" avec le middleware Com
import os
import random
from time import sleep
from threading import Thread
from Com import Com

class DiceGameProcess(Thread):
    """
    Processus qui joue au jeu de dés en utilisant toutes les fonctionnalités du middleware
    Reproduction de l'exemple donné dans le sujet original
    """
    
    def __init__(self, name):
        Thread.__init__(self)
        
        # Créer le communicateur (middleware)
        self.com = Com()
        
        # Récupérer les infos
        self.nbProcess = self.com.getNbProcess()
        self.myId = self.com.getMyId()
        self.name = name
        
        self.alive = True
        self.start()
    
    def run(self):
        """
        Scénario de jeu de dés reproduisant l'exemple du sujet
        """
        loop = 0
        print(f"🎮 {self.name} (ID={self.myId}) entre dans le jeu")
        
        while self.alive and loop < 20:
            sleep(1)
            
            try:
                # ========== Scénario du sujet original ==========
                
                if self.myId == 0:  # Utiliser l'ID réel, pas le nom
                    if loop == 2:
                        print(f"\n=== P{self.myId} démarre le jeu ===")
                        self.com.sendTo("j'appelle 2 et je te recontacte après", 1)
                    
                    elif loop == 4:
                        # Communication simple : juste envoyer, P2 va lire dans sa mailbox
                        self.com.sendTo("J'ai laissé un message à 2, je le rappellerai après, on se synchronise tous et on attaque la partie ?", 2)
                        
                    elif loop == 6:
                        self.com.sendTo("2 est OK pour jouer, on se synchronise et c'est parti!", 1)
                        
                    elif loop == 8:
                        print(f"🎯 P{self.myId}: Début de la partie - synchronisation")
                        self.com.synchronize()
                        
                        # Phase de jeu avec section critique
                        print(f"🎲 P{self.myId}: Demande l'accès au dé")
                        self.com.requestSC()
                        
                        if self.com.mailbox.isEmpty():
                            dice_result = random.randint(1, 6)
                            print(f"🎉 P{self.myId}: J'ai gagné ! Dé = {dice_result}")
                            self.com.broadcast(f"J'ai gagné avec un {dice_result} !")
                        else:
                            msg = self.com.mailbox.getMsg()
                            print(f"😞 P{self.myId}: P{msg.sender} a eu le jeton en premier")
                        
                        self.com.releaseSC()
                
                elif self.myId == 1:  # Utiliser l'ID réel
                    if loop == 3:
                        # Vérifier les messages reçus
                        if not self.com.mailbox.isEmpty():
                            msg = self.com.mailbox.getMessage()
                            print(f"📧 P{self.myId}: Lu message de P{msg.sender}: '{msg.payload}'")
                    
                    elif loop == 7:
                        # Lire les messages reçus
                        while not self.com.mailbox.isEmpty():
                            msg = self.com.mailbox.getMessage()
                            print(f"📧 P{self.myId}: Lu message de P{msg.sender}: '{msg.payload}'")
                        
                    elif loop == 8:
                        print(f"🎯 P{self.myId}: Rejoint la synchronisation")
                        self.com.synchronize()
                        
                        # Phase de jeu avec section critique
                        print(f"🎲 P{self.myId}: Demande l'accès au dé")
                        self.com.requestSC()
                        
                        if self.com.mailbox.isEmpty():
                            dice_result = random.randint(1, 6)
                            print(f"🎉 P{self.myId}: J'ai gagné ! Dé = {dice_result}")
                            self.com.broadcast(f"J'ai gagné avec un {dice_result} !")
                        else:
                            msg = self.com.mailbox.getMsg()
                            print(f"😞 P{self.myId}: P{msg.sender} a eu le jeton en premier")
                        
                        self.com.releaseSC()
                
                elif self.myId == 2:  # Utiliser l'ID réel
                    if loop == 5:
                        # Lire le message de P0 et répondre
                        if not self.com.mailbox.isEmpty():
                            msg = self.com.mailbox.getMessage()
                            print(f"📧 P{self.myId}: Lu message de P{msg.sender}: '{msg.payload}'")
                            print(f"💬 P{self.myId}: Répond à P0")
                            self.com.sendTo("OK, je suis prêt pour la partie !", 0)
                        
                    elif loop == 8:
                        print(f"🎯 P{self.myId}: Rejoint la synchronisation")
                        self.com.synchronize()
                        
                        # Phase de jeu avec section critique
                        print(f"🎲 P{self.myId}: Demande l'accès au dé")
                        self.com.requestSC()
                        
                        if self.com.mailbox.isEmpty():
                            dice_result = random.randint(1, 6)
                            print(f"🎉 P{self.myId}: J'ai gagné ! Dé = {dice_result}")
                            self.com.broadcast(f"J'ai gagné avec un {dice_result} !")
                        else:
                            msg = self.com.mailbox.getMsg()
                            print(f"😞 P{self.myId}: P{msg.sender} a eu le jeton en premier")
                        
                        self.com.releaseSC()
                
                # ========== Test des autres fonctionnalités ==========
                
                if loop == 12 and self.myId == 1:
                    print(f"\n=== Test communication synchrone avancée ===")
                    self.com.broadcastSync("Message de fin de partie", 1)
                
                if loop == 15 and self.myId == 0:
                    print(f"\n=== Test horloge de Lamport ===")
                    old_clock = self.com.lamport_clock
                    new_clock = self.com.inc_clock()
                    print(f"🕐 P{self.myId}: Horloge {old_clock} → {new_clock}")
                    self.com.sendTo("Test final", 2)
                
                if loop == 16 and self.myId == 2:
                    # Lire les derniers messages
                    while not self.com.mailbox.isEmpty():
                        msg = self.com.mailbox.getMessage()
                        print(f"📧 P{self.myId}: Message final de P{msg.sender}: '{msg.payload}'")
                        
            except Exception as e:
                print(f"❌ {self.name}: Erreur loop {loop}: {e}")
                import traceback
                traceback.print_exc()
            
            loop += 1
        
        print(f"🏁 P{self.myId}: Partie terminée")
    
    def stop(self):
        """Arrête proprement le processus"""
        self.alive = False
        
    def waitStopped(self):
        """Attend que le processus se termine"""
        self.join()

def launch_dice_game(nbProcess=3, runningTime=25):
    """
    Lance le jeu de dés avec le middleware Com
    """
    # Nettoyer d'abord les fichiers temporaires
    _cleanup_temp_files()
    sleep(0.1)  # Laisser le temps au nettoyage
    
    # Configurer le nombre de processus
    os.environ['NB_PROCESSES'] = str(nbProcess)
    
    print("🎲" + "="*60)
    print(f"🎮 JEU DE DÉS AVEC MIDDLEWARE COM ({nbProcess} JOUEURS)")
    print("🎲" + "="*60)
    print()
    print("📋 Scénario testé:")
    print("   • Communication asynchrone (messages, broadcast)")
    print("   • Communication synchrone (sendToSync, recevFromSync)")
    print("   • Section critique distribuée (accès au dé)")
    print("   • Synchronisation par barrière")
    print("   • Horloge de Lamport")
    print("   • Boîte aux lettres")
    print()
    
    # Créer et démarrer tous les processus
    processes = []
    for i in range(nbProcess):
        process_name = f"P{i}"
        print(f"🎯 Création du joueur {process_name}")
        processes.append(DiceGameProcess(process_name))
        sleep(0.3)
    
    print(f"\n✅ {nbProcess} joueurs créés et démarrés")
    print(f"⏱️ Partie en cours pendant {runningTime} secondes...\n")
    
    # Laisser jouer
    try:
        sleep(runningTime)
    except KeyboardInterrupt:
        print("\n⚠️ Interruption manuelle détectée")
    
    # Arrêt propre
    print("\n" + "="*60)
    print("🏁 FIN DE PARTIE")
    print("="*60)
    
    # Demander l'arrêt
    for p in processes:
        p.stop()
    
    # Attendre la fin
    for p in processes:
        p.waitStopped()
    
    # Nettoyage
    _cleanup_temp_files()
    
    print("✅ Tous les joueurs ont quitté")
    print("🎉 PARTIE TERMINÉE\n")

def _cleanup_temp_files():
    """Nettoie les fichiers temporaires"""
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
            pass

if __name__ == '__main__':
    print("🎲 JEU DE DÉS - Exemple d'utilisation du middleware Com")
    print("🎯 Reproduit le scénario de l'exemple donné dans le sujet")
    print()
    
    try:
        launch_dice_game(nbProcess=3, runningTime=40)  # 40 secondes au lieu de 30
    except Exception as e:
        print(f"❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()