import subprocess
import itertools
import enum

from typing import Optional, Tuple, List
from libqtile import qtile
from libqtile.command.base import expose_command
from libqtile.widget.volume import Volume


class WirePlumberMuteStatus(enum.Enum):
    MUTED = '1'
    UNMUTED = '0'
    TOGGLE = 'toggle'

    def __str__(self):
        return self.value


class WirePlumberVolumeSign(enum.Enum):
    ABSOLUTE = ''
    INCREASE = '+'
    DECREASE = '-'

    def __str__(self):
        return self.value


class WirePlumberSink:
    def __init__(
        self,
        object_id: int,
        nick: str,
        is_default: Optional[bool]=False,
    ):
        self.object_id = object_id
        self.nick = nick
        self.is_default = is_default

    @staticmethod
    def _parse_sink_status_line(status_line: str):
        tokens = status_line.split()
        is_default = '*' in tokens
        idx = 1
        if is_default:
            idx +=1
        object_id = int(tokens[idx].strip('.'))
        nick = ' '.join(
            itertools.takewhile(
                lambda x: not x.startswith('['), tokens[idx+1:]
            )
        )
        return WirePlumberSink(
            object_id=object_id,
            nick=nick,
            is_default=is_default,
        )

    @staticmethod
    def parse_status_output(status_output: str):
        lines = status_output.split('\n')
        for idx, line in enumerate(lines):
            if 'Sinks:' in line:
                break
        lines = lines[idx+1:]
        for idx, line in enumerate(lines):
            if 'Sources:' in line:
                break
        lines = lines[:idx-1]
        return [
            WirePlumberSink._parse_sink_status_line(line)
            for line in lines
        ]


class WirePlumberConnection:
    def __init__(self):
        pass

    @staticmethod
    def _call_wpctl(cmd: List[str]) -> str:
        return subprocess.check_output(' '.join(['wpctl', *cmd]), shell=True).decode('utf-8')

    def set_volume(
        self,
        value: float,
        sign: Optional[WirePlumberVolumeSign]=WirePlumberVolumeSign.ABSOLUTE,
        sink: Optional[int]=None,
    ):
        """
        :value: step fraction
        :sign: + or -, value is absolute if None
        :sink: sink id, @DEFAULT_AUDIO_SINK@ used if None
        """

        cmd = [
            'set-volume',
            f'{sink if sink is not None else "@DEFAULT_AUDIO_SINK@"}',
            f'{value}{sign}',
            '--limit',
            '1'
        ]
        self._call_wpctl(cmd)

    def set_mute(
        self,
        value: WirePlumberMuteStatus,
        sink: Optional[int]=None,
    ):
        """
        :value: 1/0/toggle
        :sink: sink id, @DEFAULT_AUDIO_SINK@ used if None
        """

        cmd = [
            'set-mute',
            f'{sink if sink is not None else "@DEFAULT_AUDIO_SINK@"}',
            f'{value}',
        ]
        self._call_wpctl(cmd)

    def get_volume(
        self,
        sink: Optional[int]=None,
    ) -> Tuple[float, bool]:
        """
        :sink: sink id, @DEFAULT_AUDIO_SINK@ used if None
        :return: (volume_level, is_muted)
        """

        cmd = [
            'get-volume',
            f'{sink if sink is not None else "@DEFAULT_AUDIO_SINK@"}',
        ]
        out = self._call_wpctl(cmd).split()
        volume = float(out[1]) * 100
        is_muted = '[MUTED]' in out
        return volume, is_muted

    def set_default(self, sink: int):
        cmd = [
            'set-default',
            f'{sink}',
        ]
        self._call_wpctl(cmd)

    def list_sinks(self) -> List[WirePlumberSink]:
        cmd = [
            'status',
            '--nick',
        ]
        out = self._call_wpctl(cmd)
        return WirePlumberSink.parse_status_output(out)


class WirePlumberVolume(Volume):
    """
    Cli based wireplumber volume widget
    """

    def __init__(self, **config):
        # NOTE: Button4/Button5 is WheelUp and WheelDown
        Volume.__init__(
            self, 
            **{
                'step': 0.05,
                **config,
            }
        )
        self._connection = WirePlumberConnection()
        self.add_callbacks(
            {
                "Button1": self.mute,
                "Button2": self.next_sink,
                "Button4": self.increase_vol,
                "Button5": self.decrease_vol,
            }
        )
    def _configure(self, qtile, bar):
        Volume._configure(self, qtile, bar)
        if self.theme_path:
            self.setup_images()

    @expose_command()
    def mute(self):
        """Mute the sound device."""
        self._connection.set_mute(value=WirePlumberMuteStatus.TOGGLE)

    @expose_command()
    def increase_vol(self, value=None):
        """Increase volume."""
        self._connection.set_mute(value=WirePlumberMuteStatus.UNMUTED)
        self._connection.set_volume(
            value=value or self.step,
            sign=WirePlumberVolumeSign.INCREASE,
        )

    @expose_command()
    def decrease_vol(self, value=None):
        """Decrease volume."""
        self._connection.set_mute(value=WirePlumberMuteStatus.UNMUTED)
        self._connection.set_volume(
            value=value or self.step,
            sign=WirePlumberVolumeSign.DECREASE,
        )

    @expose_command()
    def next_sink(self):
        """Set next sink as default"""
        sinks = self._connection.list_sinks()
        idx = 0
        for idx in range(len(sinks)):
            sink = sinks[idx]
            if sink.is_default:
                break

        if idx < len(sinks):
            self._connection.set_default(
                sinks[(idx + 1) % len(sinks)].object_id
            )

    def get_volume(self):
        return self._connection.get_volume()
