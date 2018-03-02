import datetime
import math
import os
import random
from typing import Tuple

import forecastio
from PIL import Image, ImageDraw, ImageFont

from util import draw_text_relative

SCALE_FONT = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf", size=10)
NOTE_FONT = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf", size=25)

PERCIP_RANGE = 5
MIN_TEMP_RANGE = 15  # degrees
TEMP_PADDING = 2.5  # degrees

PLOT_AREA_HEIGHT = 183
TIME_SCALE_HEIGHT = 15
TIME_SCALE_PADDING = 3
VERTICAL_SCALE_HEIGHT = PLOT_AREA_HEIGHT + TIME_SCALE_HEIGHT
LEFT_SCALE_WIDTH = SCALE_FONT.getsize("-10")[0]
RIGHT_SCALE_WIDTH = SCALE_FONT.getsize("10")[0]
RIGHT_SCALE_WIDTH_WITH_LABEL = SCALE_FONT.getsize("mm")[0]
PLOT_AREA_WIDTH = 400 - LEFT_SCALE_WIDTH - RIGHT_SCALE_WIDTH
CLOUD_COVER_HEIGHT = 20

PRIME_1 = 113

DARKSKY_API_KEY = os.getenv("DARKSKY_API_KEY")
if not DARKSKY_API_KEY:
    print("No DARKSKY_API_KEY env variable")

_pseudo_permute_cache = {}


def _pseudo_permute(value: int, limit: int):
    assert 0 <= value < limit
    if limit not in _pseudo_permute_cache:
        _pseudo_permute_cache[limit] = list(range(limit))
        rng = random.Random()
        rng.seed(0)
        rng.shuffle(_pseudo_permute_cache[limit])
    return _pseudo_permute_cache[limit][value]


def draw_forecast(draw_target):
    now = datetime.datetime.now()
    end = now + datetime.timedelta(hours=47)
    shown_points = _load_points(now, end)

    def graph_y(value: float) -> float:
        return PLOT_AREA_HEIGHT * (1 - value)

    def graph_x(point_time: datetime.datetime) -> float:
        rel_time = point_time.timestamp() - now.timestamp()
        return rel_time * PLOT_AREA_WIDTH / (end.timestamp() - now.timestamp())

    def graph_point(point_time: datetime.datetime, value: float) -> Tuple[float, float]:
        return graph_x(point_time), graph_y(value)

    left_scale_image = Image.new('1', (LEFT_SCALE_WIDTH, VERTICAL_SCALE_HEIGHT), 1)
    right_scale_image = Image.new('1', (RIGHT_SCALE_WIDTH_WITH_LABEL, VERTICAL_SCALE_HEIGHT), 1)
    plot_area_image = Image.new('1', (PLOT_AREA_WIDTH, PLOT_AREA_HEIGHT), 1)
    time_scale_image = Image.new('1', (PLOT_AREA_WIDTH, TIME_SCALE_HEIGHT), 1)

    plot_area_draw = ImageDraw.Draw(plot_area_image)
    left_scale_draw = ImageDraw.Draw(left_scale_image)
    right_scale_draw = ImageDraw.Draw(right_scale_image)
    time_scale_draw = ImageDraw.Draw(time_scale_image)

    percip_scale = 1 / PERCIP_RANGE
    temp_max = max(map(lambda pt: max(pt.temperature, pt.dewPoint), shown_points))
    temp_min = min(map(lambda pt: min(pt.temperature, pt.dewPoint), shown_points))
    if temp_max - temp_min > MIN_TEMP_RANGE:
        temp_base = temp_min
        temp_range = temp_max - temp_min
    else:
        temp_base = temp_min - (MIN_TEMP_RANGE - (temp_max - temp_min)) / 2
        temp_range = MIN_TEMP_RANGE

    temp_base -= TEMP_PADDING
    temp_range += TEMP_PADDING * 2

    temp_scale = 1 / temp_range

    # draw precipitation
    plot_area_draw.polygon([graph_point(point.time, point.precipIntensity * percip_scale)
                            for point in shown_points] + [graph_point(end, 0), graph_point(now, 0)], fill='#000000')
    # draw dew point
    plot_area_draw.line([graph_point(point.time, (point.dewPoint - temp_base) * temp_scale) for point
                         in shown_points], width=1, fill='#000000')
    # draw temperature
    plot_area_draw.line([graph_point(point.time, (point.temperature - temp_base) * temp_scale) for point
                         in shown_points], width=2, fill='#000000')

    # draw scale for temperature
    for mark in range(int(math.ceil(temp_base / 5) * 5), int(math.ceil((temp_base + temp_range) / 5) * 5), 5):
        y = graph_y((mark - temp_base) * temp_scale)
        # label
        draw_text_relative(left_scale_draw, (LEFT_SCALE_WIDTH, y), str(int(mark)), font=SCALE_FONT, xa=1, ya=.5)
        # dotted line
        for x in range(0, PLOT_AREA_WIDTH, 3):
            plot_area_draw.point((x, y), fill='#000000')

    # draw scale for percipitation
    for mark in range(0, PERCIP_RANGE + 1, 2):
        y = graph_y(mark * percip_scale)
        right_scale_draw.text((RIGHT_SCALE_WIDTH_WITH_LABEL - RIGHT_SCALE_WIDTH,
                               y - SCALE_FONT.getsize(str(int(mark)))[1] / 2), str(int(mark)), font=SCALE_FONT)

    # scale names
    right_scale_draw.text((0, PLOT_AREA_HEIGHT + TIME_SCALE_PADDING), "mm", font=SCALE_FONT)
    left_scale_draw.text((2, PLOT_AREA_HEIGHT + TIME_SCALE_PADDING), "°C", font=SCALE_FONT)

    # draw time scale
    time_scale_time = now - datetime.timedelta(seconds=now.second, minutes=now.minute, hours=now.hour % 6)
    while True:
        time_scale_time += datetime.timedelta(hours=6)
        if time_scale_time > end:
            break
        x = graph_x(time_scale_time)
        draw_text_relative(time_scale_draw, (x, TIME_SCALE_PADDING), time_scale_time.strftime("%H:%M"),
                           font=SCALE_FONT, xa=.5)
        if time_scale_time.hour == 0:
            plot_area_draw.line([(x - 1, 0), (x - 1, PLOT_AREA_HEIGHT)], fill='#000000')

    temp_min_point = min(shown_points, key=lambda pt: pt.temperature)
    draw_text_relative(plot_area_draw,
                       graph_point(temp_min_point.time, (temp_min_point.temperature - temp_base) * temp_scale),
                        "%.1f°C" % temp_min_point.temperature, NOTE_FONT, xa=.5, ya=-0.1, clamp_image=plot_area_image)
    temp_max_point = max(shown_points, key=lambda pt: pt.temperature)
    draw_text_relative(plot_area_draw,
                       graph_point(temp_max_point.time, (temp_max_point.temperature - temp_base) * temp_scale),
                        "%.1f°C" % temp_max_point.temperature, NOTE_FONT, xa=.5, ya=1.1, clamp_image=plot_area_image)

    # finish up
    del plot_area_draw
    del left_scale_draw
    del right_scale_draw
    del time_scale_draw

    draw_target.draw(left_scale_image, 0, 300 - VERTICAL_SCALE_HEIGHT)
    draw_target.draw(time_scale_image, LEFT_SCALE_WIDTH, 300 - TIME_SCALE_HEIGHT)
    draw_target.draw(right_scale_image, 400 - RIGHT_SCALE_WIDTH_WITH_LABEL, 300 - VERTICAL_SCALE_HEIGHT)
    draw_target.draw(plot_area_image, LEFT_SCALE_WIDTH, 300 - VERTICAL_SCALE_HEIGHT)
    draw_target.draw(draw_cloud_cover(graph_x, shown_points), LEFT_SCALE_WIDTH,
                     300 - VERTICAL_SCALE_HEIGHT - CLOUD_COVER_HEIGHT)


def draw_cloud_cover(graph_x, shown_points):
    cloud_cover_image = Image.new('L', (PLOT_AREA_WIDTH, CLOUD_COVER_HEIGHT), 255)
    cloud_cover_draw = ImageDraw.Draw(cloud_cover_image)
    for point in shown_points:
        point_start = int(graph_x(point.time - datetime.timedelta(minutes=30)))
        point_end = int(graph_x(point.time + datetime.timedelta(minutes=30)))
        cloud_cover_draw.rectangle(((point_start, 0), (point_end, CLOUD_COVER_HEIGHT)),
                                   fill=(int(255 * (1 - point.cloudCover))))
    del cloud_cover_draw
    return cloud_cover_image.convert("1", dither=Image.FLOYDSTEINBERG)


def _load_points(start, end):
    forecast = forecastio.load_forecast(
        key=DARKSKY_API_KEY,
        lat=49.579981,
        lng=11.020197,
        units="ca",
        lazy=True
    )
    points = forecast.hourly().data
    start_offset = 0
    end_offset = len(points)
    for i in range(len(points)):
        point = points[i]
        if point.time < start:
            start_offset = i
        if point.time > end and end_offset > i:
            end_offset = i
            break
    shown_points = points[start_offset:end_offset + 1]
    return shown_points
