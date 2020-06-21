from kaggle_environments import evaluate, make
env = make("halite", configuration={ "episodeSteps": 100 }, debug=True)
env.run(["agent.py", "random","random","random"])
out = env.render(mode="html", width=500, height=450)
f = open("replay.html", "w")
f.write(out)
f.close()