import os
import shutil
import logging

# Configuration du logging pour un suivi professionnel
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def setup_expert_architecture():
    root_dir = os.getcwd()
    
    # 1. Définition de l'arborescence cible complète
    structure = [
        "core/analyzer",
        "core/brain",
        "core/storage",
        "ui",
        "services",
        "assets",
        "database",
        "models",
        "logs",
        "scripts"
    ]
    
    # 2. Mapping exhaustif des fichiers (Source racine -> Destination spécifique)
    file_mapping = {
        "app.py": "app.py",                 # Point d'entrée racine
        "manager.py": "core/manager.py",    # <--- CentralManager déplacé ici
        "analyzer.py": "core/analyzer/dsp.py",
        "spectral.py": "core/analyzer/spectral.py",
        "model.py": "core/brain/model.py",
        "database.py": "core/storage/database.py",
        "view.py": "ui/view.py",
        "workers.py": "workers.py",
        "llm_service.py": "services/llm_service.py",
        "check_health.py": "scripts/check_health.py",
        "audio_expert_rf.joblib": "models/audio_expert_rf.joblib",
        "audio_expert.db": "database/audio_expert.db"
    }

    # 3. Création des répertoires et initialisation des packages (__init__.py)
    logging.info("🔨 Création de l'arborescence et des packages...")
    for folder in structure:
        os.makedirs(os.path.join(root_dir, folder), exist_ok=True)
        # Indispensable pour que "import core.manager" fonctionne
        # On remonte l'arborescence pour créer des __init__.py à chaque niveau
        parts = folder.split('/')
        for i in range(1, len(parts) + 1):
            sub_path = os.path.join(root_dir, *parts[:i])
            init_file = os.path.join(sub_path, "__init__.py")
            if not os.path.exists(init_file):
                with open(init_file, 'w') as f: pass

    # 4. Migration des fichiers de code et données
    logging.info("🚚 Migration des fichiers vers la nouvelle structure...")
    for filename, destination in file_mapping.items():
        source_path = os.path.join(root_dir, filename)
        dest_path = os.path.join(root_dir, destination)
        
        if os.path.exists(source_path):
            # Sécurité : ne pas déplacer si on est déjà au bon endroit
            if os.path.abspath(source_path) != os.path.abspath(dest_path):
                if not os.path.exists(dest_path):
                    shutil.move(source_path, dest_path)
                    logging.info(f"Déplacé : {filename} -> {destination}")
                else:
                    logging.warning(f"Conflit : {destination} existe déjà. Source {filename} conservée.")

    # 5. Création automatique du requirements.txt
    req_path = os.path.join(root_dir, "requirements.txt")
    if not os.path.exists(req_path):
        content = (
            "PySide6>=6.5.0\nlibrosa>=0.10.0\nnumpy>=1.24.0\n"
            "scikit-learn>=1.2.0\nmatplotlib>=3.7.0\nmutagen>=1.46.0\n"
            "psutil>=5.9.0\njoblib>=1.3.0\nsoundfile>=0.12.1\n"
            "requests>=2.31.0\n" 
        )
        with open(req_path, 'w') as f:
            f.write(content)
        logging.info("📝 requirements.txt généré.")

    # 6. Organisation des Assets (Images, Icônes, Styles)
    logging.info("🎨 Organisation des ressources visuelles...")
    asset_extensions = ('.ico', '.png', '.jpg', '.jpeg', '.svg', '.qss')
    for file in os.listdir(root_dir):
        if file.lower().endswith(asset_extensions) or "logo" in file.lower():
            source_path = os.path.join(root_dir, file)
            dest_path = os.path.join(root_dir, "assets", file)
            
            if os.path.isfile(source_path):
                shutil.move(source_path, dest_path)
                logging.info(f"Asset déplacé : {file} -> assets/")

    logging.info("✅ Architecture V2.4 opérationnelle (CentralManager -> core/manager.py).")

if __name__ == "__main__":
    setup_expert_architecture()
