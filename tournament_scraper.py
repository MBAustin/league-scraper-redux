import subprocess
import sys
import json
import re
import datetime
from urllib import request
from bs4 import BeautifulSoup


class TournamentParser:
    def __init__(self, dump_file, queue_file, seen_file, data_file, do_load):
        self.do_load = do_load
        self.dump_file = dump_file
        self.queue_file = queue_file
        self.seen_file = seen_file
        self.data_file = data_file

        self.url_q = []
        self.seen_urls = []

        self.player_names = []
        self.team_ids = []
        self.series_ids = []

        self.sql_statements = []

        self.REGIONS = ['NA', 'EU', 'LCK', 'LPL', 'LMS', 'GPL', 'CBLoL', 'LJL', 'TCL', 'LCL', 'OPL', 'CIS']

    def parse(self, url):
        starting_url = url
        if self.do_load:
            with open(self.queue_file, 'r', encoding='utf-8') as qf:
                self.url_q = json.load(qf)
            with open(self.seen_file, 'r', encoding='utf-8') as sf:
                self.seen_urls = json.load(sf)
            with open(self.data_file, 'r', encoding='utf-8') as df:
                self.sql_statements = json.load(df)
            self.do_load = False
            starting_url = self.url_q.pop(0)

        print('Parsing {0}'.format(starting_url))
        self.seen_urls.append(starting_url)
        self.render(url)
        # self.parse_helper(url)
        with open(self.dump_file, 'r', encoding='utf-8') as html_dump:
            html = html_dump.read()
        pfx = 'http://www.lolesports.com'
        soup = BeautifulSoup(html, 'html.parser')
        links = [link for link in soup.find_all('a')]

        for link in links:
            h = link.get('href') if link.get('href') else ''
            if re.search('matches/|schedule/|stats/', h):
                if (pfx + h) not in self.seen_urls and (pfx + h) not in self.url_q:
                    print('Enqueueing schedule page: {0}'.format(h))
                    self.url_q.append(pfx + h)
            elif 'match-details' in h:
                print('Found match details for {0}'.format(url))
                self.retrieve_match(h, url, soup)
            elif 'stats/' in url  and 'teams/' in h:
                team_id = link.get_text()
                if team_id not in self.team_ids:
                    self.team_ids.append(team_id)
                    print('Found team {0}'.format(team_id))
                    self.retrieve_team(pfx + h, team_id)

        if len(self.url_q) > 0:
            self.parse(self.url_q.pop(0))
        else:
            print('Created {0} SQL inserts'.format(len(self.sql_statements)))
            print('They are available in {0}'.format(self.data_file))
            with open(self.data_file, 'w', encoding='utf-8') as df:
                json.dump(self.sql_statements, df)
            sys.exit(0)


    def render(self, url):
        args = ['python', 'render.py', url, self.dump_file]
        # QT is a piece of sh*t library and prone to crashes, try it again
        # and dump progress to files if it can't recover:
        try:
            subprocess.check_call(args)
        except:
            print('Live! LIIIIVE!')
            try:
                subprocess.check_call(args)
            except:
                print('Snake? Snake?! SNAAAAAAAKE')
                self.url_q.append(url)
                self.seen_urls.remove(url)
                with open(self.queue_file, 'w', encoding='utf-8') as qf:
                    json.dump(self.url_q, qf)
                with open(self.seen_file, 'w', encoding='utf-8') as sf:
                    json.dump(self.seen_urls, sf)
                with open(self.data_file, 'w', encoding='utf-8') as df:
                    json.dump(self.sql_statements, df)
                print('Fatal QT Error: Dumped progress to files, add file names and "True" to \
                       end of command line arguments and rerun.')
                sys.exit(1)

    # def parse_helper(self, url):
    #     with open(self.dump_file, 'r', encoding='utf-8') as html_dump:
    #         html = html_dump.read()
    #     pfx = 'http://www.lolesports.com'
    #     soup = BeautifulSoup(html, 'html.parser')
    #     links = [link for link in soup.find_all('a')]
    #
    #     for link in links:
    #         h = link.get('href') if link.get('href') else ''
    #         if re.search('matches/|schedule/|stats/', h):
    #             if (pfx + h) not in self.seen_urls and (pfx + h) not in self.url_q:
    #                 print('Enqueueing schedule page: {0}'.format(h))
    #                 self.url_q.append(pfx + h)
    #         elif 'match-details' in h:
    #             print('Found match details for {0}'.format(url))
    #             self.retrieve_match(h, url, soup)
    #         elif 'stats/' in url  and 'teams/' in h:
    #             team_id = link.get_text()
    #             if team_id not in self.team_ids:
    #                 self.team_ids.append(team_id)
    #                 print('Found team {0}'.format(team_id))
    #                 self.retrieve_team(pfx + h, team_id)
    #
    #     if len(self.url_q) > 0:
    #         self.parse(self.url_q.pop(0))
    #     else:
    #         print('Created {0} SQL inserts'.format(len(self.sql_statements)))
    #         print('They are available in {0}'.format(self.data_file))
    #         with open(self.data_file, 'w', encoding='utf-8') as df:
    #             json.dump(self.sql_statements, df)
    #         sys.exit(0)


    def sql_insert(self, table, args):
        insert_string = "INSERT INTO {0} VALUES(".format(table)
        if len(args) > 2:
            for arg in args[0:len(args) - 1]:
                insert_string += str(arg) + ', '
        insert_string += str(args[-1]) + ')\n'
        self.sql_statements.append(insert_string)


    def retrieve_tournament(self, url, name, location):
        self.tournament_id = starter_url.split('/')[5] # Better hope this never changes
        t_year = re.match('[1-3][0-9]{3}', self.tournament_id)
        t_name = name
        t_loc = location

        # self.sql_statements.append("INSERT INTO tournaments VALUES({0}, {1}, {2}, {3})\n".format(
        #     self.tournament_id, t_year, t_name, t_loc
        # ))
        self.sql_insert('tournaments', [self.tournament_id, t_year, t_name, t_loc])
        self.parse(url)


    def retrieve_team(self, url, id):
        self.render(url)
        with open(self.dump_file, 'r', encoding='utf-8') as html_dump:
            html = html_dump.read()
        soup = BeautifulSoup(html)

        team_info = soup.find('div', {'class' : 'team-bio'})
        region = [r for r in self.REGIONS if team_info.find_all(r)]

        if len(region) > 1:
            raise NameError('Multiple regions found for team')
        elif len(region) == 0:
            if team_info.find_all('Brazil'):
                region = 'CBLoL'
            elif team_info.find_all(re.compile('KeSPA|Champions Spring|Champions Summer')):
                region = 'LCK'
            elif team_info.find_all(re.compile('Turkey|Turkish')):
                region = 'TCL'
            elif team_info.find_all(re.compile('IWC|International Wild Card')):
                region = 'IWC'
            else:
                region = 'NULL'
        else:
            region = region[0]

        team_name = soup.find('span', {'class' : 'team-name'}).get_text()
        self.sql_insert('teams', [id, region, team_name])
        self.sql_insert('participates', [self.tournament_id, id, 'UNKNOWN'])
        players = soup.find_all('div', {'class': 'player-row'})
        for player in players:
            player_name = player.find('SUMMONER').next_sibling
            if player_name not in self.player_names:
                self.player_names.append(player_name)
                print('Found player {0}'.format(player_name))
                self.sql_insert('players', [player_name])
                self.sql_insert('registers', [player_name, id, "date('1970-01-01')"])

    def retrieve_series(self, soup, url):
        series_id = ord(self.tournament_id) + ord(url.split('/')[-1])  # convert the unique bit of the url to an integer
        bo_count = soup.find('span', class_='game-num').get_text()
        bo_count = bo_count.split('of ')[1]

        if series_id not in self.series_ids:
            self.series_ids.append(series_id)
            self.sql_insert('series', [series_id, bo_count])
            self.sql_insert('organizes', [self.tournament_id, series_id])

    def retrieve_match(self, match_path, parent_url, soup):
        def pid_to_sname(json_object, pid):
            return json_object['participantIdentities'][pid - 1]['player']['summonerName']

        t1_box = soup.select('div.large-7.large-pull-5.small-12.columns.blue-team.ungutter')
        print('t1_box is ' + str(t1_box))
        team1Id = t1_box[3].get_text()
        t2_box = soup.select('div.large-7.large-pull-5.small-12.columns.red-team.ungutter')
        team2Id = t2_box[3].get_text()


        match_number = soup.select('span.game-num').get_text()
        match_number = match_number.split(' ')[1]

        match_date = soup.select('div.match-date').contents[2]
        match_date = datetime.datetime.strptime(match_date, '%b %-d, %Y').strftime('%Y-%m-%d')

        series_Id = ord(self.tournament_id) + ord(parent_url.split('/')[-1])

        self.sql_insert('matches', [series_Id, match_number, match_date])
        self.sql_insert('competes', [series_Id, team1Id, True])
        self.sql_insert('competes', [series_Id, team2Id, False])

        match_url = 'https://acs.leagueoflegends.com/v1/stats/game/' + match_path

        raw_data = request.urlopen(match_url).read()
        raw_data = raw_data.decode('utf-8')
        json_data = json.loads(raw_data)

        split_path = match_path.split('?')
        timeline_url = 'https://acs.leagueoflegends.com/v1/stats/game/' + split_path[0] + '/timeline?' + split_path[1]
        raw_timeline = request.urlopen(timeline_url).read()
        raw_timeline = raw_timeline.decode('utf-8')
        json_timeline = json.loads(raw_timeline)

        # SCORES
        t1_data = json_data['teams'][0]
        t1_inhibitors = t1_data['inhibitorKills']
        t1_towers = t1_data['towerKills']
        t1_riftHeralds = t1_data['riftHeraldKills']
        t1_barons = t1_data['baronKills']
        t1_dragons = t1_data['dragonKills']
        t1_nexus = 1 if (t1_data['win'] == 'Win') else 0

        t2_data = json_data['teams'][1]
        t2_inhibitors = t2_data['inhibitorKills']
        t2_towers = t2_data['towerKills']
        t2_riftHeralds = t2_data['riftHeraldKills']
        t2_barons = t2_data['baronKills']
        t2_dragons = t2_data['dragonKills']
        t2_nexus = 1 if (t2_data['win'] == 'Win') else 0

        self.sql_insert('scores', [team1Id, series_Id, match_number, t1_inhibitors, t1_towers, t1_riftHeralds,
                        t1_barons, t1_dragons, t1_nexus])
        self.sql_insert('scores', [team2Id, series_Id, match_number, t2_inhibitors, t2_towers, t2_riftHeralds,
                                   t2_barons, t2_dragons, t2_nexus])
        # BANS
        for ban in t1_data['bans']:
            self.sql_insert('bans', [series_Id, match_number, ban['championID'], ban['pickTurn']])

        for ban in t2_data['bans']:
            self.sql_insert('bans', [series_Id, match_number, ban['championID'], ban['pickTurn']])


        # PLAYS (players are listed by summonerName only)
        for p in json_data['participants']:
            p_name = pid_to_sname(json_data, p['participantId'])

            role = p['timeline']['role']
            lane = p['timeline']['lane']
            p_role = "NONE"
            if lane == 'TOP':
                p_role = "Top"
            elif lane == 'MIDDLE':
                p_role = "Mid"
            elif lane == 'JUNGLE':
                p_role = "Jungle"
            elif role == 'DUO_CARRY':
                p_role = "ADC"
            elif role == 'DUO_SUPPORT':
                p_role = "Support"

            pstats = p['stats']
            self.sql_insert('plays', [series_Id, match_number, p_name, p['championID'], p_role,
                                                            pstats['kills'], pstats['deaths'], pstats['assists'],
                                                            pstats['totalDamageDealtToChampions'],
                                                            pstats['wardsPlaced'],
                                                            pstats['wardsDestroyed'], pstats['totalMinionsKilled'],
                                                            pstats['neutralMinionsKilledTeamJungle'],
                                                            pstats['neutralMinionsKilledEnemyJungle'],
                                                            pstats['goldEarned']])

            # INTERACTS
            for frame in json_timeline['frames']:
                for e in frame['events']:
                    is_buy = 1 if e['type'] == 'ITEM_PURCHASED' else 0
                    self.sql_insert('interacts', [series_Id, match_number,
                                                                 pid_to_sname(json_data, e['participantId']),
                                                                 e['itemId'], e['timeStamp'], is_buy])

        return self.sql_statements



if __name__ == '__main__':
    starter_url = sys.argv[1]
    tournament_name = sys.argv[2]
    location = sys.argv[3]
    if len(sys.argv) > 4 :
        dump_file = sys.argv[2]
    else:
        dump_file = 'html_dump.html'
    if len(sys.argv) > 3:
        url_queue_file = sys.argv[3]
    else:
        url_queue_file = 'url_queue.json'
    if len(sys.argv) > 4:
        seen_url_file = sys.argv[4]
    else:
        seen_url_file = 'seen_urls.json'
    if len(sys.argv) > 5:
        data_file = sys.argv[5]
    else:
        data_file = 'tournament_data.json'
    if len(sys.argv) > 6:
        do_load = sys.argv[6]
    else:
        do_load = False

    parser = TournamentParser(dump_file, url_queue_file, seen_url_file, data_file, do_load)
    parser.retrieve_tournament(starter_url, tournament_name, location)
