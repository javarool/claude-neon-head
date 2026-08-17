# claude-neonhead

Процедурная говорящая голова: три вращающихся кольца, неоновый контур,
обрезанные глаза с белым яблоком и зрачком, брови, рот с зубами и планета
на орбите вместо носа. Ни одной 3D-модели — вся геометрия генерируется
в numpy каждый кадр.

Программа открывает окно и слушает порт. Ты шлёшь ей JSON: эмоции, визимы,
уровень громкости или готовый таймлайн от Chatterbox.

![превью](preview.png)

## Запуск

```bash
pip install -r requirements.txt
python run.py
```

`sounddevice` нужен только чтобы слышать wav во время `speak` — без него
таймлайн всё равно проигрывается, просто беззвучно.

```bash
python run.py --config my.json      # свой конфиг поверх дефолтного
```

Клавиши в окне: `1`–`9` эмоции (первые девять из списка; `surprise` — десятая,
без клавиши, отправляй `emotion`-командой), `d` демо-режим (перебирает все
эмоции), `y`/`n` жесты кивок/отказ, `пробел` тестовая фраза, `c` сброс,
`esc` выход.

## Протокол

Один JSON-объект на UDP-датаграмму (порт 9955), либо по объекту на строку
через TCP (порт 9956). Порядок и надёжность не важны — состояние всегда
интерполируется, ни одна команда не может дёрнуть лицо рывком.

```jsonc
{"type": "emotion", "name": "anger", "weight": 1.0, "blend_ms": 250}
{"type": "viseme",  "shape": "D"}
{"type": "level",   "rms": 0.7, "f0": 0.3}
{"type": "say",     "text": "привет, я слушаю"}
{"type": "speak",   "timeline": "out.json", "wav": "out.wav"}
{"type": "set",     "params": {"eye_gaze_x": -0.8, "brow_y_l": 0.6}}
{"type": "clear"}
{"type": "demo",    "on": true, "hold_s": 2.0}
{"type": "gesture", "name": "yes"}
{"type": "config",  "patch": {"palette": {"contour": "#3FB8C8"}}}
{"type": "title",   "text": "neonhead: /home/me/project"}
{"type": "quit"}
```

Эмоции: `neutral`, `interest`, `joy`, `anger`, `doubt`, `anxiety`, `sad`,
`fear`, `disgust`, `surprise`, `shame`. Русские алиасы тоже работают: `покой`,
`интерес`, `радость`, `злость`, `сомнение`, `тревога`, `грусть`, `страх`,
`отвращение`, `удивление`, `стыд`. Каждая описана в своём файле в
`neonhead/emotions/` — новый файл там сразу попадает в список эмоций и в
демо-режим, без правок в другом коде.

`demo` включает перебор всех эмоций из `neonhead/emotions/`, по `hold_s`
секунд на каждую (по умолчанию 2), пока не придёт `demo` с `"on": false`,
любая другая `emotion`-команда или `clear`.

Жесты — короткие анимации, а не статичная поза: `yes` (кивок, 3 цикла) и
`no` (покачивание, 3 цикла), сами гаснут по завершении. Живут в
`neonhead/gestures/`, тем же способом — новый файл там сразу становится
доступен по имени.

Визимы: `X` пауза, `A` мбп, `B` сзтднкгхцчшщйиы, `C` эе, `D` ая, `E` оё,
`F` ую, `G` фв, `H` лр.

### Из шелла

```bash
python client.py emotion anger
python client.py say "привет, как слышно"
python client.py level 0.8 0.3
python client.py set eye_gaze_x=-0.9 brow_y_l=0.7
python client.py config palette.contour=#3FB8C8 brightness.contour=4.5
python client.py demo 2.0
python client.py gesture yes
```
