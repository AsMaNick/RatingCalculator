import os
import json
import requests
import jsonpickle
import onlinejudge


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
    def __init__(self, user, place, points, penalty):
        self.user = user
        self.place = place
        self.points = points
        self.penalty = penalty

    def __str__(self):
        return f'{self.place}) {self.user}: ({self.points}, {self.penalty})'


class Standings:
    def __init__(self, online_judge, contest_id):
        self.online_judge = online_judge
        self.contest_id = contest_id
        self.results = []

    def add_result(self, handle, points, penalty):
        place = 1
        if len(self.results) > 0:
            place = len(self.results)
            if points != self.results[-1].points or penalty != self.results[-1].penalty:
                place += 1
        if self.online_judge == 'codeforces':
            user = codeforces_handles[handle]
        elif self.online_judge == 'atcoder':
            user = atcoder_handles[handle]
        else:
            raise NotImplementedError
        self.results.append(StandingsRow(user, place, points, penalty))

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
    url = f'https://spreadsheets.google.com/feeds/list/{spreadsheet_id}/2/public/values?alt=json'
    data = requests.get(url).json()['feed']['entry']
    users = [User(row['gsx$_cokwr']['$t'], row['gsx$_cpzh4']['$t'], row['gsx$_cre1l']['$t']) for row in data[2:]]
    return users


def get_codeforces_standings(contest_id):
    url = f'https://codeforces.com/api/contest.standings?contestId={contest_id}&showUnofficial=true'
    response = requests.get(url)
    data = response.json()
    standings = Standings('codeforces', contest_id)
    for row in data['result']['rows']:
        if row['party']['participantType'] != 'OUT_OF_COMPETITION' and row['party']['participantType'] != 'CONTESTANT':
            continue
        members = row['party']['members']
        handle = members[0]['handle']
        if len(members) != 1 or handle not in codeforces_handles:
            continue
        standings.add_result(handle, row['points'], row['penalty'])
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
        
    session = login()
    url = f'https://atcoder.jp/contests/{contest_id}/standings/json'
    response = session.get(url, allow_redirects=False)
    data = response.json()
    standings = Standings('atcoder', contest_id)
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
        standings.add_result(handle, points, penalty)
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


def create_standings_from_user_answers():
    online_judge = read_option('Select online judge (codeforces or atcoder): ', ['codeforces', 'atcoder'])
    contest_id = input('Enter contest id: ')
    sheet_name = input('Enter sheet name: ')
    if read_option(f'Create standings "{sheet_name}" with data from {online_judge}/{contest_id}? (yes/no) ', ['y', 'n', 'yes', 'no'])[0] == 'y':
        create_standings(online_judge, contest_id, sheet_name)


users = load_users()
codeforces_handles = {user.codeforces_handle : user for user in users if user.codeforces_handle != ''}
atcoder_handles = {user.atcoder_handle : user for user in users if user.atcoder_handle != ''}
create_standings_from_user_answers()