from kaggle_environments import evaluate, make
import sys
sys.path.append("../src")
import src.timevalue_agent as timevalue
env = make("halite", configuration={ "episodeSteps": 400 }, debug=True)
agents = {"timevalue":timevalue.get_time_value_agent(maxDepth=3),"version1":"agent.py","timevalueNew":
          timevalue.get_time_value_agent(spawn_payoff_factor=3.0,maxDepth=3),
          "timevalueOldNew":timevalue.get_time_value_agent(spawn_payoff_factor=4.0,maxDepth=4)}
env.agents = agents
env.run(["timevalue","version1","timevalueNew","timevalueOldNew"])
out = env.render(mode="html", width=500, height=450)
f = open("replay.html", "w")
f.write(out)
f.close()