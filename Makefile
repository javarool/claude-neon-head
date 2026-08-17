VENV := venv
PY   := $(VENV)/bin/python

.PHONY: venv install run clear \
        emotion-anger emotion-joy emotion-sad emotion-doubt emotion-anxiety emotion-interest emotion-neutral \
        say level speak

venv:
	python3 -m venv $(VENV)

install: venv
	$(PY) -m pip install -r requirements.txt

run:
	$(PY) run.py

## -- client examples --------------------------------------------------------

emotion-anger:
	$(PY) client.py emotion anger

emotion-joy:
	$(PY) client.py emotion joy

emotion-sad:
	$(PY) client.py emotion sad

emotion-doubt:
	$(PY) client.py emotion lol

emotion-anxiety:
	$(PY) client.py emotion anxiety

emotion-interest:
	$(PY) client.py emotion interest

emotion-neutral:
	$(PY) client.py emotion neutral

say:
	$(PY) client.py say "привет, как слышно"

level:
	$(PY) client.py level 0.8 0.3

speak:
	$(PY) client.py speak out.json out.wav

clear:
	$(PY) client.py clear
