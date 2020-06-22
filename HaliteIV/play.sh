kaggle-environments run --environment halite --agents ./src/agent.py ./src/timevalue_agent.py random random --render '{"mode": "html"}' --debug True --out replay.html
firefox replay.html
