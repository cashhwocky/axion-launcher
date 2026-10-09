"""Axion-style Kivy home launcher with a built-in Volume Styles Selector."""
import json
import os
import threading

from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import (Color, Ellipse, Rectangle, RoundedRectangle,
                           StencilPop, StencilPush, StencilUnUse, StencilUse)
from kivy.metrics import dp
from kivy.properties import (BooleanProperty, ListProperty, NumericProperty,
                             StringProperty)
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget
from kivy.utils import platform

Window.softinput_mode = 'pan'

APPS_PER_PAGE = 24  # 4 columns x 6 rows
ICON_PX = 144


# --------------------------------------------------------------------------
# Widgets
# --------------------------------------------------------------------------
class AppIcon(ButtonBehavior, BoxLayout):
    label = StringProperty('')
    icon = StringProperty('')
    pkg = StringProperty('')


class StyleCard(ButtonBehavior, BoxLayout):
    style = StringProperty('aosp')
    title = StringProperty('')


class HomeScreen(Screen):
    pass


class SettingsScreen(Screen):
    pass


class VolumeBar(Widget):
    """One widget, three looks: 'aosp', 'ios', 'indigo'."""
    style = StringProperty('aosp')
    level = NumericProperty(0.5)
    compact = BooleanProperty(False)

    SIZES = {  # (normal, compact) in dp
        'aosp': ((56, 160), (30, 80)),
        'ios': ((48, 170), (26, 80)),
        'indigo': ((220, 52), (110, 28)),
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.bind(style=self._resize, compact=self._resize)
        self.bind(pos=self._draw, size=self._draw, level=self._draw,
                  style=self._draw)
        self._resize()
        Clock.schedule_once(self._bind_app, 0)

    def _bind_app(self, *_):
        app = App.get_running_app()
        if app:
            app.bind(accent=self._draw)
        self._draw()

    def _resize(self, *_):
        normal, compact = self.SIZES.get(self.style, self.SIZES['aosp'])
        w, h = compact if self.compact else normal
        self.size = (dp(w), dp(h))

    def _clipped_fill(self, radius, vertical, fill_rgba):
        x, y, w, h = self.x, self.y, self.width, self.height
        lv = max(0.0, min(1.0, self.level))
        StencilPush()
        RoundedRectangle(pos=(x, y), size=(w, h), radius=[radius])
        StencilUse()
        Color(*fill_rgba)
        if vertical:
            Rectangle(pos=(x, y), size=(w, h * lv))
        else:
            Rectangle(pos=(x, y), size=(w * lv, h))
        StencilUnUse()
        RoundedRectangle(pos=(x, y), size=(w, h), radius=[radius])
        StencilPop()

    def _draw(self, *_):
        app = App.get_running_app()
        acc = list(app.accent) if app else [0.8, 0.82, 1, 1]
        x, y, w, h = self.x, self.y, self.width, self.height
        self.canvas.clear()
        with self.canvas:
            if self.style == 'aosp':
                r = dp(8) if self.compact else dp(14)
                Color(0.16, 0.17, 0.20, 0.97)
                RoundedRectangle(pos=(x, y), size=(w, h), radius=[r])
                self._clipped_fill(r, True, acc)
            elif self.style == 'ios':
                r = w / 2.0
                Color(1, 1, 1, 0.28)
                RoundedRectangle(pos=(x, y), size=(w, h), radius=[r])
                self._clipped_fill(r, True, (1, 1, 1, 0.96))
            else:  # indigo
                r = h / 2.0
                Color(0.10, 0.12, 0.30, 0.97)
                RoundedRectangle(pos=(x, y), size=(w, h), radius=[r])
                self._clipped_fill(r, False, (0.36, 0.42, 0.75, 1))
                d = h * 0.72
                lv = max(0.0, min(1.0, self.level))
                tx = x + (h - d) / 2 + (w - h) * lv
                Color(0.77, 0.79, 0.91, 1)
                Ellipse(pos=(tx, y + (h - d) / 2), size=(d, d))


# --------------------------------------------------------------------------
# App
# --------------------------------------------------------------------------
class LauncherApp(App):
    # Material You palette (overwritten from system colors on Android 12+)
    accent = ListProperty([0.80, 0.82, 1.00, 1])
    surface = ListProperty([0.07, 0.07, 0.09, 1])
    container = ListProperty([0.14, 0.14, 0.17, 1])
    volume_style = StringProperty('aosp')

    apps = []
    am = None
    vol_max = {2: 7, 3: 15}
    _last_vol = {}

    # ---- lifecycle -------------------------------------------------------
    def build(self):
        self.title = 'Axion Launcher'
        self._load_prefs()
        self._load_material_colors()
        Window.bind(on_keyboard=self._on_key)
        return None  # root comes from launcher.kv

    def on_start(self):
        threading.Thread(target=self._load_apps_thread, daemon=True).start()
        self._init_audio()
        Clock.schedule_interval(self._poll_volume, 0.15)

    def on_pause(self):
        return True

    def on_resume(self):
        try:
            home = self.root.ids.home
            home.ids.search.text = ''
            home.ids.pager.load_slide(home.ids.pager.slides[0])
        except Exception:
            pass

    # ---- prefs -----------------------------------------------------------
    def _prefs_path(self):
        return os.path.join(self.user_data_dir, 'prefs.json')

    def _load_prefs(self):
        try:
            with open(self._prefs_path()) as f:
                self.volume_style = json.load(f).get('volume_style', 'aosp')
        except Exception:
            pass

    def on_volume_style(self, *_):
        try:
            with open(self._prefs_path(), 'w') as f:
                json.dump({'volume_style': self.volume_style}, f)
        except Exception:
            pass

    def set_style(self, style):
        self.volume_style = style
        self.show_volume(0.6)

    # ---- Material You ----------------------------------------------------
    def _load_material_colors(self):
        if platform != 'android':
            return
        try:
            from jnius import autoclass
            act = autoclass('org.kivy.android.PythonActivity').mActivity
            R = autoclass('android.R$color')
            res, theme = act.getResources(), act.getTheme()

            def c(res_id):
                v = res.getColor(res_id, theme) & 0xFFFFFFFF
                return [((v >> 16) & 255) / 255.0, ((v >> 8) & 255) / 255.0,
                        (v & 255) / 255.0, 1]

            self.accent = c(R.system_accent1_200)
            self.surface = c(R.system_neutral1_900)
            self.container = c(R.system_neutral2_800)
        except Exception as e:
            print('Material colors unavailable:', e)

    # ---- app list --------------------------------------------------------
    def _load_apps_thread(self):
        apps = self._query_apps()
        Clock.schedule_once(lambda dt: self._set_apps(apps))

    def _set_apps(self, apps):
        self.apps = apps
        self._build_pages(apps)

    def _query_apps(self):
        if platform != 'android':
            return [{'label': 'App %d' % i, 'icon': '', 'pkg': 'demo.%d' % i}
                    for i in range(1, 31)]
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        Intent = autoclass('android.content.Intent')
        Bitmap = autoclass('android.graphics.Bitmap')
        Config = autoclass('android.graphics.Bitmap$Config')
        Fmt = autoclass('android.graphics.Bitmap$CompressFormat')
        Canvas = autoclass('android.graphics.Canvas')
        FileOutputStream = autoclass('java.io.FileOutputStream')

        act = PythonActivity.mActivity
        pm = act.getPackageManager()
        own = act.getPackageName()
        icon_dir = os.path.join(self.user_data_dir, 'icons')
        os.makedirs(icon_dir, exist_ok=True)

        intent = Intent(Intent.ACTION_MAIN)
        intent.addCategory(Intent.CATEGORY_LAUNCHER)
        resolved = pm.queryIntentActivities(intent, 0)

        out = []
        for i in range(resolved.size()):
            ri = resolved.get(i)
            pkg = ri.activityInfo.packageName
            if pkg == own:
                continue
            label = ri.loadLabel(pm).toString()
            path = os.path.join(icon_dir, pkg + '.png')
            if not os.path.exists(path):
                try:
                    d = ri.loadIcon(pm)
                    bmp = Bitmap.createBitmap(ICON_PX, ICON_PX,
                                              Config.ARGB_8888)
                    cv = Canvas(bmp)
                    d.setBounds(0, 0, ICON_PX, ICON_PX)
                    d.draw(cv)
                    fos = FileOutputStream(path)
                    bmp.compress(Fmt.PNG, 100, fos)
                    fos.flush()
                    fos.close()
                except Exception as e:
                    print('icon failed', pkg, e)
                    path = ''
            out.append({'label': label, 'icon': path, 'pkg': pkg})
        out.sort(key=lambda a: a['label'].lower())
        return out

    def _build_pages(self, apps):
        pager = self.root.ids.home.ids.pager
        pager.clear_widgets()
        total = max(len(apps), 1)
        for start in range(0, total, APPS_PER_PAGE):
            grid = GridLayout(cols=4, rows=6, spacing=dp(2), padding=dp(2))
            for a in apps[start:start + APPS_PER_PAGE]:
                grid.add_widget(AppIcon(label=a['label'], icon=a['icon'],
                                        pkg=a['pkg']))
            pager.add_widget(grid)

    def filter_apps(self, text):
        q = text.strip().lower()
        shown = [a for a in self.apps if q in a['label'].lower()] if q \
            else self.apps
        self._build_pages(shown)

    def launch(self, pkg):
        if platform != 'android':
            print('would launch', pkg)
            return
        from jnius import autoclass
        act = autoclass('org.kivy.android.PythonActivity').mActivity
        it = act.getPackageManager().getLaunchIntentForPackage(pkg)
        if it:
            act.startActivity(it)

    # ---- navigation ------------------------------------------------------
    def open_settings(self):
        sm = self.root.ids.sm
        sm.transition.direction = 'left'
        sm.current = 'settings'

    def close_settings(self):
        sm = self.root.ids.sm
        sm.transition.direction = 'right'
        sm.current = 'home'

    def open_home_settings(self):
        """Opens Android's 'Default home app' chooser."""
        if platform != 'android':
            return
        from jnius import autoclass
        act = autoclass('org.kivy.android.PythonActivity').mActivity
        Intent = autoclass('android.content.Intent')
        Settings = autoclass('android.provider.Settings')
        act.startActivity(Intent(Settings.ACTION_HOME_SETTINGS))

    def _on_key(self, window, key, *args):
        if key == 27:  # Back: never exit the launcher
            if self.root.ids.sm.current == 'settings':
                self.close_settings()
            else:
                home = self.root.ids.home
                if home.ids.search.text:
                    home.ids.search.text = ''
                else:
                    pager = home.ids.pager
                    if pager.slides:
                        pager.load_slide(pager.slides[0])
            return True
        return False

    # ---- volume ----------------------------------------------------------
    def _init_audio(self):
        if platform != 'android':
            return
        try:
            from jnius import autoclass, cast
            act = autoclass('org.kivy.android.PythonActivity').mActivity
            Context = autoclass('android.content.Context')
            self.am = cast('android.media.AudioManager',
                           act.getSystemService(Context.AUDIO_SERVICE))
            for s in (2, 3):
                self.vol_max[s] = max(1, self.am.getStreamMaxVolume(s))
                self._last_vol[s] = self.am.getStreamVolume(s)
        except Exception as e:
            print('audio init failed:', e)
            self.am = None

    def _poll_volume(self, dt):
        if not self.am:
            return
        for s in (3, 2):  # media, ring
            try:
                cur = self.am.getStreamVolume(s)
            except Exception:
                continue
            if cur != self._last_vol.get(s):
                self._last_vol[s] = cur
                self.show_volume(cur / float(self.vol_max[s]))
                break

    def show_volume(self, level):
        vol = self.root.ids.vol
        vol.style = self.volume_style
        vol.level = level
        cy = Window.height / 2.0 - vol.height / 2.0
        if vol.style == 'aosp':
            vol.pos = (Window.width - vol.width - dp(14), cy)
        elif vol.style == 'ios':
            vol.pos = (dp(14), cy)
        else:
            vol.pos = (Window.width / 2.0 - vol.width / 2.0,
                       Window.height - vol.height - dp(72))
        Animation.cancel_all(vol)
        vol.opacity = 1
        Clock.unschedule(self._hide_volume)
        Clock.schedule_once(self._hide_volume, 1.6)

    def _hide_volume(self, dt):
        Animation(opacity=0, d=0.25).start(self.root.ids.vol)

    def set_media_volume(self, frac):
        if not self.am:
            return
        try:
            mx = self.vol_max[3]
            self.am.setStreamVolume(3, int(round(frac * mx)), 0)
        except Exception as e:
            print('set volume failed:', e)

    def sync_slider(self, slider):
        if self.am:
            slider.value = self.am.getStreamVolume(3) / float(self.vol_max[3])


if __name__ == '__main__':
    LauncherApp().run()
