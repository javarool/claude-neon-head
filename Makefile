VENV := venv
PY   := $(VENV)/bin/python

.PHONY: venv install run clear \
        emotion-anger emotion-joy emotion-sad emotion-doubt emotion-anxiety emotion-neutral \
        say level speak

venv:
	python3 -m venv $(VENV)

install: venv
	$(PY) -m pip install -r requirements.txt

run:
	$(PY) run.py

## -- client examples --------------------------------------------------------

emotion-anger:
	$(PY) client.py emotion fear

emotion-joy:
	$(PY) client.py emotion joy

emotion-sad:
	$(PY) client.py emotion sad

emotion-lol:
	$(PY) client.py emotion lol

emotion-anxiety:
	$(PY) client.py emotion anxiety

emotion-neutral:
	$(PY) client.py emotion neutral

say:
	$(PY) client.py say "hello, can you hear me (lol)"

level:
	$(PY) client.py level 0.8 0.3

speak:
	$(PY) client.py speak timeline.json audio.wav

clear:
	$(PY) client.py clear
