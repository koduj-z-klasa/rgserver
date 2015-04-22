#!/usr/bin/python

import ast
import difflib
import hashlib
import json
import math
import os
import py_compile
import random
import re
import string
import subprocess
import sys
import time
import urllib
import urlparse

import web
import web.form
import pygments
import pygments.lexers
import pygments.lexers.text
import pygments.formatters

import dbcon
import matchstate as ms
import shorten
import tools
import tplib
from rgkit.settings import settings

web.config.debug = False

CHALLENGES_LIMITS = 25
ROBOTS_LIMITS = 3
MAX_NAME_LENGTH = 25

BOT_LIMIT_REACHED_MSG = '''
Currently you can have at most {0} active robots. Disabling old bots will
allow you to create new ones. Otherwise, please create a post in the Requests
board of our community to increase your limit. It's
very easy, please don't abuse the simple registration system and
create multiple users.'''

urls = (
    # legacy redirects
    '/viewrobot/(\d*)', 'PageRedirectViewRobot',
    '/viewuser/(\d*)', 'PageRedirectViewUser',
    '/robotsource/(\d*)', 'PageRedirectRobotSource',
    '/robot/stats', 'PageRobotStats',

    # apis
    '/api/robot/stats', 'PageRobotStats',
    '/api/match/history', 'PageMatchData',
    '/api/match/(\d*)', 'PageMatchData',

    # pages
    '/', 'PageHome',
    '/directory', 'PageDirectory',
    '/home', 'PageHome',
    '/login', 'PageLogin',
    '/logout', 'PageLogout',
    '/matchlist', 'PageMatchList',
    '/match/(\d*)', 'PageMatch',
    '/moderate', 'PageModerate',
    '/moderate/(\d*)', 'PageModerate',
    '/profile/edit', 'PageProfile',
    '/reg', 'PageRegister',
    '/robots', 'PageRobots',
    '/robot/(\d*)', 'PageViewRobot',
    '/robot/(\d*)/against/(\d*)', 'PageRobotHistory',
    '/robot/(\d*)/challenge', 'PageChallengeRobot',
    '/robot/(\d*)/challenge/(\d*)', 'PageChallengeRobot',
    '/robot/(\d*)/challenge/(\d*)/(\d*)', 'PageChallengeRobot',
    '/robot/(\d*)/charts', 'PageRobotCharts',
    '/robot/(\d*)/delete', 'PageDeleteRobot',
    '/robot/(\d*)/disable', 'PageDisableRobot',
    '/robot/(\d*)/history', 'PageRobotHistory',
    '/robot/(\d*)/(edit)', 'PageEditRobot',
    '/robot/(\d*)/edit/mode/(normal)', 'PageSwitchEditMode',
    '/robot/(\d*)/edit/mode/(vim)', 'PageSwitchEditMode',
    '/robot/(\d*)/edit/(vim)', 'PageEditRobot',
    '/robot/(\d*)/enable', 'PageEnableRobot',
    '/robot/(\d*)/source', 'PageRobotSource',
    '/robot/(\d*)/test', 'PageRobotTest',
    '/robot/new', 'PageNewRobot',
    '/robot/new(acc)', 'PageNewRobot',
    '/stats', 'PageStats',
    '/update/prefs', 'PageUpdatePrefs',
    '/user/(\d*)', 'PageViewUser',

    # static pages
    '/(api)', 'PageStatic',
    '/(compdir)', 'PageStatic',
    '/(credits)', 'PageStatic',
    '/(email)', 'PageStatic',
    '/(faq)', 'PageStatic',
    '/(gettingstarted)', 'PageStatic',
    '/(kit)', 'PageStatic',
    '/(moreexamples)', 'PageStatic',
    '/(namerules)', 'PageStatic',
    '/(rgdocs)', 'PageStatic',
    '/(rules)', 'PageStatic',
    '/(security)', 'PageStatic',
)

app = web.application(urls, globals())

def debuggable_session(app):
    if web.config.get('_sess') is None:
        sess = web.session.Session(app, web.session.DiskStore('sessions'))
        web.config._sess = sess
        return sess
    return web.config._sess

sess = debuggable_session(app)

def hash(data):
    return hashlib.sha1(data).hexdigest()

def generate_salt(length=10):
    random.seed()
    pool = string.ascii_uppercase + string.ascii_lowercase + string.digits
    return ''.join(random.choice(pool) for i in range(length))

def logged_in(sess):
    if 'logged_in' in sess:
        if sess.logged_in:
            if sess.user_id:
                db.update('users', where='id=$id', vars={'id': sess.user_id},
                          last_active=int(time.time()))
                # Change this to manual swap when added
                db.update('robots', where='user_id=$id',
                          vars={'id': sess.user_id}, automatch=True)
            return sess.user_id
    return False

def force_login(sess, page='/reg', check_logged_in=False):
    user_id = logged_in(sess)
    if check_logged_in:
        # Redirect if logged in
        if user_id:
            raise web.seeother(page)
    else:
        # Redirect if not logged in
        if not user_id:
            raise web.seeother(page)
    return user_id

def username_exists(username):
    result = db.select('users',
        what='1',
        where='username=$username',
        vars={'username': username},
        limit=1)
    return bool(result)

def create_user(username, password, **params):
    pw_hash = hash(password)
    pw_salt = generate_salt()
    pw_hash = hash(pw_hash+pw_salt)

    return db.insert('users', username=username, pw_hash=pw_hash, pw_salt=pw_salt, **params)

def authenticate_user(username, password):
    users = db.select('users', where='username = $username', vars={'username': username},
    what='id, pw_hash, pw_salt')
    if not users:
        return False

    user = users[0]
    if hash(hash(password) + user['pw_salt']) == user['pw_hash']:
        return user['id']
    return False

def login_user(sess, user_id):
    if logged_in(sess):
        return False

    sess.logged_in = True
    sess.user_id = user_id
    return True

def logout_user(sess):
    sess.kill()

def template_closure(directory):
    global settings
    templates = web.template.render(
        directory,
        globals={
            'sess': sess,
            'settings': settings,
            'tplib': tplib,
        },
    )
    def render(name, *params, **kwargs):
        return getattr(templates, name)(*params, **kwargs)
    return render

tpl = template_closure('t/')

def ltpl(*params, **kwargs):
    return tpl('layout', tpl(*params, **kwargs))

def lmsg(msg):
    return tpl('layout', '<div class="prose">{0}</div>'.format(msg))

db = dbcon.connect_db()

######################


def encode_history_json(hist):
    hist = json.dumps(hist)
    hist = 'replay_callback({0});'.format(hist)
    return hist.encode('base64')


def get_match_data(mid):
    history_data = db.select('history', what='data', where='match_id=$id',
                             vars={'id': mid})
    if history_data:
        data = history_data[0]['data']
        if data:
            data = shorten.loads(data)
            data['history'] = encode_history_json(data['history'])
            return data
    return None


def get_last_matches(num, min_rating=None):
    mr = ''
    if min_rating:
        mr = ' and r1.rating >= $r and r2.rating >= $r'
    query = '''
        select
            matches.*,
            r1.compiled_code as r1_code, r2.compiled_code as r2_code,
            r1.name as r1_name, r2.name as r2_name
        from matches
            join robots r1 on r1.id = matches.r1_id
            join robots r2 on r2.id = matches.r2_id
        where state = {0} {1}
        order by timestamp desc
        limit $num'''.format(ms.DONE, mr)

    matches = db.query(query, vars={'num': num, 'r': min_rating})
    return matches if matches else None

def get_latest_match(min_rating=None):
    matches = get_last_matches(1, min_rating)
    if matches:
        return matches[0]
    return None

class PageHome:
    def GET(self):
        if logged_in(sess):
            return ltpl('home')
        rating = 3000.0
        match = get_latest_match(rating)
        if match:
            match.data = get_match_data(match['id'])
        recent = get_last_matches(5, rating)
        return ltpl('home', match, recent)

class PageLogin:
    _form = web.form.Form(
        web.form.Textbox('username', description='Username'),
        web.form.Password('password', description='Password'),
        web.form.Button('Login')
    )

    def GET(self):
        force_login(sess, '/robots', True)
        form = self._form()
        return ltpl('login', form)

    def POST(self):
        form = self._form()
        if not form.validates():
            return 'bad input'

        if not form.d.username or not form.d.password:
            return 'you have to enter a username and password'

        user_id = authenticate_user(form.d.username, form.d.password)
        if not user_id:
            return 'couldn\'t authenticate user'

        login_user(sess, user_id)
        raise web.seeother('/robots')

class PageRegister:
    _form = web.form.Form(
        web.form.Textbox('username', description='Username'),
        web.form.Password('password', description='Password'),
        web.form.Button('Register')
    )

    def GET(self):
        force_login(sess, '/robots', True)
        form = self._form()
        return ltpl('reg', form)

    def POST(self):
        form = self._form()
        if not form.validates():
            return 'bad input'

        if not form.d.username or not form.d.password:
            return 'you have to enter a username and password'

        if username_exists(form.d.username):
            return 'username already exists'

        user_id = create_user(form.d.username, form.d.password)
        if not user_id:
            return 'couldn\'t create user'

        login_user(sess, user_id)
        raise web.seeother('/robot/new')

class PageLogout:
    def GET(self):
        logout_user(sess)
        raise web.seeother('/')

class PageRobots:
    def GET(self):
        force_login(sess)
        query = '''
            select *,
                (select count(*) from robots r where compiled and passed and
                 not disabled and r.rating > robots.rating + 1e-5) as ranking
            from robots
                where user_id = $user_id and not deleted and
                      disabled = $disabled
                order by rating desc nulls last'''
        robots = db.query(
            query, vars={'user_id': sess.user_id, 'disabled': False})
        disabled_robots = db.query(
            query, vars={'user_id': sess.user_id, 'disabled': True})
        return ltpl('robots', robots, disabled_robots)

def check_name(s):
    for ch in s:
        if ch in string.printable and ch not in string.whitespace:
            return True
    return False

def count_robots(user_id):
    result = db.select(
        'robots', what='count(*)',
        where='user_id=$user_id and not disabled',
        vars={'user_id': user_id})
    return result[0]['count'] if result else None

class PageNewRobot:
    _form = web.form.Form(
        web.form.Textbox('name'))

    def GET(self, new_acc=None):
        force_login(sess)

        robot_count = count_robots(sess.user_id)
        user = db.select('users', what='extra_bots', where='id=$id',
                vars={'id': sess.user_id})
        robot_limit = ROBOTS_LIMITS
        if user:
            robot_limit += user[0]['extra_bots']
        if robot_count >= robot_limit:
            return lmsg(BOT_LIMIT_REACHED_MSG.format(robot_limit))

        top_robots = list(db.select('robots',
            what='id, name, rating, open_source',
            where='compiled and passed and not disabled and rating is not NULL',
            order='rating desc',
            limit=6))

        return ltpl('newrobot', bool(new_acc), top_robots)

    def POST(self, new_acc=None):
        force_login(sess)

        robot_count = count_robots(sess.user_id)
        user = db.select('users', what='extra_bots', where='id=$id',
                vars={'id': sess.user_id})
        robot_limit = ROBOTS_LIMITS
        if user:
            robot_limit += user[0]['extra_bots']
        if robot_count >= robot_limit:
            return lmsg(BOT_LIMIT_REACHED_MSG.format(robot_limit))

        form = self._form()
        if not form.validates():
            return 'bad input'

        form.d.name = form.d.name.strip()
        if not form.d.name:
            return lmsg('You have to enter a name.')
        if not check_name(form.d.name):
            return lmsg('Please have at least one printable, non-whitespace ASCII character in your name.')

        if len(form.d.name) > MAX_NAME_LENGTH:
            return lmsg(
                'Please limit your name to {0} characters.'.format(
                    MAX_NAME_LENGTH))

        code = '''import rg

class Robot:
    def act(self, game):
        # return something
        pass'''

        rid = db.insert('robots',
            user_id=sess.user_id,
            name=form.d.name,
            code=code)
        raise web.seeother('/robot/{0}/edit'.format(rid))

def get_robot(rid, check_user_id=True):
    where = 'id=$id'
    vars = {'id': rid}

    if check_user_id and not tplib.is_admin(sess):
        where += ' and user_id=$user_id'
        vars['user_id'] = sess.user_id

    result = db.select('robots', where=where, vars=vars)
    return result[0] if result else None

class PageSwitchEditMode:
    def GET(self, rid, edit_mode):
        if edit_mode == 'vim':
            web.setcookie('vim', 'yes', 480984220)
            raise web.seeother('/robot/' + rid + '/edit/vim')

        web.setcookie('vim', 'no', -1)
        raise web.seeother('/robot/' + rid + '/edit')

class PageEditRobot:
    _form = web.form.Form(
        web.form.Textbox('name'),
        web.form.Textarea('code'),
        web.form.Checkbox('open_source'),
        web.form.Button('save'))

    def first_time(self):
        result = db.select('robots',
            what='count(*)',
            where='compiled and user_id = $user_id',
            vars={'user_id': sess.user_id})
        if result and result[0]['count'] == 0:
            return True
        user = db.select('users',
            what='registered_on',
            where='id = $id',
            vars={'id': sess.user_id})
        if user and time.time() - user[0]['registered_on'] < tools.DAY:
            return True
        return False


    def GET(self, rid, edit_mode):
        force_login(sess)

        vim_cookie = web.cookies().get('vim')
        if vim_cookie == 'yes' and edit_mode != 'vim':
            raise web.seeother('/robot/' + rid + '/edit/vim')
        if vim_cookie == 'no' and edit_mode == 'vim':
            raise web.seeother('/robot/' + rid + '/edit')

        rid = int(rid)
        robot = get_robot(rid)
        if not robot:
            return lmsg('That robot does not exist.')

        first = self.first_time()
        db.update('robots',
            where='id=$id',
            vars={'id': rid},
            saved=False)
        return ltpl('editrobot', robot, edit_mode == 'vim', first)

    def POST(self, rid, edit_mode):
        force_login(sess)

        rid = int(rid)
        robot = get_robot(rid)
        if not robot:
            return lmsg('Robot does not exist.')

        form = self._form(robot)
        if not form.validates():
            return lmsg('Bad input.')

        form.d.name = form.d.name.strip()
        if not form.d.name:
            return lmsg('You have to enter a name.')
        if not check_name(form.d.name):
            return lmsg('Please have at least one printable and ' +
                        'non-whitespace ASCII character in your name.')

        if len(form.d.name) > MAX_NAME_LENGTH:
            return lmsg(
                'Please limit your name to {0} characters.'.format(
                    MAX_NAME_LENGTH))

        if len(form.d.code) > 250000:
            return lmsg('Please limit your code to 250,000 characters.')

        robot_code = form.d.code

        db.update('robots',
            where='id=$id',
            vars={'id': rid},
            name=form.d.name,
            code=robot_code,
            open_source=form.d.open_source)

        robot = get_robot(rid)
        if not robot:
            return lmsg('Robot does not exist.')

        compiled_code = robot_code
        if robot.rating is not None:
            rating = robot.rating
        else:
            rating = settings.default_rating
        db.update('robots',
            where='id=$id',
            vars={'id': rid},
            last_updated=int(time.time()),
            last_rating=rating,
            compiled_code=compiled_code,
            changed_since_sbtest=True,
            saved=True,
            passed=True,
            compiled=True)

        raise web.seeother('/robot/{0}/edit'.format(robot.id))

MATCHES_PER_PAGE = 20

class PageRedirectViewRobot:
    def GET(self, rid):
        raise web.redirect('/robot/{0}'.format(rid))

class PageRedirectViewUser:
    def GET(self, uid):
        raise web.redirect('/user/{0}'.format(uid))

class PageRedirectRobotSource:
    def GET(self, rid):
        raise web.redirect('/robot/{0}/source'.format(rid))

class PageViewRobot:

    def get_robot(self, rid):
        query = '''
            select
                robots.id, user_id, name, disabled, last_updated, deleted,
                rating, users.about, open_source, priority, time,
                length(compiled_code) as len, fast, short, winrate, automatch,
                (select count(*) from robots r where compiled and passed and
                 not disabled and r.rating > robots.rating + 1e-5) as ranking
            from robots
                join users on users.id = robots.user_id
            where robots.id = $id'''

        robot = db.query(query, vars={'id': rid})
        return robot[0] if robot else None

    def GET(self, rid, against=None):
        robot = self.get_robot(int(rid))
        if not robot:
            return lmsg('Robot not found.')

        query = '''
            select
                matches.*,
                r1.name as r1_name,
                r2.name as r2_name
            from matches
                join robots r1 on r1.id = matches.r1_id
                join robots r2 on r2.id = matches.r2_id
            where (r1.id = $id or r2.id = $id)
                  and (state = {0} or state = {1})
            order by matches.id desc
            '''.format(ms.WAITING, ms.RUNNING)
        next_matches = db.query(query, vars={'id': rid})
        latest_match = get_latest_match()

        query = '''
            select
                matches.*,
                r1.name as r1_name,
                r2.name as r2_name
            from matches
                join robots r1 on r1.id = matches.r1_id
                join robots r2 on r2.id = matches.r2_id
            where (r1_id = $id or r2_id = $id)
                  and (state = {0} or state = {1})
            order by timestamp desc
            LIMIT {2}
            '''.format(ms.ERROR, ms.DONE, 5)
        matches = db.query(
            query, vars={'id': rid})

        challenges = 0
        if logged_in(sess):
            result = db.select('users',
                what='challenges',
                where='id=$id',
                vars={'id': sess.user_id})
            if result:
                challenges = CHALLENGES_LIMITS - result[0]['challenges']

        return ltpl('viewrobot', robot, matches, next_matches,
                    latest_match.id if latest_match else None, challenges)

class PageRobotHistory:

    def get_robot(self, rid):
        query = '''
            select
                robots.id, user_id, name, disabled, last_updated, deleted,
                rating, users.about, open_source, priority, time,
                length(compiled_code) as len, fast, short, winrate, automatch,
                (select count(*) from robots r where compiled and passed and
                 not disabled and r.rating > robots.rating + 1e-5) as ranking
            from robots
                join users on users.id = robots.user_id
            where robots.id = $id'''

        robot = db.query(query, vars={'id': rid})
        return robot[0] if robot else None

    def GET(self, rid, against=None):
        robot = self.get_robot(int(rid))
        if not robot:
            return lmsg('Robot not found.')

        opponent = None
        if against is not None:
            opponent = self.get_robot(int(against))
            if not opponent:
                return lmsg('Robot against not found.')

        #robot.about = self.convert_links(robot.about)

        params = web.input(page=None, ranked=None, per=None)
        page = int(params.page or 0)
        ranked = int(params.ranked or 0)
        per = int(params.per or MATCHES_PER_PAGE)
        if per > 200 and not tplib.is_admin(sess):
            per = 200
        ranked = 'and ranked' if ranked > 0 else 'and not ranked' if ranked < 0 else ''

        if against is None:
            query = '''
                select
                    matches.*,
                    r1.name as r1_name,
                    r2.name as r2_name
                from matches
                    join robots r1 on r1.id = matches.r1_id
                    join robots r2 on r2.id = matches.r2_id
                where (r1_id = $id or r2_id = $id)
                      and (state = {0} or state = {1})
                      {3}
                order by timestamp desc
                limit {2}
                offset $page'''.format(ms.ERROR, ms.DONE, per,
                                       ranked)
            matches = db.query(
                query, vars={'id': rid, 'page': page * per})
        else:
            query = '''
                select
                    matches.*,
                    r1.name as r1_name,
                    r2.name as r2_name
                from matches
                    join robots r1 on r1.id = matches.r1_id
                    join robots r2 on r2.id = matches.r2_id
                where ((r1_id = $id1 and r2_id = $id2) or
                       (r1_id = $id2 and r2_id = $id1))
                      and (state = {0} or state = {1})
                      {3}
                order by timestamp desc
                limit {2}
                offset $page'''.format(ms.ERROR, ms.DONE, per,
                                       ranked)
            matches = db.query(
                    query,
                    vars={
                        'id1': rid,
                        'id2': against,
                        'page': page * per
                    })

        return ltpl('robot_history', robot, matches, page, per, against,
                    params.ranked)

class PageViewUser:

    def get_user_detailed(self, uid):
        query = '''
            select
                *, coalesce(r.count, 0) as robot_count
            from users
                left join (
                    select
                        user_id as uid, count(*) as count
                    from robots
                        where not robots.disabled
                        group by user_id
                ) as r
                on r.uid = users.id
            where users.id = $id'''

        user = db.query(query, vars={'id': uid})
        return user[0] if user else None

    def get_robots(self, uid, disabled=False):
        query = '''
            select
                *,
                (select count(*) from robots r where compiled and passed and
                 not disabled and r.rating > robots.rating + 1e-5) as ranking
            from robots
            where robots.user_id = $id and disabled = $disabled and not deleted
            order by robots.rating desc nulls last
        '''

        robots = db.query(query, vars={'id': uid, 'disabled': disabled})
        return robots if robots else []

    def get_user(self, uid):
        query = '''
            select id, about, last_active, registered_on
            from users
            where id = $id'''
        user = db.query(query, vars={'id': uid})
        return user[0] if user else None

    def GET(self, uid=None):
        if uid is None or ('user_id' in sess and int(uid) == sess.user_id):
            uid = force_login(sess)
            user = self.get_user_detailed(int(uid))
            user.robots_limit = ROBOTS_LIMITS + user.extra_bots
            user.challenges_limit = CHALLENGES_LIMITS
        else:
            user = self.get_user(int(uid))

        if not user:
            return lmsg('User not found.')
        robots = self.get_robots(int(uid))
        disabled_robots = self.get_robots(int(uid), True)

        return ltpl('viewuser', user, robots, disabled_robots)

def get_match(mid, no_code=None):
    if no_code is None:
        query = '''
            select
                matches.*,
                r1.compiled_code as r1_code, r2.compiled_code as r2_code,
                r1.name as r1_name, r2.name as r2_name
            from matches
                join robots r1 on r1.id = matches.r1_id
                join robots r2 on r2.id = matches.r2_id
            where matches.id = $id'''
    else:
        query = '''
            select
                matches.*,
                r1.name as r1_name, r2.name as r2_name
            from matches
                join robots r1 on r1.id = matches.r1_id
                join robots r2 on r2.id = matches.r2_id
            where matches.id = $id'''

    match = db.query(query, vars={'id': mid})
    return match[0] if match else None

def get_pending_matches():
    query = '''
        select
            matches.*,
            r1.compiled_code as r1_code, r2.compiled_code as r2_code,
            r1.name as r1_name, r2.name as r2_name
        from matches
            join robots r1 on r1.id = matches.r1_id
            join robots r2 on r2.id = matches.r2_id
        where state = {0} and not ranked'''.format(ms.WAITING)
    return db.query(query)

class PageChallengeRobot:
    def match_running(self, rid, challenger):
        result = db.select('matches',
            what='id',
            where='''
                (r1_id = $id1 and r2_id = $id2 or
                    r1_id = $id2 and r2_id = $id1)
                and (state = {0} or state = {1})
                '''.format(ms.WAITING, ms.RUNNING),
            vars={'id1': rid, 'id2': challenger})
        return result[0].id if result else None

    def eligible(self, rid):
        result = db.select(
            'robots', what='count(*)',
            where='passed and compiled and not deleted and id=$id',
            vars={'id': rid})
        return result and result[0]['count'] > 0

    def is_self(self, rid):
        result = db.select('robots', what='user_id', where='id=$id', vars={'id': rid})
        return (result and result[0]['user_id'] == sess.user_id)

    def get_rating(self, rid):
        result = db.select('robots', what='rating', where='id=$id', vars={'id': rid})
        return result[0]['rating']

    def limit_ok(self, user_id, num_matches):
        result = db.select('users',
            what='challenges',
            where='id=$id',
            vars={'id': user_id})

        if result:
            result = result[0]
            return result['challenges'] + num_matches <= CHALLENGES_LIMITS
        return False

    def GET(self, rid, challenger=None, num_matches=None):
        force_login(sess)
        rid = int(rid)

        if self.is_self(rid):
            return lmsg('You can\'t challenge one of your own robots.')
        if num_matches is None:
            num_matches = 1
        else:
            num_matches = int(num_matches)

        if not self.limit_ok(sess.user_id, num_matches):
            return lmsg('''
                You <a href="/profile"><b>don't have enough challenges</b></a>
                left today! The counts are reset everyday at midnight EST.
                <br/><br/>''')

        if challenger is None:
            robots = db.select(
                'robots',
                where='user_id=$id and compiled and passed and not deleted',
                vars={'id':sess.user_id})
            return ltpl('choosechallenge', rid, robots)

        challenger = int(challenger)
        if not self.is_self(challenger):
            return lmsg('You can only challenge others with your robots.')

        if not self.eligible(rid):
            return lmsg('The enemy is not eligible to fight.')

        if not self.eligible(challenger):
            return lmsg('Your robot is not eligible to fight.')

        # create match
        for l in range(num_matches):
            if random.random() < 0.5:
                match_id = db.insert(
                    'matches', r1_id=rid, r2_id=challenger,
                    ranked=False, r1_rating=self.get_rating(rid),
                    r2_rating=self.get_rating(challenger),
                    seed=random.randint(1, settings.max_seed))
            else:
                match_id = db.insert(
                    'matches', r2_id=rid, r1_id=challenger,
                    ranked=False, r2_rating=self.get_rating(rid),
                    r1_rating=self.get_rating(challenger),
                    seed=random.randint(1, settings.max_seed))

        # add to user's challenges count
        db.query('UPDATE users SET challenges=challenges+$c WHERE id=$id',
                 vars={'id': sess.user_id, 'c': num_matches})

        if num_matches == 1:
            raise web.seeother('/match/{0}'.format(match_id))
        else:
            raise web.seeother('/robot/{0}'.format(rid))



class PageMatchList:
    def GET(self):
        recent = get_last_matches(100)
        query = '''
            select
                matches.*,
                r1.name as r1_name,
                r2.name as r2_name
            from matches
                join robots r1 on r1.id = matches.r1_id
                join robots r2 on r2.id = matches.r2_id
            where (state = {0} or state = {1})
            order by matches.id desc
            '''.format(ms.WAITING, ms.RUNNING)
        next_matches = db.query(query)
        return ltpl('matchlist', recent, next_matches)


class PageMatch:
    def GET(self, mid):
        match = get_match(int(mid))
        if not match:
            return 'match not found'

        match.data = get_match_data(match['id'])

        has_match_log = time.time() - match.timestamp < tools.WEEK
        return ltpl('match', match, has_match_log)

class PageStatic:
    def GET(self, page):
        return ltpl(page)

PER_PAGE = 20
class PageDirectory:
    def get_ranking(self, rating, where=''):
        if rating is None:
            count = db.select('robots',
                what='count(*)',
                where='''compiled and passed and not disabled
                         and rating is not NULL {0}'''.format(where))
        else:
            count = db.select('robots',
                what='count(*)',
                where='''compiled and passed and not disabled
                         and rating > $rating + 1e-5 {0}'''.format(where),
                vars={'rating': rating})
        return count[0]['count'] if count else None

    def GET(self):
        params = web.input(upper=None, page=None, latest=None, os=None,
                           diff=None, pri=None, viewactive=None, fast=None,
                           time=None, short=None, disabled=None, tlimit=None,
                           win=None, per=None)
        params.diff = int(params.diff or 0)
        if params.latest:
            order = 'last_updated desc'
        elif params.diff > 0:
            order = 'rating-last_rating desc nulls last'
        elif params.diff < 0:
            order = 'rating-last_rating asc nulls first'
        elif params.pri:
            order = 'priority desc'
        elif params.time:
            order = 'time desc'
        elif params.win:
            order = 'winrate ' + ('desc' if int(params.win) > 0 else 'asc')
        else:
            order = 'rating desc nulls last'
        per = int(params.per or PER_PAGE)
        if per > 200 and not tplib.is_admin(sess):
            per = 200
        os_where = ' and not disabled' if not params.disabled else ''
        os_where += ' and open_source' if params.os else ''
        os_where += ' and automatch' if params.viewactive else ''
        t = 2 if not params.tlimit else float(params.tlimit)
        os_where += ' and time < {0}'.format(t) if params.fast else ''
        os_where += ' and length(compiled_code) < 1000' if params.short else ''
        page = int(params.page or 0)
        os_what = '''id, user_id, name, rating, open_source, automatch,
                     last_updated, last_rating, fast, short, winrate'''
        if params.upper == '':
            upper = None
            robots = list(db.select('robots',
                what=os_what,
                where='''compiled and rating is NULL and passed
                         and not deleted {0}'''.format(os_where),
                order=order,
                limit=per,
                offset=page*per,
                vars=locals()))
        else:
            if params.upper is None and 'logged_in' in sess and sess.user_id:
                my_robots = list(db.select('robots',
                    what='rating',
                    where='''compiled and rating is not NULL and passed
                             and not deleted and user_id=$user_id
                             {0}'''.format(os_where),
                    order=order,
                    vars={'user_id': sess.user_id}))
                if not my_robots:
                    top_rating = settings.default_rating
                else:
                    top_rating = my_robots[0].rating
                my_rank = self.get_ranking(top_rating, os_where)
                goal_rank = max(0, my_rank - (per - 1) / 2)
                #print top_rating, my_rank, goal_rank
                left, right = int(top_rating), 10000
                while left < right:
                    #print left, right
                    mid = (left + right + 1) / 2
                    cur_rank = self.get_ranking(mid, os_where)
                    if cur_rank > goal_rank:
                        left = mid
                    elif cur_rank < goal_rank:
                        right = mid - 1
                    else:
                        left = mid
                        break
                upper = left
            else:
                upper = float(params.upper or 1000000)
            robots = list(db.select('robots',
                what=os_what,
                where='''compiled and passed and not deleted
                         and (rating <= $upper or rating is NULL) {0}'''.format(os_where),
                order=order,
                limit=per,
                offset=page*per,
                vars=locals()))

        start_ranking = 0
        if robots:
            start_ranking = self.get_ranking(robots[0].rating, os_where)
        return ltpl('directory', robots, upper, start_ranking, page, per,
                    params.latest, params.os, params.diff, params.viewactive,
                    params.fast, params.short)

class PageStats:
    def count_users_registered(self):
        count = db.select('users',
                          what='count(*)',
                          where='registered_on > $time',
                          vars={'time': time.time() - tools.MONTH})
        return count[0]['count'] if count else 0

    def count_users_period(self, period):
        count = db.select('users',
                          what='count(*)',
                          where='last_active > $time',
                          vars={'time': time.time() - period})
        return count[0]['count'] if count else 0

    def count_users_month(self):
        return self.count_users_period(tools.MONTH)

    def count_users_week(self):
        return self.count_users_period(tools.WEEK)

    def count_users_with_passing_robots(self):
        users = db.select('robots',
            what='1',
            where='compiled and passed and not disabled and automatch',
            group='user_id')
        return len(users) if users else None

    def count_users_with_robots(self):
        users = db.select('robots',
            what='1',
            where='compiled and not disabled and automatch',
            group='user_id')
        return len(users) if users else None

    def count_robots_not_disabled(self):
        count = db.select('robots',
            what='count(*)',
            where='not disabled and automatch')
        return count[0]['count'] if count else 0

    def count_robots_compiled(self):
        count = db.select('robots',
            what='count(*)',
            where='compiled and not disabled and automatch')
        return count[0]['count'] if count else 0

    def count_robots_passing(self):
        count = db.select('robots',
            what='count(*)',
            where='compiled and passed and not disabled and automatch')
        return count[0]['count'] if count else 0

    def count_robots_available(self):
        count = db.select('robots',
            what='count(*)',
            where='compiled and passed and not disabled')
        return count[0]['count'] if count else 0

    def count_robots_updated(self):
        count = db.select('robots',
            what='count(*)',
            where='''compiled and passed and not disabled
                     and last_updated > $time''',
            vars={'time': time.time() - tools.MONTH})
        return count[0]['count'] if count else 0

    def count_matches(self):
        match_count = db.select('matches', what='count(*)',
                                where='state={0}'.format(ms.DONE))
        return match_count[0]['count'] if match_count else None

    def count_histories(self):
        match_count = db.select('history', what='count(*)')
        return match_count[0]['count'] if match_count else None

    def average_rating(self):
        result = db.select('robots', what='AVG(rating)',
            where='passed and compiled and not disabled')[0]['avg']
        return int(result) if result is not None else 0

    def count_matchmaker_processes(self):
        pipes = subprocess.Popen(['ps', 'uxaf'], stdout=subprocess.PIPE)
        processes = pipes.stdout.readlines()
        scripts = ('matchmaker',)
        counts = dict((x, dict(root=0, nobody=0)) for x in scripts)

        for process in processes:
            for script in scripts:
                if ('python {0}.py'.format(script)) not in process:
                    continue
                for user in ('root', 'nobody'):
                    if user in process:
                        counts[script][user] += 1
                        break
        return counts

    def GET(self):
        info = [
            'count_users_registered',
            'count_users_month',
            'count_users_with_robots',
            'count_users_with_passing_robots',
            'count_robots_available',
            'count_robots_not_disabled',
            'count_robots_compiled',
            'count_robots_passing',
            'count_robots_updated',
            'count_matches',
            'count_histories',
            'average_rating']

        return ltpl('stats', *[getattr(self, x)() for x in info])


class PageRobotStats:
    def GET(self):
        robots = db.select(
            'robots',
            what='id, user_id, rating, name, automatch, disabled',
            where='compiled and passed')
        bots = []
        for robot in robots:
            bots.append({
                'id': robot.id,
                'user_id': robot.user_id,
                'rating': robot.rating,
                'name': robot.name,
                'automatch': robot.automatch,
                'disabled': robot.disabled,
            })
        return json.dumps(bots)


class PageMatchData:
    def GET(self, mid=None):
        if mid is None:
            histories = db.select('history', what='match_id, timestamp')
            valids = []
            for history in histories:
                valids.append({
                    'match_id': history.match_id,
                    'timestamp': history.timestamp
                })
            return json.dumps(valids)
        else:
            match = get_match(mid, True)  # No code. ;)
            if not match:
                return json.dumps({
                    'error': 'match not found'
                })
            match.data = get_match_data(mid)
            return json.dumps(match)


DEFAULT_PERIOD = tools.MONTH


class PageRobotCharts:
    def get_robot(self, rid):
        query = '''
            select
                robots.id, user_id, name, disabled, last_updated, deleted,
                rating, users.about, open_source, priority, time,
                length(compiled_code) as len, fast, short, winrate, automatch,
                (select count(*) from robots r where compiled and passed and
                 not disabled and r.rating > robots.rating + 1e-5) as ranking
            from robots
                join users on users.id = robots.user_id
            where robots.id = $id'''

        robot = db.query(query, vars={'id': rid})
        return robot[0] if robot else None

    def get_chart_data(self, robot, full=None):
        if full:
            oldest = 0
        else:
            oldest = int(time.time() - DEFAULT_PERIOD)
        chart_data = None
        query1 = '''
            select
                timestamp, r1_rating as rating, r1_ranking as ranking
            from matches
            where r1_id = $id and ranked and state = 3 and timestamp > $t'''
        query2 = '''
            select
                timestamp, r2_rating as rating, r2_ranking as ranking
            from matches
            where r2_id = $id and ranked and state = 3 and timestamp > $t'''
        rating_data = []
        ranking_data = []
        max_rating = 0
        max_timestamp = 0
        for query in [query1, query2]:
            for pair in db.query(query, vars={'id': robot.id, 't': oldest}):
                rating_data.append(
                    (pair.timestamp * 1000, pair.rating))
                if pair.rating > max_rating:
                    max_rating, max_timestamp = pair.rating, pair.timestamp
                if pair.ranking is not None:
                    ranking_data.append(
                        (pair.timestamp * 1000, pair.ranking + 1))
        rating_data.sort(key=lambda x: x[0])
        ranking_data.sort(key=lambda x: x[0])

        query = '''
            select floor(rating/100) as r, count(*) as n from robots
            where passed and compiled and not disabled and rating is not null
            group by r order by r desc
        '''
        group_data = []
        for group in db.query(query):
            group_data.append((group.r * 100, group.n))

        chart_data = [
            {
                'data': rating_data,
                'label': 'ELO Rating',
                'color': 'black',
            },
        ]
        chart_data.append(
            {
                'data': ranking_data,
                'label': 'Overall Rank',
                'color': 'darkcyan',
                'yaxis': 2,
            },
        )
        chart_data = '''
            var data = {0};
            var last_updated = {1};
            var cur_rating = {3};
            var gdata = {2};
            var max_rating = {4};
            var max_timestamp = {5};
        '''.format(json.dumps(chart_data),
                   robot.last_updated * 1000,
                   json.dumps(group_data),
                   robot.rating or settings.default_rating,
                   max_rating,
                   max_timestamp * 1000)
        chart_data = chart_data.encode('base64')
        return chart_data

    def GET(self, rid, against=None):
        robot = self.get_robot(int(rid))
        if not robot:
            return lmsg('Robot not found.')

        params = web.input(full=None)

        chart_data = self.get_chart_data(robot, params.full)
        return ltpl('robotcharts', robot, chart_data, params.full)

class PageStaticBlank:
    def GET(self, page):
        return tpl(page)

class PageProfile:
    _form = web.form.Form(
        web.form.Textarea('about'))

    def get_user(self, uid):
        query = '''
            select id, about
            from users
            where id = $id'''
        user = db.query(query, vars={'id': uid})
        return user[0] if user else None

    def GET(self):
        force_login(sess)
        user = self.get_user(sess.user_id)
        if not user:
            return lmsg('Your account was not found.')

        return ltpl('profile', user)

    def POST(self):
        force_login(sess)
        form = self._form()
        if not form.validates():
            return lmsg('Invalid input.')

        if len(form.d.about) > 5000:
            return lmsg('Please limit your profile to fewer than 5,000 characters.')

        db.update('users', where='id=$id', about=form.d.about, vars={'id': sess.user_id})
        raise web.seeother('/user/{0}'.format(sess.user_id))

class PageRobotTest:
    def GET(self, rid):
        rid = int(rid)
        robot = get_robot(rid, check_user_id=False)
        if not robot or not tplib.is_admin(sess):
            return lmsg('That robot was not found.')
        query = '''
            select
                *
            from robots
            where open_source and compiled and passed and
                rating > $rating - 100
            order by robots.rating desc
        '''
        # only robots with greater rating can be possibly copied
        os_robots = db.query(query, vars={'rating': robot.rating})
        shortest = None
        minlen = None
        for os_robot in os_robots:
            os_code = os_robot.code.splitlines(True)
            code = robot.code.splitlines(True)
            if len(os_code) > 1.5 * len(code) or len(code) > 1.5 * len(os_code):
                continue
            ud = difflib.ndiff(os_code, code)
            ud = [line for line in ud if line[:2] != '? ']
            if shortest is None or len(ud) - len(os_code) < minlen:
                minlen = len(ud) - len(os_code)
                shortest = ud
        if shortest is not None:
            return tpl(
                'robotsource',
                pygments.highlight(
                    ''.join(shortest),
                    pygments.lexers.text.DiffLexer(),
                    pygments.formatters.HtmlFormatter()),
                robot.name)
        else:
            return lmsg('No similarities found.')

class PageRobotSource:
    def GET(self, rid):
        rid = int(rid)
        robot = get_robot(rid, check_user_id=False)
        if not robot:
            return lmsg('That robot was not found.')
        if robot.open_source or (logged_in(sess) and sess.user_id == robot.user_id) or tplib.is_admin(sess):
            web.header('Content-Type', 'text/html')
            return tpl(
                'robotsource',
                pygments.highlight(
                    robot.compiled_code,
                    pygments.lexers.PythonLexer(),
                    pygments.formatters.HtmlFormatter()),
                robot.name,
                robot.open_source)
        raise web.seeother('/robot/{0}'.format(rid))

def get_robot_with_ranking(rid):
    where = 'id=$id'
    vars = {'id': rid}

    if not (logged_in(sess) and sess.user_id == 1):
        where += ' and user_id=$user_id'
        vars['user_id'] = sess.user_id

    query = '''
        select *,
            (select count(*) from robots r where compiled and passed and
                not disabled and r.rating > robots.rating + 1e-5) as ranking
        from robots
            where {0}'''.format(where)

    result = db.query(query, vars=vars)
    return result[0] if result else None

class PageDisableRobot:
    def GET(self, rid):
        force_login(sess)
        rid = int(rid)
        robot = get_robot(rid)
        if not robot:
            return lmsg('That robot was not found.')
        if tplib.is_admin(sess):
            db.update('robots',
                where='id=$id',
                vars={'id': rid},
                disabled=True)
            raise web.seeother('/robot/{0}'.format(rid))
        else:
            db.update('robots',
                where='id=$id and user_id=$user_id',
                vars={'id': rid, 'user_id': sess.user_id},
                disabled=True)
            raise web.seeother('/robots')

class PageEnableRobot:
    def GET(self, rid):
        force_login(sess)
        rid = int(rid)
        robot = get_robot(rid)
        if not robot:
            return lmsg('That robot was not found.')
        if tplib.is_admin(sess):
            db.update('robots',
                where='id=$id',
                vars={'id': rid},
                disabled=False)
            raise web.seeother('/robot/{0}'.format(rid))
        else:
            robot_count = count_robots(sess.user_id)
            user = db.select('users', what='extra_bots', where='id=$id',
                    vars={'id': sess.user_id})
            robot_limit = ROBOTS_LIMITS
            if user:
                robot_limit += user[0]['extra_bots']
            if robot_count >= robot_limit:
                return lmsg(BOT_LIMIT_REACHED_MSG.format(robot_limit))
            db.update('robots',
                where='id=$id and user_id=$user_id',
                vars={'id': rid, 'user_id': sess.user_id},
                disabled=False)
            return web.seeother('/robots')

class PageDeleteRobot:
    def GET(self, rid):
        force_login(sess)
        rid = int(rid)
        robot = get_robot(rid)
        if not robot:
            return lmsg('That robot was not found.')
        return ltpl('delrobot', robot)

    def POST(self, rid):
        force_login(sess)
        rid = int(rid)
        if tplib.is_admin(sess):
            db.update('robots',
                where='id=$id',
                vars={'id': rid},
                disabled=True,
                deleted=True)
            raise web.seeother('/robot/{0}'.format(rid))
        else:
            db.update('robots',
                where='id=$id and user_id=$user_id',
                vars={'id': rid, 'user_id': sess.user_id},
                disabled=True,
                deleted=True)
            raise web.seeother('/robots')

class PageModerate:
    def GET(self, rid=None):
        if not tplib.is_mod(sess): raise web.seeother('/')

        if rid is not None:
            rid = int(rid)
            query = """
                insert into fail_bots (hash, code) select md5($code), $code where
                not exists (select 1 from fail_bots where hash = md5($code))
            """
            robots = db.select('robots', what='compiled_code', where='id=$id',
                               vars={'id': rid})
            if robots:
                code = robots[0]['compiled_code']
                db.query(query, vars={'code': code})
                db.update('robots', where='id=$id', vars={'id': rid},
                          passed=False, disabled=True)
            raise web.ok

        robots = db.select('robots', what='id, rating, compiled_code',
                           where='''passed and compiled and not disabled and
                           rating is not NULL and rating < -800 and
                           not automatch and last_updated
                           < extract(epoch from now()) - 60 * 60 * 24 * 7''',
                           order='rating asc')
        maximum = int(web.input(maximum=100000).maximum)
        return ltpl('moderate', robots, maximum)

class PageUpdatePrefs(object):
    def GET(self):
        params = web.input(show_actions=None, show_grid=None)
        if params.show_actions is not None:
            sess.show_actions = True if params.show_actions=='yes' else False
        if params.show_grid is not None:
            sess.show_grid = True if params.show_grid=='yes' else False
        return web.ok

MAX_RETRIES = 10

application = app.wsgifunc()
if __name__ == '__main__':
    app.run()
