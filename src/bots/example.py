"""
Random walker from example page https://botwars.io/Documentation/python3
"""
import sys
import random

rdm = random.SystemRandom()
spawns = ["12:5", "12:12", "5:5", "5:12"]
directions = ['N','E','S','W']
actions = []

# Read the input from STDIN
for line in sys.stdin:

    # Get the MapData from the input
    gameData = line.split('#')

    # Loop through each bot
    for nextBot in gameData[1].split(','):

        botData = nextBot.split('-')

        # If it's our own bot, then select a random direction
        if(botData[0] == 'F'):
            actions.append(botData[1] + '-M-' + rdm.choice(directions))

# Return to STDOUT
print(','.join(actions))
