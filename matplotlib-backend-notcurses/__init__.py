# SPDX-License-Identifier: CC0-1.0

import os
import sys

from subprocess import run

from matplotlib import interactive, is_interactive
from matplotlib._pylab_helpers import Gcf
from matplotlib.backend_bases import (_Backend, FigureManagerBase)
from matplotlib.backends.backend_agg import FigureCanvasAgg


# XXX heuristic for interactive repl
if sys.flags.interactive:
    interactive(True)


class FigureManagerNotcurses(FigureManagerBase):

    def show(self):

        margins = '0'

        if os.environ.get('MPLBACKEND_NOTCURSES_SIZING', 'automatic') != 'manual':

            # gather terminal dimensions
            # FIXME should use a less hacky way for getting width/height in pixels
            info = run(['notcurses-info'], text=True, capture_output=True).stdout.rstrip()
            dims = info.splitlines()[1].split(' ')
            rows, height, width = map(int, [dims[0].split('[K')[-1], *dims[6].split('x')])

            # account for post-display prompt scrolling
            # 3 line shift for [\n, <matplotlib.axes…, >>>] after the figure
            height -= int(3*(height/rows))
            margins = '0,0,3,0' # format: top, right, bottom, left

            dpi = self.canvas.figure.dpi
            self.canvas.figure.set_size_inches((width / dpi, height / dpi))

        r, w = os.pipe()
        try:
            with os.fdopen(w, 'wb') as wf:
                self.canvas.figure.savefig(wf, format='png', facecolor='#888888')
            run(['ncplayer', '-k', '-t0', '-q', '-m', margins, f'/dev/fd/{r}'], pass_fds=(r,))
        finally:
            os.close(r)


class FigureCanvasNotcurses(FigureCanvasAgg):
    manager_class = FigureManagerNotcurses


@_Backend.export
class _BackendNotcursesAgg(_Backend):

    FigureCanvas = FigureCanvasNotcurses
    FigureManager = FigureManagerNotcurses

    # Noop function instead of None signals that
    # this is an "interactive" backend
    mainloop = lambda: None

    # XXX: `draw_if_interactive` isn't really intended for
    # on-shot rendering. We run the risk of being called
    # on a figure that isn't completely rendered yet, so
    # we skip draw calls for figures that we detect as
    # not being fully initialized yet. Our heuristic for
    # that is the presence of axes on the figure.
    @classmethod
    def draw_if_interactive(cls):
        manager = Gcf.get_active()
        if is_interactive() and manager.canvas.figure.get_axes():
            cls.show()

    @classmethod
    def show(cls, *args, **kwargs):
        _Backend.show(*args, **kwargs)
        Gcf.destroy_all()
