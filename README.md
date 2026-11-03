# DuckyPad  <br />  <img alt="Stargazers" src="https://img.shields.io/github/stars/i-is-evil-duck/ducky.mixer?style=for-the-badge&logo=starship&color=C9CBFF&logoColor=D9E0EE&labelColor=302D41">
volume mixer with a customizable macro pad

## About
Project files for my custom volume control macro pad

## Software
+ `arduino/` — firmware for the deej-style serial protocol (`slider1|...|slider5|btn1|...|btn8 @ 9600 baud`)
+ `app/python-dash/` — Python control app with a browser dashboard: slider → volume / per-app volume / monitor brightness mapping, 8-button macro pad, live serial calibration. Run with `pip install -r requirements.txt` then `python run.py` (opens http://127.0.0.1:8420)



## ToDo
+ rgb sliders & macro pad
+ rgb underglow
+ rgb tft display
+ update case design

mabey v2?
+ redo with esp or nrf instead of arduino so i can make it wireless
+ rgb control through wled so u can sync to signal rgb or custom interface

## Views

<img src="https://count.getloli.com/get/@mixer.ducky?theme=rule34" />
