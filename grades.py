import requests, re
from bs4 import BeautifulSoup
import os
import json

path = os.path.dirname(os.path.realpath(__file__))

credentials_path = f'{path}\\credentials.json'
if not os.path.exists(credentials_path):
	open(credentials_path, 'w', encoding='utf-8').write('{"username": "Username", "password": "Password"}')
	print('You need to add your credentials in "credentials.json" in the script folder.'); exit()
with open(credentials_path, 'r', encoding='utf-8') as f:
	data = json.load(f)

login_url = 'https://moodle.boun.edu.tr/login/index.php'
grade_urls = [('Course_Code', 'Grade_URL'), ('Course_Code', 'Grade_URL'), ('Course_Code', 'Grade_URL'), ('Course_Code', 'Grade_URL'), ('Course_Code', 'Grade_URL'), ('Course_Code', 'Grade_URL')]
folder_path = f'{path}//Grades'
if not os.path.exists(folder_path): os.mkdir(folder_path)

for i in grade_urls:
	if i[0] == 'Course_Code': print('You need to add your course codes and grade URLs to the "grades.py" script file.'); exit()

with requests.session() as sess:
	login_post = sess.post(login_url, data=data)
	for i in grade_urls:
		grade = sess.get(i[1])
		soup = BeautifulSoup(grade.text, 'html.parser')
		file_path = f'{path}\\Grades\\{i[0]}.html'
		if not os.path.exists(file_path): open(file_path, 'w')
		grade_text = re.sub('\s', '', soup.text)
		if 'LogInYoursessionhastimedout' in grade_text or 'PleaseuseyourBOUNe' in grade_text:
			print('Error')
			break
		if grade_text != open(file_path, 'r', encoding='utf-8').read():
			print(f'{i[0]} grades page changed')
			open(file_path, 'w', encoding='utf-8').write(grade_text)