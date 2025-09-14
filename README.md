# UFO Game Repo

**Doodad**:
An individual section that contains a set of buttons or a slider,
plus an LCD screen label.
Runs on a Pi Pico 2 with micropython (generally Python 3.9).

**Panel**:
`uv run python main.py -p --player {n}`
A whole set of doodads for a single player.
Runs on a Pi 3B+.

**Game**:
`uv run python main.py -g`
The central coordinator for the game.
Runs on a Pi 5 8gb.
