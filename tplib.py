import bleach
import hashlib
import markdown
import math
import tools

from datetime import datetime

ADMINS = (
    1, # wilku (hehe, just use one account to be safe
)
MODERATORS = (
    1, # wilku
)
USER_SALT = 'bbiuyxzoswekl;jgtohgoaboih'

def is_mod(sess):
    return 'logged_in' in sess and sess.user_id in MODERATORS
def is_admin(sess):
    return 'logged_in' in sess and sess.user_id in ADMINS
def is_logged_in(sess):
    return 'logged_in' in sess and sess.logged_in

def get_pref(pref, sess):
    if pref in sess:
        return sess[pref]
    return None

def clean(message):
    if not message:
        return ''
    return message.strip().lower()

def msghash(message):
    return hashlib.sha256(clean(message.encode('utf-8'))).hexdigest()

def time_ago(timestamp):
    diff = datetime.now() - datetime.fromtimestamp(timestamp)
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return 'just now'
    elif day_diff == 0:
        if second_diff < 60:
            return '%ds ago' % second_diff
        elif second_diff < 3600:
            return '%dm ago' % (second_diff / 60)
        else:
            return '%dh ago' % (second_diff / 3600)
    elif day_diff < 30:
        return '%dd ago' % day_diff
    elif day_diff < 365:
        return '%dmo ago' % (day_diff / 30)
    if day_diff / 365 < 40:
        return '%dyr ago' % (day_diff / 365)
    return 'long ago'

def timedelta_ago(timestamp):
    return datetime.now() - datetime.fromtimestamp(timestamp)

def rounded(num, digits=None):
    if digits is None:
        return int(round(num))
    return round(num, digits)

def dec(rating):
    result = ''
    clr = 'red'
    if isinstance(rating, basestring):
        return rating
    elif rating >= 3600:
        result = '''
            <i class="fa fa-stack rating-container">
                <i class="fa fa-bullseye fa-stack-1x rating-front"></i>
                <i class="fa fa-circle rating-middle rating-white"></i>
            </i>{0}'''
    elif rating >= 3000:
        result = '''
            <i class="fa fa-stack rating-container">
                <i class="fa fa-dot-circle-o fa-stack-1x rating-front"></i>
                <i class="fa fa-circle rating-middle rating-white"></i>
            </i>{0}'''
    else:
        if rating >= 2400:
            clr = 'red'
            per = (rating - 2400) / 600.0
        elif rating >= 1800:
            clr = 'yellow'
            per = (rating - 1800) / 600.0
        elif rating >= 1200:
            clr = 'blue'
            per = (rating - 1200) / 600.0
        elif rating >= 600:
            clr = 'green'
            per = (rating - 600) / 600.0
        else:
            clr = 'gray'
            per = rating / 600.0
        n = round((1 - per) * 11)
        if n > 0:
            n += 2
        result = '''
            <i class="fa fa-stack rating-container">
                <i class="fa fa-circle-thin fa-stack-1x rating-front"></i>
                <i class="fa fa-circle fa-stack-1x rating-middle rating-i rating-white"
                   style="height: {0}"></i>
                <i class="fa fa-circle fa-stack-1x rating-back"></i>
            </i>{{0}}'''.format(n)
    frating = '<strong>{0}</strong>'.format(rating)
    return '<span class="rating-{0}">{1}</span>'.format(
        clr, result.format(frating))

def rating_string(rating, decimal=False, ranking=None):
    if rating is None:
        return 'unrated'
    if decimal:
        rounded = round(rating, 1)
    else:
        rounded = int(round(rating))
    if ranking is not None:
        return '{0} Rank: {1}'.format(rounded, ranking + 1)
    return rounded

def drating(*args, **kwargs):
    return dec(rating(*args, **kwargs))

def rating(robot, decimal=False):
    return rating_string(robot.rating, decimal)

def rating_diff(robot):
    if robot.rating is None:
        rating = tools.DEFAULT_RATING
    else:
        rating = robot.rating
    last_rating = robot.last_rating
    return round(rating - last_rating, 1)

def rating_diff_class(robot):
    diff = rating_diff(robot)
    bounds = [16, 6, 2, -16, -6, -2]
    classes = [
        'fa-caret-up bold',
        'fa-angle-double-up bold',
        'fa-angle-up bold',
        'fa-caret-down bold',
        'fa-angle-double-down bold',
        'fa-angle-down bold',
    ]
    k = tools.get_k_factor(robot.last_rating)
    for i in range(len(bounds)):
        if diff > 0 and bounds[i] > 0 and diff > bounds[i] * k:
            return classes[i] + ' green'
        elif diff < 0 and bounds[i] < 0 and diff < bounds[i] * k:
            return classes[i] + ' red'
    return ''

def match_rating(match, rid, other=False, decimal=False):
    if (match.r1_id == rid) ^ other:
        return rating_string(match.r1_rating, decimal, match.r1_ranking)
    return rating_string(match.r2_rating, decimal, match.r2_ranking)

def new_rating(r1, r2, result, k_factor):
    expected = 1.0/(1 + pow(10, (r2 - r1)/400.0))
    return r1 + k_factor * (result - expected)

def get_rating_diff(rating1, rating2, score1, score2, k_factor=32.0):
    if score1 == score2:
        score = 0.5
    elif score1 > score2:
        score = 1
    else:
        score = 0
    return new_rating(rating1, rating2, score, k_factor) - rating1

def rating_change(match, rid, other=False):
    if (match.r1_id == rid) ^ other:
        diff = get_rating_diff(match.r1_rating, match.r2_rating,
                               match.r1_score, match.r2_score,
                               match.k_factor)
    else:
        diff = get_rating_diff(match.r2_rating, match.r1_rating,
                               match.r2_score, match.r1_score,
                               match.k_factor)
    return round(diff, 1)

def safe_markdown(string):
    string = bleach.clean(string)
    string = markdown.markdown(string)
    others = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']
    return bleach.clean(string, tags=bleach.ALLOWED_TAGS+others)
