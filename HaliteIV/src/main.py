from kaggle_environments import evaluate, make
import sys
sys.path.append("../src")
import src.timevalue_agent as timevalue
env = make("halite", configuration={ "episodeSteps": 400 }, debug=True)
agents = {"timevalue":timevalue.get_time_value_agent(debug=False),"version1":"agent.py"}
env.agents = agents
env.run(["timevalue","version1","version1","version1"])
out = env.render(mode="html", width=500, height=450)
f = open("replay.html", "w")
f.write(out)
f.close()