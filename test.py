import threading

import wx
from PIL import Image


# noinspection PyMethodMayBeStatic
class TestDrawTarget:
    def draw(self, image: Image, x: int = 0, y: int = 0):
        wx_image: wx.Image = wx.Image(image.size[0], image.size[1])
        wx_image.SetData(image.convert('RGB').tobytes())

        dc = wx.MemoryDC()
        dc.SelectObject(bitmap)
        dc.DrawBitmap(wx_image.ConvertToBitmap(), x, y)

    def flush(self):
        frame.Refresh()


app = wx.App(False)
frame = wx.Frame(None, style=wx.FRAME_FLOAT_ON_PARENT)

bitmap = wx.Bitmap(width=400, height=300)

tdc = wx.MemoryDC()
tdc.SelectObject(bitmap)
tdc.DrawRectangle(0, 0, 400, 300)


def paint(event=None):
    dc = wx.ClientDC(window=frame)
    dc.Clear()
    dc.DrawBitmap(bitmap, 0, 0, True)


frame.Bind(wx.EVT_PAINT, paint)

frame.Show()


def run():
    import draw

    draw.loop(TestDrawTarget())


threading.Thread(target=run, daemon=True).start()

app.MainLoop()
