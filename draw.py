import datetime
import re
import time
import traceback
import urllib.request
from typing import Optional

import requests
from PIL import Image, ImageDraw, ImageFont

import util
import weather

print("Loading fonts")

PATH_DROID_SANS = "/usr/share/fonts/TTF/DroidSans.ttf"

TIME_FONT = ImageFont.truetype(PATH_DROID_SANS, size=50)
TEMP_FONT = ImageFont.truetype(PATH_DROID_SANS, size=40)
CO2_FONT = ImageFont.truetype(PATH_DROID_SANS, size=25)

SPACING = 5
CO2_SPACING = 20


def _font_for_max_width(font_path, text, max_width) -> ImageFont.ImageFont:
    low = 0
    low_font = None
    high = -1
    while True:
        if high == -1:
            now = max(low * 2, 10)
        else:
            now = (high + low) // 2
            assert now <= high
        if now <= low:
            return low_font
        font = ImageFont.truetype(font_path, size=now)
        width, height = font.getsize(text)
        if width > max_width:
            high = now
        else:
            low_font = font
            low = now


def _telnet_get(host: str, port: int) -> str:
    import socket
    with socket.create_connection((host, port)) as s:
        return s.makefile(encoding="UTF-8").read()


def loop(draw_target):
    print("Adjusting font sizes")
    time_width, time_height = TIME_FONT.getsize("00:00")
    date_font = _font_for_max_width(PATH_DROID_SANS, "0000-00-00", time_width)
    date_width, date_height = date_font.getsize("0000-00-00")

    minutes_passed = 0

    def draw_time(delta):
        image = Image.new('1', (time_width, time_height + date_height + SPACING), 1)
        draw = ImageDraw.Draw(image)
        now = datetime.datetime.now() + datetime.timedelta(seconds=delta)
        draw.text((0, 0), now.strftime("%H:%M"), font=TIME_FONT)
        draw.text(((time_width - date_width) // 2, time_height + SPACING),
                  now.strftime("%Y-%m-%d"), font=date_font)
        del draw
        draw_target.draw(image, 400 - time_width, 0)

    temp_width, temp_height = TEMP_FONT.getsize("-10.0°C")

    def draw_temp():
        temp: Optional[float] = None
        try:
            lines = _telnet_get("ente.hawo.stw.uni-erlangen.de", 7337).splitlines()
            temp = float(re.match(r"^(.+?)°C.*", lines[0]).group(1))
        except IOError:
            traceback.print_exc()
        image = Image.new('1', (temp_width, temp_height), 1)
        draw = ImageDraw.Draw(image)
        if temp is None:
            text = "NaN"
        else:
            text = "%.1f°C" % temp
        draw.text((0, 0), text, font=TEMP_FONT)
        del draw
        draw_target.draw(image, 0, 0)

    co2_width, co2_height = CO2_FONT.getsize("2000ppm")

    def draw_co2():
        data: Optional[dict] = None
        try:
            response = requests.request("GET", "http://127.0.0.1:8000")
            if response.status_code == 200:
                data = response.json()
        except IOError:
            traceback.print_exc()
        image = Image.new('1', (co2_width, co2_height), 1)
        draw = ImageDraw.Draw(image)
        if data and "co2" in data:
            util.draw_text_relative(draw, (co2_width, 0), "%dppm" % data["co2"], CO2_FONT, xa=1)
        del draw
        draw_target.draw(image, 0, temp_height + 10)

    expected_flush_time = 0
    while True:
        if minutes_passed % 15 == 0:
            weather.draw_forecast(draw_target)
        if minutes_passed % 5 == 0:
            draw_temp()
        draw_co2()
        draw_time(expected_flush_time)

        flush_start = time.time()
        draw_target.flush()
        flush_end = time.time()
        # estimate flush time, and start updating display a little earlier than that
        if flush_end > flush_start:
            expected_flush_time = expected_flush_time * 0.9 + (flush_end - flush_start) * 0.1

        sleep = 60 - (time.time() % 60) - expected_flush_time
        if sleep > 0:
            time.sleep(sleep)
        minutes_passed += 1
