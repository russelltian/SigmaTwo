from kaggle_environments import make
import unittest
import sys
sys.path.append("../src")
from src import agent as modela

# Create a test environment for use later
board_size = 5
environment = make("halite", configuration={"size": board_size, "startingHalite": 2000})
agent_count = 2
environment.reset(agent_count)
environment.run([modela.agent, "random"])
out = environment.render(mode="html", width=500, height=450)
f = open("replay.html", "w")
f.write(out)
f.close()
