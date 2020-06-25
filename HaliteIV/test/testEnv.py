from kaggle_environments import make
import unittest
import time
import sys
sys.path.append("../src")
from src import agent as modela
from src import timevalue_agent as modelb
import random
# Create a test environment for use later
time_value_ratio = [0.8, 0.85, 0.88, 0.9, 0.92, 0.95, 0.97]
min_turns_to_spawn = [20,15,10,5]
spawn_payoff_factor = [3.0,4.0,5.0,6.0,7.0,8.0,9.0]

leaderboard = {}
timeValue = [1.0,0.95]
for i in range(59):
    timeValue.append(timeValue[-1]*timeValue[1])
#print(timeValue)

for i in time_value_ratio:
    for j in min_turns_to_spawn:
        for k in spawn_payoff_factor:
            if i not in leaderboard:
                leaderboard[i] = {}
            if j not in leaderboard[i]:
                leaderboard[i][j] = {}
            if k not in leaderboard[i][j]:
                leaderboard[i][j][k] = [600,0]

def calcScore(a,b,a_score,b_score,n):
    global leaderboard
    assert(len(a) == 3)
    assert(len(b) == 3)
    a_rank = leaderboard[a[0]][a[1]][a[2]][0]
    b_rank = leaderboard[b[0]][b[1]][b[2]][0]
    diff = abs(a_rank-b_rank) if a_rank != b_rank else 50
    diff = min(diff,50)
    if a_score > b_score:
        leaderboard[a[0]][a[1]][a[2]][0] += int(diff/n*timeValue[leaderboard[a[0]][a[1]][a[2]][1]])
        leaderboard[a[0]][a[1]][a[2]][1] += 1
        leaderboard[b[0]][b[1]][b[2]][0] -= int(diff / n * timeValue[leaderboard[b[0]][b[1]][b[2]][1]])
        leaderboard[b[0]][b[1]][b[2]][1] += 1
        return
    elif a_score < b_score:
        leaderboard[a[0]][a[1]][a[2]][0] -= int(diff/n*timeValue[leaderboard[a[0]][a[1]][a[2]][1]])
        leaderboard[a[0]][a[1]][a[2]][1] += 1
        leaderboard[b[0]][b[1]][b[2]][0] += int(diff/ n * timeValue[leaderboard[b[0]][b[1]][b[2]][1]])
        leaderboard[b[0]][b[1]][b[2]][1] += 1
        return
    else:
        if a_rank > b_rank:
            leaderboard[a[0]][a[1]][a[2]][0] += int(
                diff/ n * timeValue[leaderboard[a[0]][a[1]][a[2]][1]])
            leaderboard[a[0]][a[1]][a[2]][1] += 1
            leaderboard[b[0]][b[1]][b[2]][0] -= int(
                diff/ n * timeValue[leaderboard[b[0]][b[1]][b[2]][1]])
            leaderboard[b[0]][b[1]][b[2]][1] += 1
            return
        elif a_rank < b_rank:
            leaderboard[a[0]][a[1]][a[2]][0] -= int(
                diff/ n * timeValue[leaderboard[a[0]][a[1]][a[2]][1]])
            leaderboard[a[0]][a[1]][a[2]][1] += 1
            leaderboard[b[0]][b[1]][b[2]][0] += int(
                diff/ n * timeValue[leaderboard[b[0]][b[1]][b[2]][1]])
            leaderboard[b[0]][b[1]][b[2]][1] += 1
            return
    return
   # print(leaderboard[a[0]][a[1]][a[2]],leaderboard[b[0]][b[1]][b[2]])
board_size = 21
game = 100
while game > 0:
    game -= 1
    print("Game left: ", game)
    environment = make("halite", configuration={"size": board_size, "startingHalite": 5000})
    agent_count = 4
    select = []
    while len(select) < 4:
        a,b,c = random.choice(time_value_ratio),random.choice(min_turns_to_spawn),random.choice(spawn_payoff_factor)
        if [a,b,c] not in select:
            select.append([a,b,c])
    environment.reset(agent_count)
    agents = {
    "a": modelb.get_time_value_agent(time_value_ratio=select[0][0],min_turns_to_spawn=select[0][1],spawn_payoff_factor=select[0][2]),
    "b": modelb.get_time_value_agent(time_value_ratio=select[1][0],min_turns_to_spawn=select[1][1],spawn_payoff_factor=select[1][2]),
    "c": modelb.get_time_value_agent(time_value_ratio=select[2][0],min_turns_to_spawn=select[2][1],spawn_payoff_factor=select[2][2]),
    "d": modelb.get_time_value_agent(time_value_ratio=select[3][0],min_turns_to_spawn=select[3][1],spawn_payoff_factor=select[3][2])}
    environment.agents = agents
    environment.run(["a", "b","c","d"])
    store = []
    for idx, val in enumerate(environment.state):
        #print(idx, val["reward"])
        store.append([idx, val["reward"]])
    for i in range(len(store)):
        for j in range(i+1,len(store)):
            calcScore(select[i],select[j],store[i][1],store[j][1],1)

result = []
for k1,b in leaderboard.items():
        for k2,c in b.items():
            for k3,d in c.items():
                if d[1] > 0:
                    result.append([[k1,k2,k3],d])
result = sorted(result,key=lambda x: x[1][0], reverse=True)
timestr = time.strftime("%m%d-%H%M")
f =open("best_val_{}.txt".format(timestr),"w")
f.write(str(result))
f.close()
out = environment.render(mode="html", width=500, height=450)
f = open("replay.html", "w")
f.write(out)
f.close()
