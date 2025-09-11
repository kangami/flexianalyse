#!/bin/bash

# Variables
EC2_USER="ec2-user"
EC2_IP="18.223.125.154"
PEM_FILE="/c/Users/KARIM NGAMI TEUMI/Downloads/flexianalyse.pem"
EC2_PATH="/var/www/html"
LOCAL_BUILD_DIR="dist"
LOCAL_BACKEND_DIR="Backend"

# 1. Build du projet React
echo "🏗️ Lancement de la build React..."
npm run build

if [ $? -ne 0 ]; then
  echo "❌ Échec du build React."
  exit 1
fi

echo "✅ Build React terminé."

# 2. Transfert des fichiers vers EC2
echo "📤 Transfert des fichiers vers le serveur..."

# Transfert du répertoire dist/ vers /home/ec2-user/
scp -i "$PEM_FILE" -r "$LOCAL_BUILD_DIR"/* "$EC2_USER@$EC2_IP:/home/$EC2_USER/dist/"

if [ $? -ne 0 ]; then
  echo "❌ Échec du transfert du répertoire dist/."
  exit 1
fi

# Transfert du répertoire Backend/ vers /home/ec2-user/ sans déplacement (copie)
scp -i "$PEM_FILE" -r "$LOCAL_BACKEND_DIR"/* "$EC2_USER@$EC2_IP:/home/$EC2_USER/backend/"

if [ $? -ne 0 ]; then
  echo "❌ Échec du transfert du répertoire Backend/."
  exit 1
fi

echo "✅ Transfert terminé."

# 3. Déploiement sur le serveur
echo "🚀 Déploiement sur le serveur..."
ssh -i "$PEM_FILE" "$EC2_USER@$EC2_IP" << EOF
  # Vérifier et recréer le répertoire si nécessaire
  if [ ! -d "$EC2_PATH" ]; then
    sudo mkdir -p "$EC2_PATH"
    sudo chown -R nginx:nginx "$EC2_PATH"
    sudo chmod -R 755 "$EC2_PATH"
  fi
  # Arrêter Nginx temporairement
  sudo systemctl stop nginx
  # Supprimer uniquement le contenu existant
  sudo rm -rf "$EC2_PATH"/*
  # Déplacer uniquement les fichiers de dist/ transférés
  sudo mv /home/$EC2_USER/dist/* "$EC2_PATH" 2>/dev/null || echo "Avertissement : Aucun fichier à déplacer dans dist/"
  # Redémarrer Nginx
  sudo systemctl start nginx
  echo "✅ Déploiement terminé et Nginx relancé."
EOF

if [ $? -ne 0 ]; then
  echo "❌ Échec du déploiement sur le serveur."
  exit 1
fi

echo "🎉 Déploiement complet avec succès."