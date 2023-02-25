# moodle_query

This script automatically queries if Moodle class / grade pages changed after the last execution. The script is for Boğaziçi University Moodle accounts, but it can be modified for other universities.

It's just a one-file script, `query.py`. It needs Python. After that's satisfied, "requirements" should be satisfied, which can be done with running the command `pip install -r requirements.txt`.

The credentials should be entered in the file `credentials.json`.

The semester is stored in the `semester` variable, in the format `year1/year2-term` (e.g. `2022/2023-2`). It can be provided as a flag: `python3 query.py --semester 2022/2023-2` or input when asked. Once it's given, throughout the semester, there is no need to provide it again.

Requirements: `bs4, requests`
