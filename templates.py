CANVAS_SIZE = (1080, 1350)
PREVIEW_SIZE = (432, 540)

BEST_OF_OPTIONS = ["BO1", "BO3", "BO5"]

POST_VERSIONS = [
    "Matchday",
    "Victory",
    "Defeat",
    "Liga-Teilnahme",
    "Spieler-Welcome",
]

POST_HEADLINES = {
    "Matchday": "MATCHDAY",
    "Victory": "VICTORY",
    "Defeat": "DEFEAT",
    "Liga-Teilnahme": "LIGA TEILNAHME",
    "Spieler-Welcome": "WELCOME",
}


GAME_TEMPLATES = {
    "Counter Strike": {
        "base": "#1f2937",
        "accent": "#f59e0b",
        "backgrounds": {
            "Matchday": "assets/backgrounds/counter_strike/matchday.jpg",
            "Victory": "assets/backgrounds/counter_strike/victory.jpg",
            "Defeat": "assets/backgrounds/counter_strike/defeat.jpg",
            "Liga-Teilnahme": "assets/backgrounds/counter_strike/liga_teilnahme.jpg",
            "Spieler-Welcome": "assets/backgrounds/counter_strike/spieler_welcome.jpg",
        },
        "player_welcome_foreground": "assets/overlays/player_welcome_fade.png",
        "player_welcome_placeholder": "assets/placeholders/player_welcome_placeholder.png",
        "maps": ["Anubis", "Ancient", "Dust2", "Inferno", "Mirage", "Nuke", "Train", "Vertigo"],
        "leagues": ["FACEIT"],
    },
    "Rainbow Six": {
        "base": "#0f172a",
        "accent": "#f8fafc",
        "backgrounds": {
            "Matchday": "assets/backgrounds/rainbow_six/matchday.jpg",
            "Victory": "assets/backgrounds/rainbow_six/victory.jpg",
            "Defeat": "assets/backgrounds/rainbow_six/defeat.jpg",
            "Liga-Teilnahme": "assets/backgrounds/rainbow_six/liga_teilnahme.jpg",
            "Spieler-Welcome": "assets/backgrounds/rainbow_six/spieler_welcome.jpg",
        },
        "player_welcome_foreground": "assets/overlays/player_welcome_fade.png",
        "player_welcome_placeholder": "assets/placeholders/player_welcome_placeholder.png",
        "maps": ["Clubhouse", "Oregon", "Kafe", "Bank", "Chalet", "Border", "Nighthaven", "Clubhouse", "Lair", "Konsulat", "Skyscraper" ,],
        "leagues": ["ESEA", "ESL", "Major"],
    },
    "Rocket League": {
        "base": "#0b1024",
        "accent": "#38bdf8",
        "backgrounds": {
            "Matchday": "assets/backgrounds/rocket_league/matchday.jpg",
            "Victory": "assets/backgrounds/rocket_league/victory.jpg",
            "Defeat": "assets/backgrounds/rocket_league/defeat.jpg",
            "Liga-Teilnahme": "assets/backgrounds/rocket_league/liga_teilnahme.jpg",
            "Spieler-Welcome": "assets/backgrounds/rocket_league/spieler_welcome.jpg",
        },
        "player_welcome_foreground": "assets/overlays/player_welcome_fade.png",
        "player_welcome_placeholder": "assets/placeholders/player_welcome_placeholder.png",
        "maps": ["DFH Stadium", "Mannfield", "Champions Field", "Utopia Coliseum", "Neo Tokyo", "Aquadome"],
        "leagues": ["RLCS", "ESL", "Community Cup"],
    },
    "Call of Duty": {
        "base": "#1a1a1a",
        "accent": "#84cc16",
        "backgrounds": {
            "Matchday": "assets/backgrounds/call_of_duty/matchday.jpg",
            "Victory": "assets/backgrounds/call_of_duty/victory.jpg",
            "Defeat": "assets/backgrounds/call_of_duty/defeat.jpg",
            "Liga-Teilnahme": "assets/backgrounds/call_of_duty/liga_teilnahme.jpg",
            "Spieler-Welcome": "assets/backgrounds/call_of_duty/spieler_welcome.jpg",
        },
        "player_welcome_foreground": "assets/overlays/player_welcome_fade.png",
        "player_welcome_placeholder": "assets/placeholders/player_welcome_placeholder.png",
        "maps": ["Skidrow", "Terminal", "Highrise", "Rio", "Karachi", "Sub Base", "Invasion"],
        "leagues": ["CDL", "ESL", "Community Cup"],
    },
}


def get_games():
    return list(GAME_TEMPLATES.keys())
