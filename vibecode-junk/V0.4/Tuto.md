📘 Tutoriel : Maîtriser l'Analyse avec la V0.2.4

Bienvenue dans la nouvelle ère d'Audio Expert Pro. La version 0.2.4 abandonne le diagnostic binaire "Vrai/Faux" pour un système de Score de Suspicion beaucoup plus fin. Voici comment interpréter vos résultats.
1. Comprendre le Score de Suspicion (0 à 100%)

Contrairement à l'ancienne version, le système évalue maintenant une probabilité de fraude ou d'anomalie. Le score est représenté sur votre jauge dynamique :

    🔵 0% à 40% (Zone Saine) : Le fichier présente des caractéristiques techniques cohérentes (SNR élevé, pas de coupure de fréquences suspecte). Aucune action requise.

    🟠 40% à 75% (Zone d'Arbitrage) : Le système détecte des irrégularités (ex: compression inhabituelle, bitrate instable). C'est ici que l'IA intervient pour vous aider.

    🔴 75% à 100% (Zone Critique) : Fortes présomptions de manipulation ou de dégradation majeure du signal.

2. Utiliser l'Arbitrage du LLM

Lorsque le score tombe dans la Zone d'Arbitrage (Orange), un bouton "Demander Diagnostic" apparaît (ou s'exécute automatiquement selon vos réglages).

L'IA ne regarde plus seulement les chiffres, elle analyse le contexte technique :

    Exemple : "Bien que le score soit de 65%, l'anomalie semble due à un vieil encodeur MP3 plutôt qu'à une manipulation volontaire du signal."

Conseil : Fiez-vous au diagnostic textuel pour décider si le fichier doit être écarté ou validé.
3. Les Nouvelles Métriques à la Loupe

Vous trouverez quatre indicateurs clés sous la jauge. Voici ce qu'ils signifient pour vous :
Métrique	Ce qu'elle surveille	Alerte si...
SNR	La clarté du signal.	Le bruit de fond est anormalement élevé.
Cut-off	La limite des hautes fréquences.	Le son est "étouffé", signe d'une possible double compression.
Clipping	La saturation numérique.	Le signal "tape" dans le rouge, indiquant un gain forcé.
Bitrate	La densité des données.	Le débit est trop faible pour une analyse de qualité pro.
4. Bonnes Pratiques pour une Analyse Fiable

    Vérification MIME automatique : Ne vous inquiétez plus de l'origine du fichier. Si le voyant de sécurité est Vert, le fichier a été certifié comme un flux audio réel par notre sentinelle logicielle.

    Gestion des Timeouts : Si une analyse dépasse 30 secondes, le système l'interrompt pour protéger votre ordinateur. Réessayez avec un extrait plus court du fichier.

    Historique : Utilisez le panneau latéral pour comparer les scores de fichiers similaires. Une cohérence de score sur une même série est souvent signe de fiabilité.

✅ Résumé du flux de travail

    Glissez-déposez votre fichier.

    Observez la couleur de la jauge.

    Lisez le diagnostic IA si la jauge est orange.

    Exportez le rapport certifié pour vos archives.
