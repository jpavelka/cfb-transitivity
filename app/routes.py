import requests
import json
from flask import render_template, url_for, jsonify, request
from app import app
from .transitivity_rankings import TransRank

app.trans = None


@app.route('/')
def home_page():
    if app.trans is None:
        get_trans()
    top_ten = app.trans.rank_df.query('comb_rank <= 10')
    top_ten_teams = list(top_ten.index)
    top_ten_ranks = top_ten['comb_rank'].to_dict()
    top_ten_win_ranks = top_ten['win_rank'].to_dict()
    top_ten_loss_ranks = top_ten['loss_rank'].to_dict()
    top_ten_avg_ranks = top_ten['avg_rank'].to_dict()
    return render_template('index.html', all_teams=app.trans.teams, all_team_urls=app.trans.all_team_urls(),
                           top_ten_teams=top_ten_teams, top_ten_ranks=top_ten_ranks,
                           top_ten_win_ranks=top_ten_win_ranks, top_ten_loss_ranks=top_ten_loss_ranks,
                           top_ten_avg_ranks=top_ten_avg_ranks, logos=app.logos, urls=app.trans.all_team_urls())


@app.route('/rankings')
def rank_page():
    if app.trans is None:
        get_trans()
    html_table = app.trans.get_html_table(images=app.logos)
    return render_template('ranks.html', table=html_table,
                           all_teams=app.trans.teams, all_team_urls=app.trans.all_team_urls())


@app.route('/<team_with_underscores>')
def team_page_router(team_with_underscores):
    team = team_with_underscores.replace('_', ' ')
    return team_page(team)


def team_page(team):
    if app.trans is None:
        get_trans()
    if team not in app.trans.teams:
        return 'Team not found'
        # todo: make this nicer
    win_paths = app.trans.win_paths[team]
    win_levels, no_wins = get_levels(win_paths, app.trans.teams, team)
    loss_paths = app.trans.loss_paths[team]
    loss_levels, no_losses = get_levels(loss_paths, app.trans.teams, team)
    paths = {'victories': win_paths, 'defeats': loss_paths}
    levels = {'victories': win_levels, 'defeats': loss_levels}
    no_paths = {'victories': no_wins, 'defeats': no_losses}
    rank_info = dict(app.trans.rank_df.loc[team])
    return render_template('team.html', team=team, paths=paths, no_paths=no_paths, levels=levels, rank_info=rank_info,
                           logos=app.logos, all_teams=app.trans.teams, all_team_urls=app.trans.all_team_urls())


@app.route('/rankings/about')
def about_rank_page():
    return render_template('ranks-about.html')


@app.route('/_get_path', methods=['POST'])
def get_path():
    my_team = request.form['my_team']
    other_team = request.form['other_team']
    if other_team in app.trans.win_paths[my_team]:
        return jsonify(app.trans.win_paths[my_team][other_team])
    else:
        return jsonify([])


def get_levels(paths, all_teams, team):
    included_teams = []
    if len(paths) == 0:
        max_length = 0
    else:
        max_length = max(len(paths[t]) - 1 for t in paths)
    levels = {i + 1: [] for i in range(max_length)}
    for t in paths:
        levels[len(paths[t]) - 1] += [t]
        included_teams += [t]
    for l in levels:
        levels[l] = sorted(levels[l])
    excluded_teams = sorted(set(all_teams) - set(included_teams) -{team})
    return levels, excluded_teams


def get_trans():
    conferences = ['ACC', 'American Athletic', 'Big 12', 'Big Ten', 'Conference USA', 'FBS Independents',
                   'Mid-American', 'Mountain West', 'Pac-12', 'SEC', 'Sun Belt']
    game_data_url = 'https://api.collegefootballdata.com/games?year=2018'
    game_data = json.loads(requests.get(game_data_url).text)
    game_data = [g for g in game_data if g['home_conference'] in conferences and g['away_conference'] in conferences]
    winners = [g['away_team'] if g['away_points'] > g['home_points'] else g['home_team'] for g in game_data]
    losers = [g['home_team'] if g['away_points'] > g['home_points'] else g['away_team'] for g in game_data]
    app.trans = TransRank(winners, losers)
    teams_url = 'https://api.collegefootballdata.com/teams'
    team_info = json.loads(requests.get(teams_url).text)
    app.logos = {x['school']: x['logos'][0] for x in team_info if x['school'] in app.trans.teams}