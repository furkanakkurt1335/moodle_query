import requests, re, os, json
from bs4 import BeautifulSoup
from datetime import datetime
import logging

THIS_DIR = os.path.dirname(os.path.realpath(__file__))

log_path = os.path.join(THIS_DIR, 'changes.log')
logging.basicConfig(filename=log_path, level=logging.INFO, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)

credentials_path = os.path.join(THIS_DIR, 'credentials.json')
if not os.path.exists(credentials_path):
    with open(credentials_path, 'w', encoding='utf-8') as f:
        f.write('{"username": null, "password": null}')
    print('You need to add your credentials in "credentials.json" in the script folder.')
    exit()
with open(credentials_path, 'r', encoding='utf-8') as f:
    data = json.load(f)
    if data['username'] == None or data['password'] == None:
        print('You need to add your credentials in "credentials.json" in the script folder.')
        exit()

urls_path = os.path.join(THIS_DIR, 'URLs.json')
empty_urls_d = { "login": "https://moodle.boun.edu.tr/login/index.php", "dashboard": "https://moodle.boun.edu.tr/my/", "pages": dict() }
if not os.path.exists(urls_path):
    with open(urls_path, 'w', encoding='utf-8') as f:
        json.dump(empty_urls_d, f)
else:
    with open(urls_path, 'r', encoding='utf-8') as f:
        try:
            urls = json.load(f)
        except:
            urls = {}
    keys = ['dashboard', 'login', 'pages']
    for k in keys:
        if k not in urls.keys():
            with open(urls_path, 'w', encoding='utf-8') as f:
                json.dump(empty_urls_d, f)
                break
with open(urls_path, 'r', encoding='utf-8') as f:
    urls = json.load(f)

pages_folder = os.path.join(THIS_DIR, 'Pages')
if not os.path.exists(pages_folder):
    os.mkdir(pages_folder)

sess = requests.session()
login_post = sess.post(urls['login'], data=data)

def get_pages(sess):
    urls['pages'] = dict()
    course_pattern = '(\d{4}/\d{4}-\d) (.*?)$'
    dashboard_get = sess.get(urls['dashboard'])
    dashboard_text = dashboard_get.text
    soup = BeautifulSoup(dashboard_text, 'html.parser')
    courses = soup.find('select', attrs={'name': 'course'}).find_all('option')
    sem_s = set()
    for course in courses:
        course_find = re.search(course_pattern, course.text)
        if course_find:
            sem = course_find.group(1)
            if len(sem_s) == 0:
                print('Semester:', sem)
            sem_s.add(sem)
            if len(sem_s) > 1:
                break
            course_code = course_find.group(2)
            course_id = course['value']
            d_t = {'course_code': course_code, 'course_id': course_id, 'course_url': 'https://moodle.boun.edu.tr/course/view.php?id={}'.format(course_id), 'grade_url': 'https://moodle.boun.edu.tr/grade/report/user/index.php?id={}'.format(course_id)}
            urls['pages'][course_id] = d_t
    with open(urls_path, 'w', encoding='utf-8') as f:
        json.dump(urls, f, indent=4, ensure_ascii=False)
    return urls['pages']

if urls['pages']:
    pages = urls['pages']
else:
    pages = get_pages(sess)

ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def check_change(sess, pages):
    for course_id in pages.keys():
        course = pages[course_id]
        course_query = sess.get(course['course_url'])
        cq_text = course_query.text
        if 'This course is currently unavailable to students' in cq_text:
            with open(urls_path, 'w', encoding='utf-8') as f:
                json.dump(empty_urls_d, f)
            print('Run again, A previous course was not available')
            exit()
        if 'Your session has timed out' in cq_text or 'Please use your BOUN' in cq_text:
            print('Error')
            break
        soup = BeautifulSoup(cq_text, 'html.parser')
        for act in soup.find_all('img', class_='activityicon'):
            act.decompose()
        weeks = soup.find('ul', class_='weeks')
        topics = soup.find('ul', class_='topics')
        course_content = None
        if weeks:
            span_order_t = soup.find('span', class_='order-1')
            if span_order_t:
                span_order_t.decompose()
            course_content = str(weeks).replace('\n\n', '\n')
        elif topics:
            course_content = str(topics)
        if course_content == None:
            print('Course page of %s is not available' % course['course_code'])
        else:
            filepath = os.path.join(pages_folder, '{cc}_course.html'.format(cc=course['course_code']))
            if not os.path.exists(filepath):
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(course_content)
                    print_str = 'Course page of %s created' % course['course_code']
                    print(print_str, ts)
                    logger.info(print_str)
            else:
                with open(filepath, 'r', encoding='utf-8') as f:
                    previous_content = f.read()
                if course_content != previous_content:
                    print_str = 'Course page of %s changed' % course['course_code']
                    print(print_str, ts)
                    logger.info(print_str)
                    # beep(sound=1)
                    previous_path = os.path.join(pages_folder, '{cc}_course-prev.html'.format(cc=course['course_code']))
                    with open(previous_path, 'w', encoding='utf-8') as f:
                        f.write(previous_content)
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(course_content)
        grade_query = sess.get(course['grade_url'])
        gq_text = grade_query.text
        soup = BeautifulSoup(gq_text, 'html.parser')
        for act in soup.find_all('img', class_='itemicon'):
            act.decompose()
        grade_table = soup.find('table', class_='user-grade')
        if grade_table == None:
            print('Grade page of %s is not available' % course['course_code'])
            continue
        else:
            grade_table = str(grade_table)
            filepath = os.path.join(pages_folder, '{cc}_grade.html'.format(cc=course['course_code']))
            if not os.path.exists(filepath):
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(grade_table)
                    print_str = 'Grade page of %s created' % course['course_code']
                    print(print_str, ts)
                    logger.info(print_str)
            else:
                with open(filepath, 'r', encoding='utf-8') as f:
                    previous_content = f.read()
                if grade_table != previous_content:
                    print_str = 'Grade page of %s changed' % course['course_code']
                    print(print_str, ts)
                    logger.info(print_str)
                    # beep(sound=1)
                    previous_path = os.path.join(pages_folder, '{cc}_grade-prev.html'.format(cc=course['course_code']))
                    with open(previous_path, 'w', encoding='utf-8') as f:
                        f.write(previous_content)
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(grade_table)

check_change(sess, pages)
