# Max's Adventure - A Python Game


## About the game
This was a project made for a 2 semester Python course at the university.

It was my first time using Python, but I got so involved that I ended up doing something beyond expected. The game uses the Pygame library as the render engine, and a pyshics engine made from scratch to simulate gravity and different object interation (that was the hardest part by far, but it was worth it to learn).

Video showing the gameplay:

https://www.youtube.com/watch?v=nJsVoI51Noc

Video showing some of the behind the scenes during the creation process:

https://www.youtube.com/watch?v=dAUqbNDkGGg

## How to play

1- Install Python 3.X

2- Clone this repo

3- Open the terminal at the root folder and run to install required libs:
```
pip install -r requirements.txt
```

3- Then run this to start the game:
```
python main.py
```

## Controls

Gameplay:
- A: Walk left
- D: Walk right
- W: Jump
- Shift: Hold to run
- Space: Hold to grab objects
- F: Grab/Hide gun (if you have any ammo)
- Esc: Pause
- Mouse: Use to aim, left-click to shoot or punch enemies

## God-Mode

You can activate God-Mode in the pause (settings) menu

Feadures:
- Infinite ammo
- Infinite life
- Infinite Jump
- Spawn cube with mouse right-click
- Spawn enemy with mouse wheel-click
