# Launcher.py
from time import sleep
from Process import Process

def launch(nbProcess, runningTime=20):
    """Lance l'expérience avec plusieurs processus"""
    print(f"🚀 Démarrage de {nbProcess} processus")
    print("=" * 50)
    
    processes = []
    for i in range(nbProcess):
        processes.append(Process("P"+str(i), nbProcess))

    sleep(runningTime)
    
    print("=" * 50)
    print("🛑 Arrêt en cours...")
    
    for p in processes:
        p.stop()
    for p in processes:
        p.waitStopped()
    
    print("✅ Terminé")

if __name__ == '__main__':
    launch(nbProcess=3, runningTime=20)  # Plus court pour les tests