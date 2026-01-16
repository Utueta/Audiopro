
#!/bin/bash

echo "⚠️ Purge de la mémoire applicative (Database/Models)..."

rm -rf ../database/*

rm -rf ../models/*.joblib

rm -rf ../logs/*.log

echo "✅ Système prêt pour un nouvel entraînement."

