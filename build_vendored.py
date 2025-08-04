#!/usr/bin/env python3

"""
Customized build backend extending setuptools with downloading dependencies to be bundled with the package
(JavaScript libraries and similar assets).
Can also be directly called as an executable to download the dependencies.
"""

import subprocess
import tempfile
from pathlib import Path

from setuptools import build_meta as _orig

# Expose all symbols of the original build backend
from setuptools.build_meta import *  # noqa: F403, pylint: disable=W0401, W0614


def build_sdist(sdist_directory, config_settings=None):  # pylint: disable=E0102

    _download_vendored_deps()

    return _orig.build_sdist(sdist_directory, config_settings)


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):  # pylint: disable=E0102

    _download_vendored_deps()

    return _orig.build_wheel(wheel_directory, config_settings, metadata_directory)


def _download_vendored_deps():

    _download_htmx()


def _get_vendor_dir():

    vendor_dir = Path(__file__).parent / 'src/samaware/static/samaware/vendor'
    vendor_dir.mkdir(exist_ok=True)

    return vendor_dir


def _download_htmx():

    htmx_version = '2.0.4'
    url = f'https://unpkg.com/htmx.org@{htmx_version}/dist/htmx.min.js'

    vendor_dir = _get_vendor_dir().resolve()
    out_file = vendor_dir / 'htmx.min.js'

    if not out_file.exists():
        # Make the download atomic by using a temporary file because build steps might run in parallel
        # Put temporary file in the same directory to ensure staying on the same file system
        with tempfile.NamedTemporaryFile(dir=vendor_dir, delete=False) as tmp_file:
            subprocess.run(['curl', '-L', url, '-o', tmp_file.name], check=True, timeout=30)  # noqa: S607
            Path(tmp_file.name).replace(out_file)


if __name__ == '__main__':

    _download_vendored_deps()
