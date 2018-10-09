import requests
import json
from flask import render_template
from app import app
from .transitivity_rankings import TransRank


@app.route('/')
def rank_page():
    conferences_url = 'https://api.collegefootballdata.com/conferences'
    conferences = json.loads(requests.get(conferences_url).text)
    conferences = [c['name'] for c in conferences]
    game_data_url = 'https://api.collegefootballdata.com/games?year=2018'
    game_data_url += '&home_conference=' + ','.join(conferences).replace(' ', '%20')
    game_data_url += '&away_conference=' + ','.join(conferences).replace(' ', '%20')
    game_data = json.loads(requests.get(game_data_url).text)
    winners = [g['away_team'] if g['away_points'] > g['home_points'] else g['home_team'] for g in game_data]
    losers = [g['home_team'] if g['away_points'] > g['home_points'] else g['away_team'] for g in game_data]
    trans = TransRank(winners, losers)
    teams_url = 'https://api.collegefootballdata.com/teams'
    team_info = json.loads(requests.get(teams_url).text)
    logos = {x['school']: x['logos'][0] for x in team_info if x['school'] in trans.teams}
    html_table = trans.get_html_table(images=logos)
    return render_template('ranks.html', table=html_table)

