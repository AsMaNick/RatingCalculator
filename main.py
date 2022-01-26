import os
import sys
import time
import json
import requests
import jsonpickle
import onlinejudge
from tqdm import tqdm
from datetime import datetime


class User:
    def __init__(self, name, codeforces_handle, atcoder_handle, tlx_handle, is_official):
        def filter_handle(handle):
            if len(handle) <= 2 or handle.lower() == 'нет':
                return ''
            return handle
        self.name = name
        self.codeforces_handle = filter_handle(codeforces_handle)
        self.atcoder_handle = filter_handle(atcoder_handle)
        self.tlx_handle = filter_handle(tlx_handle)
        self.is_official = is_official

    def __str__(self):
        handles = ', '.join(f'{online_judge}: {self.get_handle(online_judge)}' for online_judge in online_judges if self.get_handle(online_judge) != '')
        return f'{self.name}, {handles}, official: {self.is_official}'

    def __repr__(self):
        return self.__str__()

    def get_handle(self, online_judge):
        if online_judge == 'codeforces':
            return self.codeforces_handle
        elif online_judge == 'atcoder':
            return self.atcoder_handle
        elif online_judge == 'tlx':
            return self.tlx_handle
        raise NotImplementedError


class StandingsRow:
    def __init__(self, user, place, points, penalty, is_rated):
        self.user = user
        self.place = place
        self.points = points
        self.penalty = penalty
        self.is_rated = is_rated

    def __str__(self):
        return f'{self.place}) {self.user}: ({self.points}, {self.penalty}, rated = {self.is_rated}, official = {self.user.is_official})'


class Standings:
    def __init__(self, online_judge, contest_id, start_date):
        assert(online_judge in online_judges)
        self.online_judge = online_judge
        self.contest_id = contest_id
        self.start_date = start_date
        self.results = []
        self.last_official_id = -1
        self.official_participants = 0

    def add_result(self, handle, points, penalty, is_rated):
        user = handles_by_judges[self.online_judge][handle]
        place = 1
        if self.last_official_id != -1:
            place = self.results[self.last_official_id].place
            if points != self.results[self.last_official_id].points or penalty != self.results[self.last_official_id].penalty:
                place = self.official_participants + 1
        if user.is_official:
            self.official_participants += 1
            self.last_official_id = len(self.results)
        self.results.append(StandingsRow(user, place, points, penalty, is_rated))

    def empty(self):
        for result in self.results:
            if result.user.is_official and result.points != 0:
                return False
        return True

    def __str__(self):
        return '\n'.join([str(row) for row in self.results])


def load_users():
    spreadsheet_id = open('data/spreadsheet_id.txt', 'r').read()
    google_api_key = open('data/google_api_key.txt', 'r').read()
    table_name = open('data/table_name.txt', 'r').read()
    url = f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{table_name}?alt=json&key={google_api_key}'
    data = requests.get(url).json()['values']
    users = [User(row[1], row[3], row[4], row[5], row[0] != '-') for row in data[3:]]
    return users


def get_codeforces_standings(contest_id):
    url = f'https://codeforces.com/api/contest.standings?contestId={contest_id}&showUnofficial=true'
    response = requests.get(url)
    if response.status_code != 200:
        print(f'{response.status_code}: incorrect parameters (check contest id), try again')
        exit(1)
    data = response.json()
    standings = Standings('codeforces', contest_id, datetime.utcfromtimestamp(data['result']['contest']['startTimeSeconds']).strftime('%d.%m.%Y'))
    for row in data['result']['rows']:
        if row['party']['participantType'] != 'OUT_OF_COMPETITION' and row['party']['participantType'] != 'CONTESTANT':
            continue
        members = row['party']['members']
        handle = members[0]['handle']
        if len(members) != 1 or handle not in handles_by_judges['codeforces']:
            continue
        standings.add_result(handle, row['points'], row['penalty'], row['party']['participantType'] == 'CONTESTANT')
    return standings


def get_atcoder_standings(contest_id):
    def get_credentials():
        if os.path.isfile('data/atcoder_credentials.txt'):
            f = open('data/atcoder_credentials.txt', 'r')
            credentials = f.read().split()
            f.close()
            if len(credentials) == 2:
                return tuple(credentials)
        username = input('Enter atcoder username: ')
        from stdiomask import getpass
        password = getpass(prompt='Enter atcoder password: ')
        return username, password
        
    def save_credentials(username, password):
        f = open('data/atcoder_credentials.txt', 'w')
        print(username, password, file=f)
        f.close()
        
    def login():
        atcoder = onlinejudge.service.atcoder.AtCoderService()
        while True:
            try:
                username, password = get_credentials()
                atcoder.login(get_credentials=lambda username=username, password=password: (username, password))
                save_credentials(username, password)
                break
            except onlinejudge.type.LoginError:
                print('Incorrect username or password, please try again')
        session=onlinejudge.service.atcoder.utils.get_default_session()
        return session
        
    def get_contest_date(session, contest_id):
        url = f'https://atcoder.jp/contests/{contest_id}'
        response = session.get(url, allow_redirects=False).text
        pos = response.find('<small class="contest-duration">')
        pos = response.find('</time>', pos)
        pos = response.rfind('>', 0, pos) + 1
        year = response[pos:pos + 4]
        month = response[pos + 5:pos + 7]
        day = response[pos + 8:pos + 10]
        return f'{day}.{month}.{year}'
        
    session = login()
    start_date = get_contest_date(session, contest_id)
    url = f'https://atcoder.jp/contests/{contest_id}/standings/json'
    response = session.get(url, allow_redirects=False)
    if response.status_code != 200:
        print(f'{response.status_code}: incorrect parameters (check contest id), try again')
        exit(1)
    data = response.json()
    standings = Standings('atcoder', contest_id, start_date)
    for row in data['StandingsData']:
        if not row['IsRated'] and False:
            continue
        handle = row['UserScreenName']
        if handle not in handles_by_judges['atcoder']:
            continue
        if not row['TotalResult']['Count']:
            continue
        points = row['TotalResult']['Score'] // 100
        penalty = row['TotalResult']['Elapsed'] // 10 ** 9 + row['TotalResult']['Penalty'] * 5 * 60
        standings.add_result(handle, points, penalty, row['IsRated'])
    return standings


def get_tlx_standings(contest_id):
    def get_info(slug):
        url = f'https://api.tlx.toki.id/v2/contests?page=1'
        response = requests.get(url)
        if response.status_code != 200:
            print(f'{response.status_code}: something went wrong, try again')
            exit(1)
        data = response.json()
        for contest in data['data']['page']:
            if contest['slug'] == slug:
                return contest['jid'], contest['beginTime'] // 1000
        print(f"Can't find contest jid by slug: {slug}")
        exit(1)

    contest_jid, start_time = get_info(contest_id)
    url = f'https://api.tlx.toki.id/v2/contests/{contest_jid}/scoreboard?frozen=false&showClosedProblems=false'
    response = requests.get(url)
    if response.status_code != 200:
        print(f'{response.status_code}: incorrect parameters (check contest id), try again')
        exit(1)
    data = response.json()
    standings = Standings('tlx', contest_id, datetime.utcfromtimestamp(start_time).strftime('%d.%m.%Y'))
    for row in data['data']['scoreboard']['content']['entries']:
        handle = row['contestantUsername']
        if handle not in handles_by_judges['tlx']:
            continue
        standings.add_result(handle, row['totalPoints'], row['totalPenalties'], True)
    return standings


def get_standings(online_judge, contest_id):
    if online_judge == 'codeforces':
        return get_codeforces_standings(contest_id)
    elif online_judge == 'atcoder':
        return get_atcoder_standings(contest_id)
    elif online_judge == 'tlx':
        return get_tlx_standings(contest_id)
    else:
        raise NotImplementedError


def post_standings(standings, sheet_name):
    print(standings)
    if standings.empty():
        print('Standings are empty')
        return
    spreadsheet_app_id = open('data/spreadsheet_app_id.txt', 'r').read()
    url = f'https://script.google.com/macros/s/{spreadsheet_app_id}/exec'
    data = jsonpickle.decode(jsonpickle.encode(standings, unpicklable=False))
    data['sheet_name'] = sheet_name
    data['action'] = 'add_standings'
    response = requests.post(url, json=data)
    print(response.status_code)


def create_standings(online_judge, contest_id, sheet_name):
    standings = get_standings(online_judge, contest_id)
    post_standings(standings, sheet_name)


def read_option(prompt, options, case_sensetive=False):
    option = input(prompt)
    if not case_sensetive:
        option = option.lower()
    while option not in options:
        print(f'Incorrect option, try again')
        option = input(prompt)
        if not case_sensetive:
            option = option.lower()
    return option


def read_date(prompt):
    while True:
        try:
            str_date = input(prompt)
            date = datetime.strptime(str_date, '%d.%m.%Y')
            return date
        except Exception as e:
            print('Date should be in format dd.mm.yyyy')


def guess_online_judge(contest_id):
    if contest_id[:3] in ['abc', 'arc', 'agc']:
        return 'atcoder'
    if contest_id.find('troc') != -1:
        return 'tlx'
    return 'codeforces'


def create_standings_from_user_answers():
    contest_id = input('Enter contest id: ')
    online_judge = guess_online_judge(contest_id)
    if online_judge == 'atcoder':
        sheet_name = f'{contest_id[:3].upper()} #{contest_id[3:]}'
    elif online_judge == 'tlx':
        division = ''
        contest_number = contest_id
        if contest_number.find('div') != -1:
            division = f' (Div. {contest_number[-1]})'
            contest_number = contest_number[:-6]
        sheet_name = f'TROC #{contest_number[5:]}{division}'
    else:
        sheet_name = input('Enter sheet name: ')
    if read_option(f'Create standings "{sheet_name}" with data from {online_judge}/{contest_id}? (yes/no) ', ['y', 'n', 'yes', 'no'])[0] == 'y':
        create_standings(online_judge, contest_id, sheet_name)


def update_ratings(online_judge, start_date, C_platform, D_platform):
    def get_contest_history_url(online_judge, handle):
        if online_judge == 'codeforces':
            return f'https://codeforces.com/api/user.rating?handle={handle}'
        elif online_judge == 'atcoder':
            return f'https://atcoder.jp/users/{handle}/history/json'
        elif online_judge == 'tlx':
            return f'https://api.tlx.toki.id/v2/contest-history/public?username={handle}'
        raise NotImplementedError
        
    def contest_history_iterator(online_judge, data):
        if online_judge == 'codeforces':
            for row in data['result']:
                yield row['ratingUpdateTimeSeconds'], row['newRating']
        elif online_judge == 'atcoder':
            for row in data:
                timestamp = datetime.strptime(row['EndTime'][:10], '%Y-%m-%d').timestamp()
                yield timestamp, row['NewRating']
        elif online_judge == 'tlx':
            for row in data['data']:
                timestamp = data['contestsMap'][row['contestJid']]['beginTime'] // 1000
                try:
                    new_rating = row['rating']['publicRating']
                except Exception as e:
                    new_rating = 0
                yield timestamp, new_rating
                
    start_timestamp = start_date.timestamp()
    wait_time = 5
    ratings = []
    for user in tqdm(users):
        handle = user.get_handle(online_judge)
        if handle == '':
            continue
        while True:
            url = get_contest_history_url(online_judge, handle)
            response = requests.get(url)
            if response.status_code == 503:
                time.sleep(wait_time)
                continue
            if response.status_code != 200:
                print(f'Something went wrong, status code = {response.status_code}')
                print(f'Response text: {response.text}')
                time.sleep(wait_time)
                print('Trying to repeat query')
                continue
            data = response.json()
            old_last_rating, old_max_rating, current_rating = 0, 0, 0
            new_ratings = []
            cnt_rated = 0
            for timestamp, new_rating in contest_history_iterator(online_judge, data):
                if timestamp < start_timestamp:
                    old_last_rating = new_rating
                    old_max_rating = max(old_max_rating, new_rating)
                elif current_rating != new_rating:
                    new_ratings.append(new_rating)
                if cnt_rated < C_platform:
                    old_max_rating = max(old_max_rating, new_rating)
                cnt_rated += current_rating != new_rating
                current_rating = new_rating
            if len(new_ratings) == 0:
                new_ratings.append(current_rating)
            ratings.append({
                'handle': handle,
                'old_rating': max(old_max_rating - D_platform, old_last_rating),
                'new_rating': max(new_ratings[-((len(new_ratings) + 3) // 4):])
            })
            break
    print(*ratings, sep='\n')
    data = {
        'ratings': ratings,
        'action': 'update_ratings',
        'online_judge': online_judge
    }
    spreadsheet_app_id = open('data/spreadsheet_app_id.txt', 'r').read()
    url = f'https://script.google.com/macros/s/{spreadsheet_app_id}/exec'
    response = requests.post(url, json=data)
    print(response.status_code)


def update_ratings_from_user_answers():
    C = {
        'codeforces': 10,
        'atcoder': 10,
        'tlx': 5,
    }
    D = {
        'codeforces': 200,
        'atcoder': 150,
        'tlx': 200,
    }
    online_judge = read_option(f'Select online judge ({", ".join(online_judges[:-1])} or {online_judges[-1]}): ', online_judges)
    start_date = read_date('Enter start date (dd.mm.yyyy) for rating calculation: ')
    update_ratings(online_judge, start_date, C[online_judge], D[online_judge])


online_judges = ['codeforces', 'atcoder', 'tlx']
users = load_users()
handles_by_judges = {
    online_judge: {user.get_handle(online_judge) : user for user in users if user.get_handle(online_judge) != ''} for online_judge in online_judges
}
if len(sys.argv) != 2 or sys.argv[1] not in ['-s', '-r']:
    print('There should be exactly one argument: -s for adding standings, -r for updating ratings')
    exit()
if sys.argv[1] == '-s':
    create_standings_from_user_answers()
else:
    update_ratings_from_user_answers()