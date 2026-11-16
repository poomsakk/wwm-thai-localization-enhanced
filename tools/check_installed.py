"""Show which Thai locale files are installed in the game: our MOD build, the ORIGINAL backup, or something else."""
import hashlib
import sys
from pathlib import Path

GAME = Path(r"D:\steam\steamapps\common\Where Winds Meet")
ROOT = Path(__file__).resolve().parent.parent
PKG = GAME / "Package/HD/oversea/locale"
PAIRS = [  # game file, our build, original backup
    (PKG / "translate_words_map_th", ROOT / "work/build/translate_words_map_th",
     ROOT / "backup/original/Package/translate_words_map_th"),
    (PKG / "translate_words_map_th_diff", ROOT / "work/build/translate_words_map_th_diff",
     ROOT / "backup/original/Package/translate_words_map_th_diff"),
    (GAME / "LocalData/Patch/HD/oversea/locale/translate_words_map_th_diff", None,
     ROOT / "backup/original/LocalData/translate_words_map_th_diff"),
]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p and p.exists() else None


for game, mod, orig in PAIRS:
    h = sha(game)
    state = ("MISSING" if h is None else "MOD (ours)" if h == sha(mod) else
             "ORIGINAL (backup)" if h == sha(orig) else "OTHER (game updated -> run update_game.bat)")
    print(f"{state:44} {game.relative_to(GAME)}")
sys.exit(0)
