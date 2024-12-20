import subprocess
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
            f'{sink if sink is not None else "@DEFAULT_AUDIO_SINK@"}',
        ]
        self._call_wpctl(cmd)


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

    def get_volume(self):
        return self._connection.get_volume()
