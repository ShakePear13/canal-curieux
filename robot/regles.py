# -*- coding: utf-8 -*-
"""Règles du robot Canal Curieux : tout ce qui se règle à la main est ici.

Aucune IA : ce sont des listes de mots et de seuils, modifiables sans risque.
"""

# ---------------------------------------------------------------- réglages
DUREE_MIN = 180            # secondes : en dessous, on considère que c'est un Short ou un extrait
DUREE_MIN_DECOUVERTE = 480 # les vidéos de chaînes découvertes doivent faire au moins 8 min
MAX_PAR_CHAINE = 3         # nouveautés ajoutées par chaîne et par passage
MAX_PAR_PASSAGE = 40       # plafond total d'ajouts par passage (sobriété)
SOCLE_PAR_CHAINE = 6       # au 1er passage, une chaîne peu représentée est complétée jusqu'à ce nombre
PART_DECOUVERTES = 0.05    # ~5 % du catalogue en vidéos de chaînes découvertes
MAX_DECOUVERTES_EN_ATTENTE = 4   # on ne propose rien de plus tant que tu n'as pas trié
NOUVELLES_DECOUVERTES_PAR_PASSAGE = 2
VIDEOS_PAR_DECOUVERTE = 2
ABONNES_MIN_DECOUVERTE = 5000
HN_PAR_PASSAGE = 40
SECTIONS_TOUS_LES_JOURS = 56     # relire les « chaînes mises en avant » d'une chaîne tous les 56 jours

THEMES = {
    "finance": "Finance & bourse", "eco": "Économie", "sciences": "Sciences",
    "ingenierie": "Ingénierie & industrie", "tech": "Tech & numérique", "histoire": "Histoire",
    "geopol": "Géopolitique & politique", "energie": "Énergie & climat",
    "philo": "Philo, lettres & langue", "musique": "Musique", "auto": "Automobile",
    "comm": "Éloquence & communication",
}

# Mots qui écartent une vidéo (titre normalisé : minuscules, sans accents)
MOTS_EXCLUS = [
    "#shorts", "#short", "teaser", "bande-annonce", "bande annonce", "trailer", "concours",
    "giveaway", "unboxing", "je reagis", "reaction a", "reacts to", "drama", "clash",
    "best of", "bestof", "rediffusion", "annonce :", "live de ", "en direct de",
]

# Chaînes de médias généralistes : jamais proposées en découverte
MAINSTREAM = [
    "bfm", "lci", "cnews", "france 24", "france24", "franceinfo", "france info", "france tv",
    "france televisions", "france 2", "france 3", "france 5", "tf1", "m6", "arte", "brut",
    "konbini", "le monde", "le figaro", "liberation", "le parisien", "l'obs", "mediapart",
    "europe 1", "rtl", "rmc", "france inter", "france culture", "radio france", "nrj", "mtv",
    "bbc", "cnn", "fox news", "sky news", "nota bene", "vevo", "quotidien", "tpmp", "c a vous",
    "hugodecrypte", "le huffpost", "huffpost", "public senat", "lcp", "euronews", "tv5monde",
]

# ---------------------------------------------------------------- sous-thèmes
# (sous-thème, [mots-clés cherchés dans le titre normalisé]) ; "=mot" = mot entier
REGLES = [
    ("Bourse", ["bourse", "marche", "trading", "vix", "stock", "hedge", "investing", "fondamentale", "strategie", "cac", "nasdaq", "actions"]),
    ("ETF & placement", ["etf", "portefeuille", "emergent", "silver", "invest", "pea", "assurance-vie", "assurance vie", "scpi"]),
    ("Patrimoine", ["patrimoine", "holding", "retraite", "enrichir", "banquier", "immobilier", "heritage", "impot"]),
    ("Crypto", ["crypto", "bitcoin", "ethereum"]),
    ("Monnaie & banques centrales", ["inflation", "banque", "argent", "money", "fed", "monetaire", "tresor", "bce", "euro"]),
    ("Dette publique", ["dette", "taux", "deficit"]),
    ("Capitalisme & croissance", ["capitalism", "croissance", "economie", "economics", "poorer", "poor", "consolidation", "accounting", "pib", "chomage"]),
    ("Astronomie", ["univers", "planete", "galax", "cosmi", "solaire", "trou noir", "trous noirs", "universe", "black hole", "etoile", "mars", "lune"]),
    ("Physique", ["quantique", "physique", "physics", "electricite", "entropy", "gravitation", "mesure", "counterintuitive", "relativite", "lumiere"]),
    ("Mathématiques", ["linear", "vector", "matri", "determinant", "eigen", "dot product", "cross product", "calcul", "theoreme", "6÷2", "math", "nombre", "probabilit"]),
    ("Esprit critique", ["esprit", "autodefense", "bayes", "fake news", "biais", "complot"]),
    ("Comportements humains", ["foule", "influenceur", "brain", "cerveau", "psycholog"]),
    ("IA", ["=ia", "intelligence artificielle", "chatgpt", "deep learning", "=ai", "llm", "gpt", "claude", "mistral"]),
    ("Cybersécurité", ["hack", "virus", "dark web", "arnaque", "ranconne", "pirat", "faille", "malware"]),
    ("Programmation", ["code", "coder", "developpeur", "python", "javascript", "linux", "logiciel"]),
    ("Électronique & matériel", ["electronique", "arduino", "processeur", "circuit", "soudure", "composant", "raspberry", "carte mere", "gpu", "=pc", "smartphone", "batterie"]),
    ("Nucléaire", ["nucleaire", "uranium", "iter", "fusion", "reacteur", "epr"]),
    ("Industrie & infrastructures", ["usine", "pont", "train", "ferroviaire", "aluminium", "rocket", "f-16", "a-10", "makers", "experience", "avion", "tunnel", "barrage", "acier"]),
    ("Climat & CO2", ["climat", "co2", "carbone", "climate", "rechauffement"]),
    ("Océans", ["ocean", "marin", "=mer", "abysse", "sous-marin", "baleine", "requin", "corail"]),
    ("Énergie", ["energie", "energetique", "electricite", "renouvelable", "transition", "petrole", "gaz", "eolien", "hydrogene"]),
    ("Antiquité", ["punic", "granicus", "pyrrh", "alexander", "rome", "romain", "grece", "egypte", "gaulois"]),
    ("Moyen Âge", ["crusade", "agincourt", "mongol", "moyen age", "medieval", "croisade", "chevalier"]),
    ("Époque moderne", ["revolution", "trenton", "titanic", "atlantique", "xixe", "civil war", "tranch", "napoleon", "louis xiv"]),
    ("Guerres mondiales", ["premiere guerre", "seconde guerre", "world war", "pacific war", "crete", "1914", "1940", "1944", "resistance"]),
    ("Histoire de France", ["histoire de france", "france en", "de la france", "histoire complete", "history of france", "patrimoine", "chateau", "village"]),
    ("Europe & UE", ["europe", "=ue", "frexit", "bruxelles"]),
    ("Politique française", ["france", "droite", "gauche", "clivage", "presidentielle", "knafo", "le maire", "republique", "gouverne", "asselineau", "2027", "assemblee", "budget"]),
    ("Géopolitique", ["geopolitique", "moyen-orient", "rdc", "rwanda", "asie", "civilisations", "strategique", "humanitaire", "chine", "russie", "ukraine", "etats-unis", "otan"]),
    ("Géographie & cartes", ["geography", "map", "cartograph", "frontiere", "border"]),
    ("Médias", ["media", "journalis", "legend", "brut"]),
    ("Philosophie morale", ["morale", "utilitarisme", "stoicisme", "spinoza", "philosoph", "corps et l'esprit", "manipulation", "nietzsche", "platon", "kant"]),
    ("Littérature", ["roman", "classiques", "gautier", "delacroix", "litterature", "poesie", "hugo", "balzac", "proust"]),
    ("Langue française", ["langue", "langues", "francais", "orthographe", "etymologie"]),
    ("Analyse de morceaux", ["what makes this song great"]),
    ("Théorie musicale", ["music theory", "theory", "harmonie", "accord"]),
    ("Essais", ["essai", "test"]),
    ("Guide d'achat", ["guide achat", "quelle voiture", "fiabilite", "occasion"]),
    ("Histoire de l'auto", ["avantime", "echec", "histoire de vilebrequin", "fleetwood", "1980", "histoire de"]),
    ("Rhétorique", ["rhetorique", "argument", "convaincre", "persuader"]),
    ("Communication d'entreprise", ["dirigeant", "entreprise", "manager", "reunion", "pitch"]),
    ("Art oratoire", ["oratoire", "prise de parole", "eloquence", "discours", "trac", "voix"]),
]
DEFAUT = {
    "finance": "Bourse", "eco": "Capitalisme & croissance", "sciences": "Physique",
    "ingenierie": "Industrie & infrastructures", "tech": "Programmation", "histoire": "Histoire générale",
    "geopol": "Géopolitique", "energie": "Énergie", "philo": "Philosophie morale",
    "musique": "Analyse de morceaux", "auto": "Essais", "comm": "Art oratoire",
}
AUTORISES = {  # sous-thèmes permis par thème, pour éviter les croisements bizarres
    "finance": {"Bourse", "ETF & placement", "Patrimoine", "Crypto", "Énergie", "Capitalisme & croissance", "Monnaie & banques centrales"},
    "eco": {"Monnaie & banques centrales", "Dette publique", "Capitalisme & croissance", "Politique française"},
    "sciences": {"Astronomie", "Physique", "Mathématiques", "Esprit critique", "Comportements humains", "IA"},
    "ingenierie": {"Nucléaire", "Industrie & infrastructures"},
    "tech": {"IA", "Cybersécurité", "Programmation", "Électronique & matériel"},
    "histoire": {"Antiquité", "Moyen Âge", "Époque moderne", "Guerres mondiales", "Histoire de France", "Europe & UE"},
    "geopol": {"Europe & UE", "Politique française", "Géopolitique", "Géographie & cartes", "Médias", "IA", "Climat & CO2"},
    "energie": {"Climat & CO2", "Énergie", "Nucléaire", "Océans"},
    "philo": {"Philosophie morale", "Littérature", "Langue française"},
    "musique": {"Analyse de morceaux", "Théorie musicale"},
    "auto": {"Essais", "Guide d'achat", "Histoire de l'auto"},
    "comm": {"Art oratoire", "Rhétorique", "Communication d'entreprise"},
}

# ---------------------------------------------------------------- ligne « Pourquoi »
# Une phrase par chaîne : qui l'a choisie + ce que c'est. Jamais de fait inventé.
POURQUOI = {
    "Finary": "Ton choix · patrimoine et investissement expliqués",
    "Nicolas Chéron": "Ton choix · stratégie boursière et lecture des marchés",
    "UPR TV": "Ton choix · conférences longues de François Asselineau",
    "Sarah Knafo": "Ton choix · prises de parole de Sarah Knafo",
    "Vilebrequin": "Ton choix · essais et culture automobile",
    "Aywen": "Ton choix · informatique et défis de code",
    "VA Plus": "Ton choix · format magazine de VA Plus",
    "LEGEND": "Ton choix · grands entretiens",
    "Jean-Marc Jancovici": "Ton choix · énergie et climat par Jancovici",
    "Thierry Watelet": "Ton choix · art oratoire et rhétorique",
    "Heu?reka": "Sélection de départ · référence de la vulgarisation économique en français",
    "Patrick Boyle": "Sélection de départ · ex-gérant de fonds, finance et marchés",
    "The Plain Bagel": "Sélection de départ · bases de l'investissement, analyste financier",
    "Money & Macro": "Sélection de départ · macroéconomie par un économiste",
    "Wendover Productions": "Sélection de départ · économie et logistique du monde réel",
    "Science Étonnante": "Sélection de départ · physique et IA par un docteur en physique",
    "Balade Mentale": "Sélection de départ · astronomie et cosmos, très visuel",
    "Fouloscopie": "Sélection de départ · science des foules par un chercheur",
    "Micmaths": "Sélection de départ · maths récréatives",
    "Hygiène Mentale": "Sélection de départ · esprit critique et méthode",
    "Veritasium": "Sélection de départ · physique contre-intuitive",
    "3Blue1Brown": "Sélection de départ · les maths visualisées, référence mondiale",
    "Kurzgesagt": "Sélection de départ · sciences en animation",
    "Monsieur Bidouille": "Sélection de départ · coulisses de l'industrie et du nucléaire",
    "Real Engineering": "Sélection de départ · ingénierie expliquée",
    "Micode": "Sélection de départ · enquêtes cybersécurité",
    "Underscore_": "Sélection de départ · émission tech et IA",
    "Histony": "Sélection de départ · histoire par un historien",
    "Manon Bril": "Sélection de départ · histoire par une docteure en histoire",
    "OverSimplified": "Sélection de départ · grandes périodes racontées en animation",
    "Kings and Generals": "Sélection de départ · histoire militaire en cartes animées",
    "Thinkerview": "Sélection de départ · longs entretiens sans coupe",
    "Mister Geopolitix": "Sélection de départ · géopolitique accessible",
    "RealLifeLore": "Sélection de départ · géographie et géopolitique",
    "Le Réveilleur": "Sélection de départ · climat et énergie, sources à l'appui",
    "Monsieur Phi": "Sélection de départ · philosophie par un prof de philo",
    "Le Précepteur": "Sélection de départ · philosophie par un prof de philo",
    "Le Mock": "Sélection de départ · littérature classique",
    "Linguisticae": "Sélection de départ · linguistique",
    "Rick Beato": "Sélection de départ · un producteur décortique les morceaux",
    "Adam Neely": "Sélection de départ · théorie musicale",
}
