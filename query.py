import requests, re, os, json
from bs4 import BeautifulSoup
from datetime import datetime
import logging

print('Checking for changes on Moodle...')

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

urls_d = { "login": "https://moodle.boun.edu.tr/login/index.php", "courses": "https://moodle.boun.edu.tr/my" }

pages_folder = os.path.join(THIS_DIR, 'pages')
if not os.path.exists(pages_folder):
    os.mkdir(pages_folder)

sess = requests.session()
login_post = sess.post(urls_d['login'], data=data)

def get_pages(sess):
    pages_d = dict()
    course_pattern = '(\d{4}/\d{4}-\d) (.*?)$'
    courses_get = sess.get(urls_d['courses'])
    soup = BeautifulSoup(courses_get.text, 'html.parser')
    courses = soup.find('select', attrs={'name': 'course'}).find_all('option')
    sem_l = list()
    for course in courses:
        course_find = re.search(course_pattern, course.text)
        if course_find:
            sem = course_find.group(1)
            sem_l.append(sem)
    sel_sem = sorted(sem_l)[-1]
    print('Semester:', sel_sem)
    for course in courses:
        course_find = re.search(course_pattern, course.text)
        if course_find:
            sem = course_find.group(1)
            if sem != sel_sem:
                continue
            course_code = course_find.group(2)
            course_id = course['value']
            d_t = {'course_code': course_code, 'course_id': course_id, 'course_url': 'https://moodle.boun.edu.tr/course/view.php?id={}'.format(course_id), 'grade_url': 'https://moodle.boun.edu.tr/grade/report/user/index.php?id={}'.format(course_id)}
            pages_d[course_code] = d_t
    return pages_d

pages_d = get_pages(sess)

ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def check_change(sess, pages):
    for course_code in pages:
        course = pages[course_code]
        course_query = sess.get(course['course_url'])
        cq_text = course_query.text
        if 'This course is currently unavailable to students' in cq_text:
            print('Course page of %s is not available' % course['course_code'])
            continue
        elif 'Your session has timed out' in cq_text or 'Please use your BOUN' in cq_text:
            print('Session timed out. Please run the script again.')
            continue
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
            course_content = course_content.replace('\r', '')
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
                    previous_path = os.path.join(pages_folder, '{cc}_grade-prev.html'.format(cc=course['course_code']))
                    with open(previous_path, 'w', encoding='utf-8') as f:
                        f.write(previous_content)
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(grade_table)

check_change(sess, pages_d)
