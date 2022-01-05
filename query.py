import requests, re
from bs4 import BeautifulSoup
import os
import json

def get_class_pages(sess):
	dashboard_get = sess.get(urls['Dashboard'])
	dashboard_text = dashboard_get.text
	dashboard_text = dashboard_text[dashboard_text.index('My courses'):]
	dashboard_text = dashboard_text[:dashboard_text.index('\n')]
	course_pattern = '<a.*?href="(https://moodle.boun.edu.tr/course/view.php\?id=.*?)">(.*?)</a>'
	course_list = re.findall(course_pattern, dashboard_text)
	course_code_pattern = '[a-zA-Z]{2,4}[ \d]*'
	courses = []
	for i in course_list:
		course_code_found = re.search(course_code_pattern, i[1])
		if course_code_found:
			course_code = course_code_found.group().replace(' ', '')
			course_url = i[0]
			courses.append((course_code, course_url))
	urls['Class Pages'] = courses
	with open(urls_path, 'w', encoding='utf-8') as f:
		json.dump(urls, f)
	return courses

def get_grade_pages(sess):
	grade_get = sess.get(urls['Grade'])
	grade_text = grade_get.text
	grade_text = grade_text[grade_text.index('Course name'):]
	grade_text = grade_text[:grade_text.index('\n')]
	grade_url_pattern = '<a.*?href="(https://moodle.boun.edu.tr/course/user.php\?mode=grade.*?)">.*?</a>'
	grade_urls = re.findall(grade_url_pattern, grade_text)
	grades = []
	for i in grade_urls:
		get_grade = sess.get(i.replace('amp;', ''))
		grade_text = get_grade.text
		grade_text = grade_text[grade_text.index('Grades')+1:]
		grade_text = grade_text[grade_text.index('Grades'):]
		grade_text = grade_text[:grade_text.index('User report')]
		course_code_pattern = '<li.*?>.*?([a-zA-Z]{2,4}[ \d]*).*?</li>'
		course_code_found = re.search(course_code_pattern, grade_text)
		if course_code_found: course_code = course_code_found.group(1).replace(' ', '')
		grades.append((course_code, i))
	urls['Grades'] = grades
	with open(urls_path, 'w', encoding='utf-8') as f:
		json.dump(urls, f)
	return grades

def check_change(sess, page_list):
	types = ['Class Pages', 'Grades']
	for page_type_int in range(2):
		pages = page_list[page_type_int]
		page_type = types[page_type_int]
		for i in pages:
			query = sess.get(i[1])
			soup = BeautifulSoup(query.text, 'html.parser')
			file_path = f'{path}\\{page_type}\\{i[0]}.html'
			if not os.path.exists(file_path): open(file_path, 'w')
			query_text = re.sub('\s', '', soup.text)
			if 'LogInYoursessionhastimedout' in query_text or 'PleaseuseyourBOUNe' in query_text:
				print('Error')
				break
			if query_text != open(file_path, 'r', encoding='utf-8').read():
				if page_type_int == 0: print(f'{i[0]} Class Page changed')
				else: print(f'{i[0]} Grades Page changed')
				open(file_path, 'w', encoding='utf-8').write(query_text)

path = os.path.dirname(os.path.realpath(__file__))

credentials_path = f'{path}\\credentials.json'
if not os.path.exists(credentials_path):
	open(credentials_path, 'w', encoding='utf-8').write('{"username": "Username", "password": "Password"}')
	print('You need to add your credentials in "credentials.json" in the script folder.'); exit()
with open(credentials_path, 'r', encoding='utf-8') as f:
	data = json.load(f)

urls_path = f'{path}\\URLs.json'
if not os.path.exists(urls_path):
	open(urls_path, 'w', encoding='utf-8').write('{"Login": "https://moodle.boun.edu.tr/login/index.php", "Dashboard": "https://moodle.boun.edu.tr/my/", "Class Pages": [], "Grade": "https://moodle.boun.edu.tr/grade/report/overview/index.php", "Grades": []}')
with open(urls_path, 'r', encoding='utf-8') as f:
	urls = json.load(f)

folder_path = f'{path}//Grades'
if not os.path.exists(folder_path): os.mkdir(folder_path)

with requests.session() as sess:
	login_post = sess.post(urls['Login'], data=data)
	if urls['Class Pages'] != []: class_pages = urls['Class Pages']
	else: class_pages = get_class_pages(sess)
	if urls['Grades'] != []: grade_pages = urls['Grades']
	else: grade_pages = get_grade_pages(sess)
	check_change(sess, [class_pages, grade_pages])
	