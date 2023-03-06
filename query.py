import requests, re, os, json, argparse
from bs4 import BeautifulSoup
from datetime import datetime
import logging

THIS_DIR = os.path.dirname(os.path.realpath(__file__))

log_path = os.path.join(THIS_DIR, 'changes.log')
logging.basicConfig(filename=log_path, level=logging.INFO, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser(description='Query Moodle for changes in course pages and grades.')
parser.add_argument('-s', '--semester', type=str, help='Semester to query, e.g. 2022/2023-2')
args = parser.parse_args()

sem_pattern = r'^\d{4}/\d{4}-\d$'

data_path = os.path.join(THIS_DIR, 'data.json')
if not os.path.exists(data_path):
    if args.semester:
        semester = args.semester
        sem_search = re.search(sem_pattern, semester)
        if not sem_search:
            print('Invalid semester format in arguments. Example: 2022/2023-2')
            exit()
        else:
            semester = sem_search.group(0)
            with open(data_path, 'w', encoding='utf-8') as f:
                json.dump({'semester': semester}, f)
    else:
        semester = input('Semester: ')
        sem_search = re.search(sem_pattern, semester)
        if not sem_search:
            print('Invalid semester format input. Example: 2022/2023-2')
            exit()
        else:
            semester = sem_search.group(0)
            with open(data_path, 'w', encoding='utf-8') as f:
                json.dump({'semester': semester}, f)
else:
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        semester = data['semester']

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
empty_urls_d = { "Login": "https://moodle.boun.edu.tr/login/index.php", "Dashboard": "https://moodle.boun.edu.tr/my/", "Pages": {} }
if not os.path.exists(urls_path):
    with open(urls_path, 'w', encoding='utf-8') as f:
        json.dump(empty_urls_d, f)
else:
    with open(urls_path, 'r', encoding='utf-8') as f:
        try:
            urls = json.load(f)
        except:
            urls = {}
    keys = ['Dashboard', 'Login', 'Pages']
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
login_post = sess.post(urls['Login'], data=data)

def get_pages(sess):
    urls['Pages'] = {}
    course_pattern = f'{semester} (.*?)$'
    dashboard_get = sess.get(urls['Dashboard'])
    dashboard_text = dashboard_get.text
    soup = BeautifulSoup(dashboard_text, 'html.parser')
    courses = soup.find('select', attrs={'name': 'course'}).find_all('option')
    for course in courses:
        course_find = re.search(course_pattern, course.text)
        if course_find:
            course_code = course_find.group(1)
            course_id = course['value']
            d_t = {'course_code': course_code, 'course_id': course_id, 'course_url': f'https://moodle.boun.edu.tr/course/view.php?id={course_id}', 'grade_url': f'https://moodle.boun.edu.tr/grade/report/user/index.php?id={course_id}'}
            urls['Pages'][course_id] = d_t
    with open(urls_path, 'w', encoding='utf-8') as f:
        json.dump(urls, f, indent=4, ensure_ascii=False)
    return urls['Pages']

if urls['Pages'] != {}:
    pages = urls['Pages']
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
            soup.find('span', class_='order-1').decompose()
            course_content = str(weeks).replace('\n\n', '\n')
        elif topics:
            course_content = str(topics)
        if course_content == None:
            print(f'{course["course_code"]} Course Page is not available')
        else:
            filepath = os.path.join(pages_folder, '{cc}_course.html'.format(cc=course['course_code']))
            if not os.path.exists(filepath):
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(course_content)
                    print_str = '{cc} Course Page created'.format(cc=course['course_code'])
                    print(print_str, ts)
                    logger.info(print_str)
            else:
                with open(filepath, 'r', encoding='utf-8') as f:
                    previous_content = f.read()
                if course_content != previous_content:
                    print_str = '{cc} Course Page changed'.format(cc=course['course_code'])
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
            print(f'{course["course_code"]} Grade Page is not available')
            continue
        else:
            grade_table = str(grade_table)
            filepath = os.path.join(pages_folder, '{cc}_grade.html'.format(cc=course['course_code']))
            if not os.path.exists(filepath):
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(grade_table)
                    print_str = '{cc} Grade Page created'.format(cc=course['course_code'])
                    print(print_str, ts)
                    logger.info(print_str)
            else:
                with open(filepath, 'r', encoding='utf-8') as f:
                    previous_content = f.read()
                if grade_table != previous_content:
                    print_str = '{cc} Grade Page changed'.format(cc=course['course_code'])
                    print(print_str, ts)
                    logger.info(print_str)
                    # beep(sound=1)
                    previous_path = os.path.join(pages_folder, '{cc}_grade-prev.html'.format(cc=course['course_code']))
                    with open(previous_path, 'w', encoding='utf-8') as f:
                        f.write(previous_content)
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(grade_table)

check_change(sess, pages)
