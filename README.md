# inkstate

e-ink status display.

## Files

- `epdif.py`, `epd4in2.py` contain the display drivers from waveshare
- `draw.py` with `util.py` and `weather.py` handles the drawing (to an API that accepts PIL)
- `main_4in2.py` is the actual main application which drives the e-ink display (also implements the partial refresh) and delegates to `draw.py` for drawing
- `test.py` is an alternative application that invokes `draw.py` with a mock wx-based display for testing on the desktop

## Setup

This project is currently not ready for out-of-the-box use by other people.

- The project is not OS-agnostic
- It uses internal APIs for CO2 and temperature displays
- Location info for the weather API is hardcoded
