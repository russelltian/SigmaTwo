from kaggle_environments import evaluate, make
env = make("halite", configuration={ "episodeSteps": 200 }, debug=True)
env.run(["agent.py", "random","random","random"])
env.render(mode="html", width=800, height=600)