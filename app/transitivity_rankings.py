import pandas
import numpy
import networkx


class TransRank:
    def __init__(self, winners, losers, distances=None):
        win_graph = networkx.DiGraph()
        win_graph.add_edges_from(zip(winners, losers))
        loss_graph = networkx.DiGraph()
        loss_graph.add_edges_from(zip(losers, winners))
        self.teams = sorted(list(win_graph.nodes()))
        win_paths = self.get_paths_from_graph(win_graph)
        loss_paths = self.get_paths_from_graph(loss_graph, reverse=True)
        df_cols = ['trans_wins', 'avg_win_len', 'win_score', 'win_rank', 'trans_losses' 'avg_loss_len', 'loss_score', 'loss_rank',
                   'avg_rank', 'comb_rank']
        rank_df = pandas.DataFrame(index=self.teams, columns=df_cols)
        rank_df['trans_wins'] = [len(win_paths[t]) for t in self.teams]
        rank_df['trans_losses'] = [len(loss_paths[t]) for t in self.teams]
        rank_df['avg_win_len'] = [len(self.teams) if len(win_paths[t]) == 0
                                  else numpy.mean([len(win_paths[t][p]) - 1 for p in win_paths[t]]) for t in self.teams]
        rank_df['avg_loss_len'] = [0 if len(loss_paths[t]) == 0 else numpy.mean([len(loss_paths[t][p]) - 1
                                                                                 for p in loss_paths[t]]) for t in self.teams]
        rank_df['win_score'] = rank_df['trans_wins'] - rank_df['avg_win_len'] / (max(rank_df['avg_win_len']) + 1)
        rank_df['loss_score'] = -(rank_df['trans_losses'] - rank_df['avg_loss_len'] / (max(rank_df['avg_loss_len']) + 1))
        rank_df['win_rank'] = [sum(rank_df['win_score'] > rank_df.loc[t, 'win_score']) + 1 for t in self.teams]
        rank_df['loss_rank'] = [sum(rank_df['loss_score'] > rank_df.loc[t, 'loss_score']) + 1 for t in self.teams]
        rank_df['avg_rank'] = rank_df[['win_rank', 'loss_rank']].mean(axis=1)
        rank_df['comb_rank'] = [sum(rank_df['avg_rank'] < rank_df.loc[t, 'avg_rank']) + 1 for t in self.teams]
        rank_df['wins'] = pandas.Series(dict(win_graph.out_degree()))
        rank_df['losses'] = pandas.Series(dict(loss_graph.out_degree()))
        rank_df = rank_df[['comb_rank', 'win_rank', 'loss_rank', 'avg_rank', 'wins', 'trans_wins', 'avg_win_len',
                           'losses', 'trans_losses', 'avg_loss_len']]
        rank_df = rank_df.sort_values('comb_rank')
        if distances is not None:
            for e in win_graph.edges():
                win_graph[e[0]][e[1]]['weight'] = distances[e[0], e[1]]
            for e in loss_graph.edges():
                loss_graph[e[0]][e[1]]['weight'] = distances[e[0], e[1]]
            self.win_geo_paths = networkx.all_pairs_dijkstra_path(win_graph)
            self.loss_geo_paths = networkx.all_pairs_dijkstra_path(loss_graph)
        self.win_paths = win_paths
        self.loss_paths = loss_paths
        self.rank_df = rank_df

    def get_paths_from_graph(self, graph, reverse=False):
        paths = {x[0]: x[1] for x in networkx.all_pairs_shortest_path(graph)}
        paths = {t: {p: paths[t][p] for p in paths[t] if p != t} for t in self.teams}
        if reverse:
            for t in paths:
                paths[t] = {s: paths[t][s][::-1] for s in paths[t]}
        return paths

    def team_link(self, team):
        return '/' + team.replace(' ', '_')

    def get_html_table(self, images=None):
        display_header_names = {'comb_rank': 'Rank', 'win_rank': 'Win Rank', 'loss_rank': 'Loss Rank',
                                'trans_wins': 'Trans Wins', 'trans_losses': 'Trans Losses', 'avg_win_len': 'Avg Trans Win',
                                'avg_loss_len': 'Avg Trans Loss', 'avg_rank': 'Avg Rank'}
        html_df = self.rank_df.rename(columns=display_header_names)
        html_df['Avg Trans Win'] = [self.style_float(x) for x in html_df['Avg Trans Win']]
        html_df['Avg Trans Loss'] = [self.style_float(x) for x in html_df['Avg Trans Loss']]
        if images is not None:
            html_df.index = [f'<img src="{images[t]}" class="team-logo">&nbsp&nbsp<a href="{self.team_link(t)}">{t}</a>'
                             for t in html_df.index]
        html_df.index = [x + f" ({html_df['wins'][x]}-{html_df['losses'][x]})" for x in html_df.index]
        html_df = html_df.drop(['wins', 'losses'], axis=1)
        html_table = html_df.to_html(classes=['table-striped', 'table-bordered', 'full-width'], table_id='rank-table',
                                     escape=False)
        return html_table

    def style_float(self, f):
        return '%.2f' % f