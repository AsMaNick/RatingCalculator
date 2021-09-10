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
    def __init__(self, name, codeforces_handle, atcoder_handle):
        def filter_handle(handle):
            if len(handle) <= 2 or handle.lower() == 'нет':
                return ''
            return handle
        self.name = name
        self.codeforces_handle = filter_handle(codeforces_handle)
        self.atcoder_handle = filter_handle(atcoder_handle)

    def __str__(self):
        return self.name + ', codeforces: ' + self.codeforces_handle + ', atcoder: ' + self.atcoder_handle

    def __repr__(self):
        return self.__str__()


class StandingsRow:
    def __init__(self, user, place, points, penalty, is_rated):
        self.user = user
        self.place = place
        self.points = points
        self.penalty = penalty
        self.is_rated = is_rated

    def __str__(self):
        return f'{self.place}) {self.user}: ({self.points}, {self.penalty}, rated = {self.is_rated})'


class Standings:
    def __init__(self, online_judge, contest_id, start_date):
        self.online_judge = online_judge
        self.contest_id = contest_id
        self.start_date = start_date
        self.results = []

    def add_result(self, handle, points, penalty, is_rated):
        place = 1
        if len(self.results) > 0:
            place = self.results[-1].place
            if points != self.results[-1].points or penalty != self.results[-1].penalty:
                place = len(self.results) + 1
        if self.online_judge == 'codeforces':
            user = codeforces_handles[handle]
        elif self.online_judge == 'atcoder':
            user = atcoder_handles[handle]
        else:
            raise NotImplementedError
        self.results.append(StandingsRow(user, place, points, penalty, is_rated))

    def empty(self):
        for result in self.results:
            if result.points != 0:
                return False
        return True

    def __str__(self):
        return '\n'.join([str(row) for row in self.results])


def read_users_from_file():
    f = open('data/users.txt', 'r', encoding='utf-8')
    data = f.read().split()
    users = [User(' '.join(data[i:i + 3]), data[i + 3], data[i + 4]) for i in range(0, len(data), 5)]
    return users
    
    
def load_users():
    spreadsheet_id = open('data/spreadsheet_id.txt', 'r').read()
    google_api_key = open('data/google_api_key.txt', 'r').read()
    table_name = open('data/table_name.txt', 'r').read()
    url = f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{table_name}?alt=json&key={google_api_key}'
    data = requests.get(url).json()['values']
    users = [User(row[1], row[2], row[3]) for row in data[3:]]
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
        if len(members) != 1 or handle not in codeforces_handles:
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
        if handle not in atcoder_handles:
            continue
        if not row['TotalResult']['Count']:
            continue
        points = row['TotalResult']['Score'] // 100
        penalty = row['TotalResult']['Elapsed'] // 10 ** 9 + row['TotalResult']['Penalty'] * 5 * 60
        standings.add_result(handle, points, penalty, row['IsRated'])
    return standings


def get_standings(online_judge, contest_id):
    if online_judge == 'codeforces':
        return get_codeforces_standings(contest_id)
    elif online_judge == 'atcoder':
        return get_atcoder_standings(contest_id)
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
    return 'codeforces'


def create_standings_from_user_answers():
    contest_id = input('Enter contest id: ')
    online_judge = guess_online_judge(contest_id)
    if online_judge == 'atcoder':
        sheet_name = f'{contest_id[:3].upper()} #{contest_id[3:]}'
    else:
        sheet_name = input('Enter sheet name: ')
    if read_option(f'Create standings "{sheet_name}" with data from {online_judge}/{contest_id}? (yes/no) ', ['y', 'n', 'yes', 'no'])[0] == 'y':
        create_standings(online_judge, contest_id, sheet_name)


def update_codeforces_ratings(start_date):
    start_timestamp = start_date.timestamp()
    wait_time = 5
    ratings = []
    for user in tqdm(users):
        if user.codeforces_handle == '':
            continue
        while True:
            url = f'https://codeforces.com/api/user.rating?handle={user.codeforces_handle}'
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
            if len(data['result']) == 0:
                old_last_rating, old_max_rating, current_rating = 0, 0, 0
            else:
                old_last_rating = 1000
                old_max_rating = 1200
                for rating_change in data['result']:
                    if rating_change['ratingUpdateTimeSeconds'] < start_timestamp:
                        old_last_rating = rating_change['newRating']
                        old_max_rating = max(old_max_rating, rating_change['newRating'])
                    current_rating = rating_change['newRating']
            ratings.append({
                'handle': user.codeforces_handle,
                'old_rating': max(old_max_rating - 200, old_last_rating),
                'new_rating': current_rating
            })
            break
    print(*ratings, sep='\n')
    data = {
        'ratings': ratings,
        'action': 'update_ratings',
        'online_judge': 'codeforces'
    }
    spreadsheet_app_id = open('data/spreadsheet_app_id.txt', 'r').read()
    url = f'https://script.google.com/macros/s/{spreadsheet_app_id}/exec'
    response = requests.post(url, json=data)
    print(response.status_code)


def update_atcoder_ratings(start_date):
    start_timestamp = start_date.timestamp()
    wait_time = 5
    ratings = []
    for user in tqdm(users):
        if user.atcoder_handle == '':
            continue
        while True:
            url = f'https://atcoder.jp/users/{user.atcoder_handle}/history/json'
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
            for rating_change in data:
                timestamp = datetime.strptime(rating_change['EndTime'][:10], '%Y-%m-%d').timestamp()
                if timestamp < start_timestamp:
                    old_last_rating = rating_change['NewRating']
                    old_max_rating = max(old_max_rating, rating_change['NewRating'])
                current_rating = rating_change['NewRating']
            ratings.append({
                'handle': user.atcoder_handle,
                'old_rating': max(old_max_rating - 200, old_last_rating),
                'new_rating': current_rating
            })
            break
    print(*ratings, sep='\n')
    data = {
        'ratings': ratings,
        'action': 'update_ratings',
        'online_judge': 'atcoder'
    }
    spreadsheet_app_id = open('data/spreadsheet_app_id.txt', 'r').read()
    url = f'https://script.google.com/macros/s/{spreadsheet_app_id}/exec'
    response = requests.post(url, json=data)
    print(response.status_code)


def update_ratings_from_user_answers():
    online_judge = read_option('Select online judge (codeforces or atcoder): ', ['codeforces', 'atcoder'])
    start_date = read_date('Enter start date (dd.mm.yyyy) for rating calculation: ')
    if online_judge == 'codeforces':
        update_codeforces_ratings(start_date)
    else:
        update_atcoder_ratings(start_date)


users = load_users()
codeforces_handles = {user.codeforces_handle : user for user in users if user.codeforces_handle != ''}
atcoder_handles = {user.atcoder_handle : user for user in users if user.atcoder_handle != ''}
if len(sys.argv) != 2 or sys.argv[1] not in ['-s', '-r']:
    print('There should be exactly one argument: -s for adding standings, -r for updating ratings')
    exit()
if sys.argv[1] == '-s':
    create_standings_from_user_answers()
else:
    update_ratings_from_user_answers()