import subprocess
import sys
import json
import webbrowser
import re
import datetime
from urllib import request
from bs4 import BeautifulSoup
from hashlib import md5


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
        self.matches = []


        self.sql_statements = []

        self.REGIONS = ['NA', 'EU', 'LCK', 'LPL', 'LMS', 'GPL', 'CBLoL', 'LJL', 'TCL', 'LCL', 'OPL', 'CIS']
        self.PFX = 'http://www.lolesports.com'

    def parse(self, url):
        # Handle loading from files:
        if self.do_load:
            with open(self.queue_file, 'r', encoding='utf-8') as qf:
                self.url_q = json.load(qf)
            with open(self.seen_file, 'r', encoding='utf-8') as sf:
                self.seen_urls = json.load(sf)
            with open(self.data_file, 'r', encoding='utf-8') as df:
                self.sql_statements = json.load(df)
            self.do_load = False
            url = self.url_q.pop(0)

        self.seen_urls.append(url)
        self.render(url)
        with open(self.dump_file, 'r', encoding='utf-8') as html_dump:
            html = html_dump.read()

        soup = BeautifulSoup(html, 'html.parser')

        if 'matches/' in url:
            series_id = self.gen_id(self.tournament_id + url.split('/')[-1])
            self.retrieve_series(url, series_id, soup)
        else:
            for link in soup.find_all('a'):
                h = link.get('href') if link.get('href') else ''
                if re.search('matches/|schedule/', h):
                    if (self.PFX + h) not in self.seen_urls and (self.PFX + h) not in self.url_q:
                        print('Enqueueing page: {0}'.format(h))
                        self.url_q.append(self.PFX + h)

        if len(self.url_q) > 0:
            self.parse(self.url_q.pop(0))
        else:
            print('Found these {0} teams: '.format((len(self.team_ids))))
            for t in self.team_ids:
                print(str(t))
            print('\nFound these {0} players: '.format(len(self.player_names)))
            for p in self.player_names:
                print(str(p))
            print('\nFound these {0} matches: '.format(len(self.matches)))
            for m in self.matches:
                print(str(m))
            print('\nCreated {0} SQL inserts'.format(len(self.sql_statements)))
            print('They are available in {0}'.format(self.data_file))
            with open(self.data_file, 'w', encoding='utf-8') as df:
                df.writelines(self.sql_statements)
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
                print('Fatal QT Error: Dumped progress to files, add file names and "True" to '
                      'end of command line arguments and rerun.')
                sys.exit(1)


    def sql_insert(self, table, args):
        insert_string = "INSERT INTO {0} VALUES(".format(table)
        if len(args) > 2:
            for arg in args[0:len(args) - 1]:
                insert_string += str(arg) + ', '
        insert_string += str(args[-1]) + ')\n'
        self.sql_statements.append(insert_string)

    def gen_id(self, s): # this fcking project I swear to god
        m = md5()
        m.update(s.encode('utf-8'))
        out = m.hexdigest()
        out = out[0:10]  # md5 hashes are really long and the first 10 digits will probably be unique
        out = '0x{}'.format(out)
        out = int(out, 16)

        return out

    def retrieve_tournament(self, url, name, location):
        webbrowser.open('https://youtu.be/5W_wd9Qf0IE?t=2s', new=2)
        self.tournament_id = starter_url.split('/')[5]  # Better hope this never changes
        t_year = re.match('[1-3][0-9]{3}', self.tournament_id)
        t_name = name
        t_loc = location

        self.sql_insert('tournaments', [self.tournament_id, t_year, t_name, t_loc])
        self.parse(url)

    def retrieve_team(self, url, team_id):
        print('Retrieving team at {0}'.format(url))
        self.render(url)
        with open(self.dump_file, 'r', encoding='utf-8') as html_dump:
            html = html_dump.read()
        soup = BeautifulSoup(html, 'html.parser')

        # Can't do region sometimes because team bio doesn't exist or won't load
        region = 'UNKNOWN'
        team_info = soup.find('div', class_='team-bio')
        if team_info:
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
                    region = 'UNKNOWN'
            else:
                region = region[0]

        team_name = soup.find('span', class_='team-name').get_text()
        self.sql_insert('teams', [team_id, region, team_name])
        self.sql_insert('participates', [self.tournament_id, team_id, 'UNKNOWN'])
        
    def retrieve_series(self, url, series_id, soup):
        if series_id not in self.series_ids:
            bo_count = soup.select_one('span.game-num')
            if bo_count:
                bo_count = bo_count.get_text()
            else:
                bo_count = 1
            t1_box = soup.select_one('div.blue')
            t1_link = self.PFX + t1_box.select_one('a.ember-view').get('href')
            t1_id = t1_box.select_one('div.team-name.hide-for-medium-up').get_text()
            t2_box = soup.select_one('div.red')
            t2_link = self.PFX + t2_box.select_one('a.ember-view').get('href')
            t2_id = t2_box.select_one('div.team-name.hide-for-medium-up').get_text()

            if t1_id not in self.team_ids:
                self.team_ids.append(t1_id)
                self.retrieve_team(t1_link, t1_id)
            if t2_id not in self.team_ids:
                self.team_ids.append(t2_id)
                self.retrieve_team(t2_link, t2_id)

            stats_links = soup.find_all('a', class_='stats-link')

            for i in range(0, len(stats_links)):
                print('Found match details for ' + url.split('/')[-1])
                self.retrieve_match(stats_links[i].get('href'), i+1, url, soup, series_id, t1_id, t2_id)

            self.series_ids.append(series_id)
            self.sql_insert('series', [series_id, bo_count])
            self.sql_insert('organizes', [self.tournament_id, series_id])

    def retrieve_match(self, match_path, match_number, parent_url, soup, series_id, t1_id, t2_id):

        self.matches.append(parent_url.split('matches/')[1])

        def pid_to_sname(json_object, pid):
            return json_object['participantIdentities'][pid - 1]['player']['summonerName']

        match_date = soup.select_one('div.match-date').contents[2].strip(' ')
        match_date = datetime.datetime.strptime(match_date, '– %b %d, %Y\n').strftime('%Y-%m-%d')

        self.sql_insert('matches', [series_id, match_number, match_date])
        self.sql_insert('competes', [series_id, t1_id, True])
        self.sql_insert('competes', [series_id, t2_id, False])

        match_path = match_path.split('details/')[1]
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
        t1_riftheralds = t1_data['riftHeraldKills']
        t1_barons = t1_data['baronKills']
        t1_dragons = t1_data['dragonKills']
        t1_nexus = 1 if (t1_data['win'] == 'Win') else 0

        t2_data = json_data['teams'][1]
        t2_inhibitors = t2_data['inhibitorKills']
        t2_towers = t2_data['towerKills']
        t2_riftheralds = t2_data['riftHeraldKills']
        t2_barons = t2_data['baronKills']
        t2_dragons = t2_data['dragonKills']
        t2_nexus = 1 if (t2_data['win'] == 'Win') else 0

        self.sql_insert('scores', [t1_id, series_id, match_number, t1_inhibitors, t1_towers, t1_riftheralds,
                                   t1_barons, t1_dragons, t1_nexus])
        self.sql_insert('scores', [t2_id, series_id, match_number, t2_inhibitors, t2_towers, t2_riftheralds,
                                   t2_barons, t2_dragons, t2_nexus])
        # BANS
        for ban in t1_data['bans']:
            self.sql_insert('bans', [series_id, match_number, ban['championId'], ban['pickTurn']])

        for ban in t2_data['bans']:
            self.sql_insert('bans', [series_id, match_number, ban['championId'], ban['pickTurn']])

        # PLAYS (players are listed by summonerName only)
        for p in json_data['participants']:
            p_name = pid_to_sname(json_data, p['participantId'])
            p_name = p_name.split(' ', 1)[1] # Get rid of TeamID
            if p_name not in self.player_names:
                self.player_names.append(p_name)
                print('Found player {0}'.format(p_name))
                self.sql_insert('players', [p_name])
                if p['teamId'] == 100:
                    self.sql_insert('registers', [p_name, t1_id, "date('1970-01-01')"])
                elif p['teamId'] == 200:
                    self.sql_insert('registers', [p_name, t2_id, "date('1970-01-01')"])
                else:
                    raise ValueError('Could not identify player team')

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
            self.sql_insert('plays', [series_id, match_number, p_name, p['championId'], p_role,
                                                            pstats['kills'], pstats['deaths'], pstats['assists'],
                                                            pstats['totalDamageDealtToChampions'],
                                                            pstats['wardsPlaced'],
                                                            pstats['wardsKilled'], pstats['totalMinionsKilled'],
                                                            pstats['neutralMinionsKilledTeamJungle'],
                                                            pstats['neutralMinionsKilledEnemyJungle'],
                                                            pstats['goldEarned']])

        # INTERACTS

        for frame in json_timeline['frames']:
            for e in frame['events']:
                is_buy = 1 if e['type'] == 'ITEM_PURCHASED' else 0
                if e['type'] == 'ITEM_PURCHASED' or e['type'] == 'ITEM_SOLD':
                    self.sql_insert('interacts', [series_id, match_number,
                                                                 pid_to_sname(json_data, e['participantId']).split(' ',1)[1],
                                                                 e['itemId'], e['timestamp'], is_buy])

if __name__ == '__main__':
    starter_url = sys.argv[1]
    tournament_name = sys.argv[2]
    location = sys.argv[3]
    if len(sys.argv) > 4:
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
        data_file = 'tournament_data.sql'
    if len(sys.argv) > 6:
        do_load = sys.argv[6]
    else:
        do_load = False

    parser = TournamentParser(dump_file, url_queue_file, seen_url_file, data_file, do_load)
    parser.retrieve_tournament(starter_url, tournament_name, location)
